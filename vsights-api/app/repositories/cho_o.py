"""SQL cho chỗ ở (CO_SO_LUU_TRU) và loại phòng (LOAI_PHONG)."""
from sqlalchemy import Connection, text

from app.repositories.chung import chen, sua, thay_bang_noi

COT_CO_SO = {"ma_tinh", "ten", "loai_hinh", "dia_chi", "khu_vuc", "vi_do", "kinh_do", "hang_sao", "mo_ta",
             "gio_nhan_phong", "gio_tra_phong", "chinh_sach_huy", "chinh_sach_khac", "la_du_lieu_mau"}
COT_LOAI_PHONG = {"ma_co_so", "ten_loai_phong", "loai_giuong", "suc_chua_nl", "suc_chua_te", "dien_tich",
                  "co_bua_sang", "dieu_kien_huy", "thanh_toan_tai_cho", "so_ngay_huy_mien_phi"}

_CHON_CO_SO = """
SELECT cs.ma_co_so, cs.ma_tinh, t.ten_tinh, cs.ten, cs.loai_hinh, cs.dia_chi, cs.khu_vuc, cs.vi_do, cs.kinh_do,
       cs.hang_sao, cs.mo_ta, cs.gio_nhan_phong, cs.gio_tra_phong, cs.chinh_sach_huy, cs.chinh_sach_khac,
       cs.diem_tb, cs.so_luot_danh_gia, cs.la_du_lieu_mau, cs.trang_thai, cs.ngay_cap_nhat,
       COALESCE((SELECT array_agg(ma_tien_nghi ORDER BY ma_tien_nghi) FROM co_so_tien_nghi x
                 WHERE x.ma_co_so = cs.ma_co_so), '{}') AS ma_tien_nghi,
       (SELECT count(*) FROM loai_phong lp WHERE lp.ma_co_so = cs.ma_co_so) AS so_loai_phong
FROM co_so_luu_tru cs JOIN tinh_thanh t USING (ma_tinh)"""


def lay_co_so(conn: Connection, ma: int, khoa: bool = False):
    if khoa:
        conn.execute(text("SELECT 1 FROM co_so_luu_tru WHERE ma_co_so = :m FOR UPDATE"), {"m": ma})
    return conn.execute(text(_CHON_CO_SO + " WHERE cs.ma_co_so = :m"), {"m": ma}).mappings().first()


def danh_sach_co_so(conn: Connection, ma_tinh: int | None, trang_thai: str | None, q: str | None,
                    trang: int, kich_thuoc: int):
    dk = ["(CAST(:t AS smallint) IS NULL OR cs.ma_tinh = :t)", "(CAST(:tt AS text) IS NULL OR cs.trang_thai = :tt)",
          "(CAST(:q AS text) IS NULL OR unaccent(lower(cs.ten)) LIKE '%' || unaccent(lower(:q)) || '%')"]
    p = {"t": ma_tinh, "tt": trang_thai, "q": q, "lim": kich_thuoc, "off": (trang - 1) * kich_thuoc}
    where = " WHERE " + " AND ".join(dk)
    tong = conn.execute(text("SELECT count(*) FROM co_so_luu_tru cs" + where), p).scalar_one()
    rows = conn.execute(text(_CHON_CO_SO + where + " ORDER BY cs.ma_co_so DESC LIMIT :lim OFFSET :off"), p).mappings().all()
    return rows, tong


def co_so_trung(conn: Connection, ma_tinh: int, ten: str, dia_chi: str, tru_ma: int | None = None) -> int | None:
    return conn.execute(text(
        "SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh = :t AND lower(btrim(ten)) = lower(btrim(:ten)) "
        "AND lower(btrim(dia_chi)) = lower(btrim(:dc)) AND (CAST(:tru AS bigint) IS NULL OR ma_co_so <> :tru) LIMIT 1"),
        {"t": ma_tinh, "ten": ten, "dc": dia_chi, "tru": tru_ma}).scalar()


def tao_co_so(conn: Connection, du_lieu: dict) -> int:
    return chen(conn, "co_so_luu_tru", "ma_co_so", du_lieu, COT_CO_SO)


def sua_co_so(conn: Connection, ma: int, du_lieu: dict) -> None:
    sua(conn, "co_so_luu_tru", "ma_co_so", ma, du_lieu, COT_CO_SO, them_set="ngay_cap_nhat = now()")


def dat_tien_nghi_co_so(conn: Connection, ma: int, ds: list[int]) -> None:
    thay_bang_noi(conn, "co_so_tien_nghi", "ma_co_so", ma, "ma_tien_nghi", ds)


def doi_trang_thai_co_so(conn: Connection, ma: int, trang_thai: str) -> None:
    conn.execute(text("UPDATE co_so_luu_tru SET trang_thai = :tt, ngay_cap_nhat = now() WHERE ma_co_so = :m"),
                 {"tt": trang_thai, "m": ma})


_CHON_LOAI_PHONG = """
SELECT lp.ma_loai_phong, lp.ma_co_so, lp.ten_loai_phong, lp.loai_giuong, lp.suc_chua_nl, lp.suc_chua_te,
       lp.dien_tich, lp.co_bua_sang, lp.dieu_kien_huy, lp.thanh_toan_tai_cho, lp.so_ngay_huy_mien_phi, lp.trang_thai,
       COALESCE((SELECT array_agg(ma_tien_nghi ORDER BY ma_tien_nghi) FROM loai_phong_tien_nghi x
                 WHERE x.ma_loai_phong = lp.ma_loai_phong), '{}') AS ma_tien_nghi
FROM loai_phong lp"""


def lay_loai_phong(conn: Connection, ma: int, khoa: bool = False):
    if khoa:
        conn.execute(text("SELECT 1 FROM loai_phong WHERE ma_loai_phong = :m FOR UPDATE"), {"m": ma})
    return conn.execute(text(_CHON_LOAI_PHONG + " WHERE lp.ma_loai_phong = :m"), {"m": ma}).mappings().first()


def loai_phong_cua_co_so(conn: Connection, ma_co_so: int):
    return conn.execute(text(_CHON_LOAI_PHONG + " WHERE lp.ma_co_so = :m ORDER BY lp.ma_loai_phong"),
                        {"m": ma_co_so}).mappings().all()


def tao_loai_phong(conn: Connection, du_lieu: dict) -> int:
    return chen(conn, "loai_phong", "ma_loai_phong", du_lieu, COT_LOAI_PHONG)


def sua_loai_phong(conn: Connection, ma: int, du_lieu: dict) -> None:
    sua(conn, "loai_phong", "ma_loai_phong", ma, du_lieu, COT_LOAI_PHONG - {"ma_co_so"})


def dat_tien_nghi_loai_phong(conn: Connection, ma: int, ds: list[int]) -> None:
    thay_bang_noi(conn, "loai_phong_tien_nghi", "ma_loai_phong", ma, "ma_tien_nghi", ds)


def doi_trang_thai_loai_phong(conn: Connection, ma: int, trang_thai: str) -> None:
    conn.execute(text("UPDATE loai_phong SET trang_thai = :tt WHERE ma_loai_phong = :m"), {"tt": trang_thai, "m": ma})
