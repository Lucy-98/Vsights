"""SQL cho địa điểm, quán ăn (DIA_DIEM) và bảng con: giờ mở cửa, giá vé, sở thích."""
from sqlalchemy import Connection, text

from app.repositories.chung import chen, sua, thay_bang_noi

COT_DIA_DIEM = {"ma_tinh", "ma_loai", "ten", "dia_chi", "vi_do", "kinh_do", "mo_ta", "luu_y", "thoi_diem_dep",
                "thoi_luong_goi_y", "muc_gia_nguoi_tu", "muc_gia_nguoi_den", "lien_ket_mua_ve", "la_du_lieu_mau"}

_CHON = """
SELECT d.ma_dia_diem, d.ma_tinh, t.ten_tinh, d.ten, d.dia_chi, d.vi_do, d.kinh_do,
       json_build_object('ma_loai', l.ma_loai, 'ten_loai', l.ten_loai, 'nhom', l.nhom) AS loai,
       d.muc_gia_nguoi_tu, d.muc_gia_nguoi_den, d.diem_tb, d.so_luot_danh_gia, d.la_du_lieu_mau, d.trang_thai"""
_TU = " FROM dia_diem d JOIN loai_dia_diem l USING (ma_loai) JOIN tinh_thanh t ON t.ma_tinh = d.ma_tinh"

_CHI_TIET = """,
       d.mo_ta, d.luu_y, d.thoi_diem_dep, d.thoi_luong_goi_y, d.lien_ket_mua_ve, d.ngay_cap_nhat,
       COALESCE((SELECT json_agg(json_build_object('thu_trong_tuan', g.thu_trong_tuan, 'ca', g.ca,
                  'gio_mo', to_char(g.gio_mo, 'HH24:MI'), 'gio_dong', to_char(g.gio_dong, 'HH24:MI'))
                  ORDER BY g.thu_trong_tuan, g.ca) FROM gio_mo_cua g WHERE g.ma_dia_diem = d.ma_dia_diem), '[]') AS gio_mo_cua,
       COALESCE((SELECT json_agg(json_build_object('ma_gia_ve', v.ma_gia_ve, 'loai_khach', v.loai_khach,
                  'dieu_kien', v.dieu_kien, 'gia', v.gia) ORDER BY v.gia DESC)
                 FROM gia_ve v WHERE v.ma_dia_diem = d.ma_dia_diem), '[]') AS gia_ve,
       COALESCE((SELECT array_agg(s.ma_so_thich ORDER BY s.ma_so_thich) FROM dia_diem_so_thich s
                 WHERE s.ma_dia_diem = d.ma_dia_diem), '{}') AS ma_so_thich"""


def tim(conn: Connection, *, chi_hien: bool, ma_tinh=None, nhom=None, ma_loai=None, ma_so_thich=None, q=None,
        trang_thai=None, trang: int = 1, kich_thuoc: int = 20):
    where = """ WHERE (NOT :chi_hien OR d.trang_thai = 'hien')
      AND (CAST(:tt AS text) IS NULL OR d.trang_thai = :tt)
      AND (CAST(:t AS smallint) IS NULL OR d.ma_tinh = :t)
      AND (CAST(:nhom AS text) IS NULL OR l.nhom = :nhom)
      AND (CAST(:ml AS smallint) IS NULL OR d.ma_loai = :ml)
      AND (CAST(:st AS smallint) IS NULL OR EXISTS (SELECT 1 FROM dia_diem_so_thich s
            WHERE s.ma_dia_diem = d.ma_dia_diem AND s.ma_so_thich = :st))
      AND (CAST(:q AS text) IS NULL OR unaccent(lower(d.ten)) LIKE '%' || unaccent(lower(:q)) || '%')"""
    p = {"chi_hien": chi_hien, "tt": trang_thai, "t": ma_tinh, "nhom": nhom, "ml": ma_loai, "st": ma_so_thich,
         "q": q, "lim": kich_thuoc, "off": (trang - 1) * kich_thuoc}
    tong = conn.execute(text("SELECT count(*)" + _TU + where), p).scalar_one()
    # Sắp xếp công khai: điểm đánh giá (khi đủ 3 lượt) rồi tên; không có hệ số thương mại
    rows = conn.execute(text(_CHON + _TU + where +
                             " ORDER BY (d.so_luot_danh_gia >= 3) DESC, d.diem_tb DESC NULLS LAST, d.ten, d.ma_dia_diem"
                             " LIMIT :lim OFFSET :off"), p).mappings().all()
    return rows, tong


def lay(conn: Connection, ma: int, khoa: bool = False):
    if khoa:
        conn.execute(text("SELECT 1 FROM dia_diem WHERE ma_dia_diem = :m FOR UPDATE"), {"m": ma})
    return conn.execute(text(_CHON + _CHI_TIET + _TU + " WHERE d.ma_dia_diem = :m"), {"m": ma}).mappings().first()


def tao(conn: Connection, du_lieu: dict) -> int:
    return chen(conn, "dia_diem", "ma_dia_diem", du_lieu, COT_DIA_DIEM)


def sua_dia_diem(conn: Connection, ma: int, du_lieu: dict) -> None:
    sua(conn, "dia_diem", "ma_dia_diem", ma, du_lieu, COT_DIA_DIEM, them_set="ngay_cap_nhat = now()")


def dat_gio_mo_cua(conn: Connection, ma: int, ds: list[dict]) -> None:
    conn.execute(text("DELETE FROM gio_mo_cua WHERE ma_dia_diem = :m"), {"m": ma})
    for g in ds:
        conn.execute(text("INSERT INTO gio_mo_cua (ma_dia_diem, thu_trong_tuan, ca, gio_mo, gio_dong) "
                          "VALUES (:m, :thu, :ca, :mo, :dong)"),
                     {"m": ma, "thu": g["thu_trong_tuan"], "ca": g["ca"], "mo": g["gio_mo"], "dong": g["gio_dong"]})


def dat_gia_ve(conn: Connection, ma: int, ds: list[dict]) -> None:
    conn.execute(text("DELETE FROM gia_ve WHERE ma_dia_diem = :m"), {"m": ma})
    for v in ds:
        conn.execute(text("INSERT INTO gia_ve (ma_dia_diem, loai_khach, dieu_kien, gia) VALUES (:m, :lk, :dk, :g)"),
                     {"m": ma, "lk": v["loai_khach"], "dk": v.get("dieu_kien"), "g": v["gia"]})


def dat_so_thich(conn: Connection, ma: int, ds: list[int]) -> None:
    thay_bang_noi(conn, "dia_diem_so_thich", "ma_dia_diem", ma, "ma_so_thich", ds)


def doi_trang_thai(conn: Connection, ma: int, trang_thai: str) -> None:
    conn.execute(text("UPDATE dia_diem SET trang_thai = :tt, ngay_cap_nhat = now() WHERE ma_dia_diem = :m"),
                 {"tt": trang_thai, "m": ma})
