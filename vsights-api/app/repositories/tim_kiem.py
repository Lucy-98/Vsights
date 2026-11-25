"""Truy vấn chỗ ở khả dụng theo dải ngày [ngay_nhan, ngay_tra) — D-028b, D-021, BR-04.

Khả dụng = trên CÙNG MỘT OTA có giá tham khảo cho ĐỦ mọi đêm (GROUP BY ... HAVING COUNT(*) = số đêm).
Giá dùng để so luôn là giá đã gồm thuế, phí (D-021): OTA niêm yết chưa gồm thuế phí được quy đổi theo
NGUON_OTA.ty_le_thue_phi; OTA chưa có tỷ lệ thì không vào phép so.

Kỹ thuật tối ưu:
- ix_co_so_tim (chỉ mục từng phần, trang_thai = 'hien') chọn cơ sở của tỉnh;
- ix_loai_phong_co_so (từng phần) lấy loại phòng đủ sức chứa;
- khoá chính phủ của gia_tham_khao (ma_loai_phong, ma_lien_ket, ngay) INCLUDE (gia_dem, gom_thue_phi):
  mỗi cặp (loại phòng, OTA) đọc đúng một đoạn chỉ mục dài bằng số đêm, quét chỉ mục thuần;
- tiện nghi lọc bằng EXISTS trên hai chỉ mục ngược;
- tên OTA, tên loại phòng, ngày cập nhật giá chỉ lấy cho các dòng của trang kết quả (lấy muộn);
- giá ngoài phép so (OTA chưa gồm thuế phí, chưa có tỷ lệ — B-023) cũng chỉ lấy cho các cơ sở của trang.
"""
from datetime import date

from sqlalchemy import Connection, text

_SAP_XEP = {
    # BR-04: khớp sở thích → giá cả chuyến → điểm đánh giá; không có hệ số thương mại
    "phu_hop": "so_thich_khop DESC, tong_ca_chuyen ASC, diem_xep DESC NULLS LAST, ma_co_so",
    "gia_tang": "tong_ca_chuyen ASC, diem_xep DESC NULLS LAST, ma_co_so",
    "danh_gia": "diem_xep DESC NULLS LAST, so_luot_danh_gia DESC, tong_ca_chuyen ASC, ma_co_so",
}

_SQL = """
WITH ung_vien AS MATERIALIZED (  -- tính trước: loại phòng đang hiện, đủ sức chứa, của cơ sở đang hiện trong tỉnh
  SELECT lp.ma_loai_phong, lp.ma_co_so
  FROM co_so_luu_tru cs
  JOIN loai_phong lp ON lp.ma_co_so = cs.ma_co_so AND lp.trang_thai = 'hien'
  WHERE cs.ma_tinh = :ma_tinh AND cs.trang_thai = 'hien'
    AND cs.ma_co_so <> ALL(CAST(:loai_tru AS bigint[]))   -- chatbot: chỗ ở du khách đã loại (AI-015)
    AND lp.suc_chua_nl * :so_phong >= :so_nguoi
    AND (CAST(:loai_hinh AS text) IS NULL OR cs.loai_hinh = :loai_hinh)
    AND NOT EXISTS (          -- mọi tiện nghi được lọc đều có ở cơ sở hoặc ở loại phòng
      SELECT 1 FROM unnest(CAST(:tien_nghi AS smallint[])) AS yc(ma)
      WHERE NOT EXISTS (SELECT 1 FROM co_so_tien_nghi x WHERE x.ma_tien_nghi = yc.ma AND x.ma_co_so = cs.ma_co_so)
        AND NOT EXISTS (SELECT 1 FROM loai_phong_tien_nghi y WHERE y.ma_tien_nghi = yc.ma AND y.ma_loai_phong = lp.ma_loai_phong))
),
lua_chon AS (                 -- (loại phòng × OTA) có giá cho ĐỦ mọi đêm, giá đã gồm thuế phí
  -- Cộng bigint theo nhóm rồi quy đổi một lần mỗi nhóm (nhanh hơn quy đổi numeric từng đêm)
  SELECT uv.ma_co_so, g.ma_loai_phong, g.ma_lien_ket,
         (COALESCE(SUM(g.gia_dem) FILTER (WHERE g.gom_thue_phi), 0)
          + COALESCE(round(SUM(g.gia_dem) FILTER (WHERE NOT g.gom_thue_phi) * (1 + max(o.ty_le_thue_phi) / 100)), 0)
         )::bigint * :so_phong AS tong_ca_chuyen
  FROM ung_vien uv
  JOIN lien_ket_ota lk ON lk.ma_co_so = uv.ma_co_so AND lk.trang_thai = 'hoat_dong'
  JOIN nguon_ota o     ON o.ma_ota = lk.ma_ota AND o.trang_thai = 'hoat_dong'
  JOIN gia_tham_khao g ON g.ma_loai_phong = uv.ma_loai_phong AND g.ma_lien_ket = lk.ma_lien_ket
                      AND g.ngay >= :nhan AND g.ngay < :tra
  WHERE g.gom_thue_phi OR o.ty_le_thue_phi IS NOT NULL
  GROUP BY uv.ma_co_so, g.ma_loai_phong, g.ma_lien_ket
  HAVING COUNT(*) = :so_dem
),
re_nhat AS (                  -- lựa chọn rẻ nhất mỗi cơ sở (sau khi đã quy đổi thuế phí)
  SELECT DISTINCT ON (ma_co_so) ma_co_so, ma_loai_phong, ma_lien_ket, tong_ca_chuyen,
         count(*) OVER (PARTITION BY ma_co_so) AS so_lua_chon
  FROM lua_chon
  ORDER BY ma_co_so, tong_ca_chuyen, ma_loai_phong, ma_lien_ket
),
loc AS (
  SELECT r.*, cs.ten, cs.loai_hinh, cs.dia_chi, cs.khu_vuc, cs.hang_sao, cs.la_du_lieu_mau,
         cs.diem_tb, cs.so_luot_danh_gia,
         CASE WHEN cs.so_luot_danh_gia >= 3 THEN cs.diem_tb END AS diem_xep,
         (SELECT count(*) FROM co_so_so_thich st
           WHERE st.ma_co_so = r.ma_co_so AND st.ma_so_thich = ANY(CAST(:so_thich AS smallint[]))) AS so_thich_khop
  FROM re_nhat r JOIN co_so_luu_tru cs ON cs.ma_co_so = r.ma_co_so
  WHERE CAST(:ngan_sach AS bigint) IS NULL
     OR (:loai_ngan_sach = 'ca_chuyen' AND r.tong_ca_chuyen <= :ngan_sach)
     OR (:loai_ngan_sach = 'moi_dem'   AND r.tong_ca_chuyen <= CAST(:ngan_sach AS bigint) * :so_dem * :so_phong)
)
SELECT *, count(*) OVER () AS tong FROM loc
ORDER BY {sap_xep}
LIMIT :lim OFFSET :off
"""

# Lấy muộn: chỉ cho các dòng của trang kết quả
_CHI_TIET = """
SELECT lp.ma_loai_phong, lp.ten_loai_phong, lk.ma_lien_ket, o.ten_ota, lk.url,
       bool_and(g.gom_thue_phi) AS gia_goc_gom_thue_phi, min(g.ngay_cap_nhat) AS cap_nhat_gia
FROM unnest(CAST(:lp AS bigint[]), CAST(:lk AS bigint[])) AS c(ma_loai_phong, ma_lien_ket)
JOIN loai_phong lp ON lp.ma_loai_phong = c.ma_loai_phong
JOIN lien_ket_ota lk ON lk.ma_lien_ket = c.ma_lien_ket
JOIN nguon_ota o ON o.ma_ota = lk.ma_ota
JOIN gia_tham_khao g ON g.ma_loai_phong = c.ma_loai_phong AND g.ma_lien_ket = c.ma_lien_ket
                    AND g.ngay >= :nhan AND g.ngay < :tra
GROUP BY lp.ma_loai_phong, lp.ten_loai_phong, lk.ma_lien_ket, o.ten_ota, lk.url
"""


# B-023 (D-021): giá của OTA chưa gồm thuế, phí và chưa có tỷ lệ quy đổi — không vào phép so, chỉ HIỆN RIÊNG.
# Rẻ nhất mỗi (cơ sở, OTA) trên các loại phòng đủ điều kiện như CTE ung_vien; chỉ cho các cơ sở của trang kết quả.
_NGOAI_PHEP_SO = """
SELECT DISTINCT ON (lp.ma_co_so, lk.ma_ota)
       lp.ma_co_so, o.ten_ota, lk.ma_lien_ket, lk.url, lp.ma_loai_phong, lp.ten_loai_phong,
       SUM(g.gia_dem)::bigint * :so_phong AS tong_chua_gom_thue_phi, min(g.ngay_cap_nhat) AS cap_nhat_gia
FROM loai_phong lp
JOIN lien_ket_ota lk ON lk.ma_co_so = lp.ma_co_so AND lk.trang_thai = 'hoat_dong'
JOIN nguon_ota o     ON o.ma_ota = lk.ma_ota AND o.trang_thai = 'hoat_dong' AND o.ty_le_thue_phi IS NULL
JOIN gia_tham_khao g ON g.ma_loai_phong = lp.ma_loai_phong AND g.ma_lien_ket = lk.ma_lien_ket
                    AND g.ngay >= :nhan AND g.ngay < :tra
WHERE lp.ma_co_so = ANY(CAST(:cs AS bigint[])) AND lp.trang_thai = 'hien' AND lp.suc_chua_nl * :so_phong >= :so_nguoi
  AND NOT EXISTS (
      SELECT 1 FROM unnest(CAST(:tien_nghi AS smallint[])) AS yc(ma)
      WHERE NOT EXISTS (SELECT 1 FROM co_so_tien_nghi x WHERE x.ma_tien_nghi = yc.ma AND x.ma_co_so = lp.ma_co_so)
        AND NOT EXISTS (SELECT 1 FROM loai_phong_tien_nghi y WHERE y.ma_tien_nghi = yc.ma AND y.ma_loai_phong = lp.ma_loai_phong))
GROUP BY lp.ma_co_so, lk.ma_ota, o.ten_ota, lk.ma_lien_ket, lk.url, lp.ma_loai_phong, lp.ten_loai_phong
HAVING COUNT(*) = :so_dem AND NOT bool_and(g.gom_thue_phi)
ORDER BY lp.ma_co_so, lk.ma_ota, tong_chua_gom_thue_phi, lp.ma_loai_phong
"""


def sql_tim(sap_xep: str) -> str:
    return _SQL.format(sap_xep=_SAP_XEP[sap_xep])


def tim_cho_o(conn: Connection, *, ma_tinh: int, nhan: date, tra: date, so_nguoi: int, so_phong: int,
              ngan_sach: int | None, loai_ngan_sach: str, loai_hinh: str | None, tien_nghi: list[int],
              so_thich: list[int], sap_xep: str, trang: int, kich_thuoc: int, loai_tru: list[int] = ()):
    p = {"ma_tinh": ma_tinh, "nhan": nhan, "tra": tra, "so_dem": (tra - nhan).days, "so_nguoi": so_nguoi,
         "so_phong": so_phong, "ngan_sach": ngan_sach, "loai_ngan_sach": loai_ngan_sach, "loai_hinh": loai_hinh,
         "tien_nghi": tien_nghi, "so_thich": so_thich, "loai_tru": list(loai_tru), "lim": kich_thuoc, "off": (trang - 1) * kich_thuoc}
    rows = conn.execute(text(sql_tim(sap_xep)), p).mappings().all()
    if not rows:
        # Xin trang vượt quá số trang: vẫn trả đúng `tong` (trước đây trả 0 → giao diện hiện nhầm "không có kết quả")
        return [], (dem_ket_qua(conn, **kw_dem(p)) if trang > 1 else 0), {}, {}
    ct = conn.execute(text(_CHI_TIET), {"lp": [r["ma_loai_phong"] for r in rows],
                                        "lk": [r["ma_lien_ket"] for r in rows], "nhan": nhan, "tra": tra}).mappings().all()
    chi_tiet = {(c["ma_loai_phong"], c["ma_lien_ket"]): c for c in ct}
    ngoai = {}
    for r in conn.execute(text(_NGOAI_PHEP_SO), {**p, "cs": [r["ma_co_so"] for r in rows]}).mappings():
        ngoai.setdefault(r["ma_co_so"], []).append(r)
    return rows, rows[0]["tong"], chi_tiet, ngoai


def kw_dem(p: dict) -> dict:
    return {"ma_tinh": p["ma_tinh"], "nhan": p["nhan"], "tra": p["tra"], "so_nguoi": p["so_nguoi"],
            "so_phong": p["so_phong"], "ngan_sach": p["ngan_sach"], "loai_ngan_sach": p["loai_ngan_sach"],
            "loai_hinh": p["loai_hinh"], "tien_nghi": p["tien_nghi"], "loai_tru": p["loai_tru"]}


def dem_ket_qua(conn: Connection, *, ma_tinh: int, nhan: date, tra: date, so_nguoi: int, so_phong: int,
                ngan_sach: int | None, loai_ngan_sach: str, loai_hinh: str | None, tien_nghi: list[int],
                loai_tru: list[int] = ()) -> int:
    """Chỉ đếm số kết quả (cùng truy vấn tìm, LIMIT 1) — cho trang vượt số trang và gợi ý nới điều kiện (B-028)."""
    p = {"ma_tinh": ma_tinh, "nhan": nhan, "tra": tra, "so_dem": (tra - nhan).days, "so_nguoi": so_nguoi,
         "so_phong": so_phong, "ngan_sach": ngan_sach, "loai_ngan_sach": loai_ngan_sach, "loai_hinh": loai_hinh,
         "tien_nghi": list(tien_nghi), "so_thich": [], "loai_tru": list(loai_tru), "lim": 1, "off": 0}
    r = conn.execute(text(sql_tim("gia_tang")), p).mappings().first()
    return r["tong"] if r else 0


def ghi_luot_tim(conn: Connection, *, ma_nguoi_dung, ma_tinh, nhan, tra, so_nguoi, so_phong, ngan_sach,
                 loai_ngan_sach, so_ket_qua) -> None:
    conn.execute(text(
        "INSERT INTO luot_tim_kiem (ma_nguoi_dung, ma_tinh, ngay_nhan, ngay_tra, so_nguoi, so_phong, ngan_sach, "
        "loai_ngan_sach, so_ket_qua) VALUES (:u, :t, :n, :tr, :sn, :sp, :ns, :lns, :kq)"),
        {"u": ma_nguoi_dung, "t": ma_tinh, "n": nhan, "tr": tra, "sn": so_nguoi, "sp": so_phong, "ns": ngan_sach,
         "lns": loai_ngan_sach if ngan_sach is not None else None, "kq": so_ket_qua})
