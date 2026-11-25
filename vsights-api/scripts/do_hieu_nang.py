"""Đo hiệu năng truy vấn tìm chỗ ở theo dải ngày trên dữ liệu giả lập lớn.

Dữ liệu: 5.000 cơ sở (tỉnh lớn TP. Hồ Chí Minh có 1.000), 12.500 loại phòng, giá 150 đêm cho mỗi
(loại phòng × OTA) → khoảng 4,4 triệu dòng giá. Tạo CSDL riêng `vsights_do`, không đụng CSDL demo.

Cách đo: mỗi trường hợp chạy 1 lần làm nóng + 7 lần EXPLAIN (ANALYZE, BUFFERS), lấy trung vị "Execution Time".
Hai cấu hình:
  A. Đầy đủ tối ưu (lược đồ db/01_schema.sql).
  B. Bỏ tối ưu: bỏ các chỉ mục từng phần, chỉ mục ngược tiện nghi, khoá chính giá không có INCLUDE.

Chạy:  PGHOST=localhost PGUSER=postgres python scripts/do_hieu_nang.py
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import psycopg

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))
DB = "vsights_do"

SINH_DU_LIEU = """
SELECT setseed(0.2026);
-- 5.000 cơ sở: TP.HCM (ma_tinh 27) 1.000, 33 tỉnh còn lại chia đều phần còn lại
INSERT INTO co_so_luu_tru (ma_tinh, ten, loai_hinh, dia_chi, hang_sao, la_du_lieu_mau, trang_thai)
SELECT CASE WHEN i <= 1000 THEN 27 ELSE 1 + ((i - 1001) % 33) + CASE WHEN 1 + ((i - 1001) % 33) >= 27 THEN 1 ELSE 0 END END,
       'Cơ sở giả lập ' || i,
       (ARRAY['khach_san','homestay','resort','can_ho','nha_nghi'])[1 + i % 5],
       'Địa chỉ giả lập ' || i, 1 + i % 5, TRUE,
       CASE WHEN i % 20 = 0 THEN 'an' ELSE 'hien' END
FROM generate_series(1, 5000) i;

INSERT INTO co_so_tien_nghi SELECT c.ma_co_so, t.ma_tien_nghi FROM co_so_luu_tru c JOIN tien_nghi t ON t.pham_vi='co_so'
WHERE random() < 0.35;
INSERT INTO co_so_so_thich SELECT c.ma_co_so, s.ma_so_thich FROM co_so_luu_tru c JOIN so_thich s ON s.pham_vi <> 'dia_diem'
WHERE random() < 0.3;

-- 12.500 loại phòng (2 hoặc 3 mỗi cơ sở)
INSERT INTO loai_phong (ma_co_so, ten_loai_phong, suc_chua_nl, suc_chua_te, co_bua_sang, trang_thai)
SELECT c.ma_co_so, 'Loại ' || k, (ARRAY[2,2,4])[k], 1, k = 2, CASE WHEN random() < 0.03 THEN 'an' ELSE 'hien' END
FROM co_so_luu_tru c CROSS JOIN generate_series(1, 3) k
WHERE k <= 2 OR c.ma_co_so % 2 = 0;
INSERT INTO loai_phong_tien_nghi SELECT lp.ma_loai_phong, t.ma_tien_nghi FROM loai_phong lp JOIN tien_nghi t ON t.pham_vi='phong'
WHERE random() < 0.35;

-- Liên kết OTA: Booking.com + Agoda cho mọi cơ sở, Traveloka cho 1/3
INSERT INTO lien_ket_ota (ma_co_so, ma_ota, url, trang_thai)
SELECT c.ma_co_so, o.ma_ota, o.url_goc || '/gl/' || c.ma_co_so, CASE WHEN random() < 0.02 THEN 'hong' ELSE 'hoat_dong' END
FROM co_so_luu_tru c JOIN nguon_ota o ON o.ten_ota IN ('Booking.com','Agoda') OR (o.ten_ota='Traveloka' AND c.ma_co_so % 3 = 0);

-- Giá 150 đêm, ~3% đêm thiếu giá
INSERT INTO gia_tham_khao (ma_loai_phong, ma_lien_ket, ngay, gia_dem, gom_thue_phi)
SELECT lp.ma_loai_phong, lk.ma_lien_ket, d::date, (300 + (lp.ma_loai_phong * 37 + lk.ma_ota * 11) % 2500) * 1000,
       lk.ma_ota = 2
FROM loai_phong lp JOIN lien_ket_ota lk ON lk.ma_co_so = lp.ma_co_so
CROSS JOIN generate_series(current_date, current_date + 149, interval '1 day') d
WHERE random() >= 0.03;
"""

BO_TOI_UU = """
DROP INDEX ix_co_so_tim; DROP INDEX ix_loai_phong_co_so; DROP INDEX ix_lien_ket_hoat_dong;
DROP INDEX ix_co_so_tien_nghi_nguoc; DROP INDEX ix_loai_phong_tien_nghi_nguoc;
ALTER TABLE gia_tham_khao DROP CONSTRAINT gia_tham_khao_pkey;
ALTER TABLE gia_tham_khao ADD PRIMARY KEY (ma_loai_phong, ma_lien_ket, ngay);
"""


def psql(db: str, *args: str) -> None:
    subprocess.run(["psql", "-v", "ON_ERROR_STOP=1", "-q", "-d", db, *args], check=True)


def chuan_bi() -> None:
    psql("postgres", "-c", f'DROP DATABASE IF EXISTS "{DB}"', "-c", f'CREATE DATABASE "{DB}"')
    for f in ("db/01_schema.sql", "db/02_danh_muc.sql"):
        psql(DB, "-f", str(GOC / f))
    t = time.time()
    psql(DB, "-c", SINH_DU_LIEU)
    psql(DB, "-c", "VACUUM ANALYZE")  # đặt visibility map để quét chỉ mục thuần không phải đọc heap
    print(f"Sinh dữ liệu: {time.time() - t:.0f} s", file=sys.stderr)


def dsn() -> str:
    return f"dbname={DB}"


def do(conn, sql: str, p: dict, lan: int = 7) -> tuple[float, dict]:
    sql_pg = re.sub(r"(?<!:):(\w+)", r"%(\1)s", sql)
    conn.execute("EXPLAIN (ANALYZE) " + sql_pg, p)  # làm nóng
    tg, plan = [], None
    for _ in range(lan):
        plan = conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql_pg, p).fetchone()[0][0]
        tg.append(plan["Execution Time"])
    return statistics.median(tg), plan


def heap_fetches_gia(node) -> list:
    kq = []
    if node.get("Relation Name") == "gia_tham_khao":
        kq.append((node["Node Type"], node.get("Heap Fetches")))
    for con in node.get("Plans", []):
        kq += heap_fetches_gia(con)
    return kq


def cac_truong_hop():
    from app.repositories.tim_kiem import sql_tim
    nhan = date.today() + timedelta(days=20)
    base = {"ma_tinh": 27, "nhan": nhan, "so_nguoi": 2, "so_phong": 1, "ngan_sach": None,
            "loai_ngan_sach": "moi_dem", "loai_hinh": None, "tien_nghi": [], "so_thich": [1, 3], "loai_tru": [], "lim": 20, "off": 0}
    for dem in (2, 7):
        yield f"Tỉnh lớn (1.000 cơ sở), {dem} đêm, sắp xếp phù hợp", sql_tim("phu_hop"), \
            {**base, "tra": nhan + timedelta(days=dem), "so_dem": dem}
    yield "Tỉnh lớn, 2 đêm, ngân sách 1,2 triệu/đêm + 2 tiện nghi", sql_tim("phu_hop"), \
        {**base, "tra": nhan + timedelta(days=2), "so_dem": 2, "ngan_sach": 1200000, "tien_nghi": [1, 9]}
    yield "Tỉnh nhỏ (~121 cơ sở), 2 đêm", sql_tim("phu_hop"), \
        {**base, "ma_tinh": 21, "tra": nhan + timedelta(days=2), "so_dem": 2}
    yield "Tiện nghi: cơ sở ở tỉnh lớn có Hồ bơi", (
        "SELECT cs.ma_co_so FROM co_so_luu_tru cs WHERE cs.ma_tinh = :ma_tinh AND cs.trang_thai = 'hien' "
        "AND EXISTS (SELECT 1 FROM co_so_tien_nghi x WHERE x.ma_tien_nghi = 2 AND x.ma_co_so = cs.ma_co_so)"), \
        {"ma_tinh": 27}


def chay_cau_hinh(ten: str) -> list[dict]:
    kq = []
    with psycopg.connect(dsn(), autocommit=True) as conn:
        quy_mo = conn.execute("SELECT (SELECT count(*) FROM co_so_luu_tru), (SELECT count(*) FROM loai_phong), "
                              "(SELECT count(*) FROM gia_tham_khao)").fetchone()
        for nhan_ttg, sql, p in cac_truong_hop():
            ms, plan = do(conn, sql, p)
            kq.append({"cau_hinh": ten, "truong_hop": nhan_ttg, "trung_vi_ms": round(ms, 2),
                       "gia_tham_khao_scan": heap_fetches_gia(plan["Plan"]), "quy_mo": quy_mo})
            print(f"[{ten}] {nhan_ttg}: {ms:.2f} ms  {heap_fetches_gia(plan['Plan'])}", file=sys.stderr)
    return kq


def main():
    os.environ.setdefault("VS_JWT_SECRET", "x" * 40)
    chuan_bi()
    kq = chay_cau_hinh("A. đầy đủ tối ưu")
    psql(DB, "-c", BO_TOI_UU)
    psql(DB, "-c", "VACUUM ANALYZE")
    kq += chay_cau_hinh("B. bỏ tối ưu")
    (GOC / "scripts" / "ket_qua_do.json").write_text(json.dumps(kq, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(kq, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
