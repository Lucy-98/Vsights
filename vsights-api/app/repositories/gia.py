"""SQL cho chi tiết chỗ ở và bảng giá từng đêm (T-013, UC03, D-021, D-029(1), D-035).

Chỉ đọc. Lấy giá của MỌI loại phòng đang hiện × MỌI liên kết OTA đang hoạt động (OTA đang hoạt động) trong
một dải ngày; phần quy đổi thuế, phí và chọn rẻ nhất làm ở services/gia.py để dùng chung một quy tắc với
/stays/search (repositories/tim_kiem.py).
"""
from datetime import date

from sqlalchemy import Connection, text


def co_so_hien(conn: Connection, ma: int):
    return conn.execute(text(
        "SELECT cs.ma_co_so, cs.ma_tinh, cs.ten, cs.loai_hinh, cs.dia_chi, cs.khu_vuc, cs.hang_sao, cs.vi_do, "
        "cs.kinh_do, cs.diem_tb, cs.so_luot_danh_gia, cs.la_du_lieu_mau, cs.mo_ta, "
        "COALESCE((SELECT array_agg(t.ten_tien_nghi ORDER BY t.ma_tien_nghi) FROM co_so_tien_nghi x "
        "          JOIN tien_nghi t USING (ma_tien_nghi) WHERE x.ma_co_so = cs.ma_co_so), '{}') AS tien_nghi, "
        "COALESCE((SELECT array_agg(s.ten ORDER BY s.ma_so_thich) FROM co_so_so_thich x "
        "          JOIN so_thich s USING (ma_so_thich) WHERE x.ma_co_so = cs.ma_co_so), '{}') AS so_thich "
        "FROM co_so_luu_tru cs WHERE cs.ma_co_so = :m AND cs.trang_thai = 'hien'"), {"m": ma}).mappings().first()


def loai_phong_hien(conn: Connection, ma_co_so: int):
    return conn.execute(text(
        "SELECT lp.ma_loai_phong, lp.ten_loai_phong, lp.loai_giuong, lp.suc_chua_nl, lp.suc_chua_te, lp.dien_tich, "
        "lp.co_bua_sang, lp.thanh_toan_tai_cho, lp.so_ngay_huy_mien_phi, lp.dieu_kien_huy, "
        "COALESCE((SELECT array_agg(t.ten_tien_nghi ORDER BY t.ma_tien_nghi) FROM loai_phong_tien_nghi x "
        "          JOIN tien_nghi t USING (ma_tien_nghi) WHERE x.ma_loai_phong = lp.ma_loai_phong), '{}') AS tien_nghi "
        "FROM loai_phong lp WHERE lp.ma_co_so = :m AND lp.trang_thai = 'hien' ORDER BY lp.ma_loai_phong"),
        {"m": ma_co_so}).mappings().all()


def gia_trong_dai(conn: Connection, ma_co_so: int, tu: date, den: date):
    """Mọi giá trong [tu, den) — đọc bằng khoá chính phủ của gia_tham_khao, mỗi cặp một đoạn chỉ mục."""
    return conn.execute(text(
        "SELECT g.ma_loai_phong, lk.ma_lien_ket, o.ten_ota, lk.url, o.ty_le_thue_phi, "
        "       g.ngay, g.gia_dem, g.gom_thue_phi, g.ngay_cap_nhat "
        "FROM loai_phong lp "
        "JOIN lien_ket_ota lk ON lk.ma_co_so = lp.ma_co_so AND lk.trang_thai = 'hoat_dong' "
        "JOIN nguon_ota o     ON o.ma_ota = lk.ma_ota AND o.trang_thai = 'hoat_dong' "
        "JOIN gia_tham_khao g ON g.ma_loai_phong = lp.ma_loai_phong AND g.ma_lien_ket = lk.ma_lien_ket "
        "                    AND g.ngay >= :tu AND g.ngay < :den "
        "WHERE lp.ma_co_so = :m AND lp.trang_thai = 'hien' "
        "ORDER BY g.ma_loai_phong, o.ten_ota, g.ngay"),
        {"m": ma_co_so, "tu": tu, "den": den}).mappings().all()
