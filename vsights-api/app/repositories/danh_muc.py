"""SQL danh mục (tỉnh, tiện nghi, sở thích, loại địa điểm) và nhật ký quản trị."""
from sqlalchemy import Connection, text


def tinh_thanh(conn: Connection):
    return conn.execute(text(
        "SELECT t.ma_tinh, t.ten_tinh, t.ma_vung, v.ten_vung FROM tinh_thanh t JOIN vung_mien v USING (ma_vung) "
        "ORDER BY t.ma_vung, t.ten_tinh")).mappings().all()


def tinh_ton_tai(conn: Connection, ma_tinh: int) -> bool:
    return conn.execute(text("SELECT EXISTS (SELECT 1 FROM tinh_thanh WHERE ma_tinh = :t)"), {"t": ma_tinh}).scalar()


def tien_nghi(conn: Connection):
    return conn.execute(text("SELECT ma_tien_nghi, ten_tien_nghi, pham_vi FROM tien_nghi ORDER BY pham_vi, ma_tien_nghi")).mappings().all()


def so_thich(conn: Connection):
    return conn.execute(text("SELECT ma_so_thich, ten, pham_vi FROM so_thich ORDER BY ma_so_thich")).mappings().all()


def loai_dia_diem(conn: Connection):
    return conn.execute(text("SELECT ma_loai, ten_loai, nhom FROM loai_dia_diem ORDER BY nhom DESC, ma_loai")).mappings().all()


def tien_nghi_sai_pham_vi(conn: Connection, ma: list[int], pham_vi: str) -> list[int]:
    """Trả các mã không tồn tại hoặc không thuộc phạm vi (co_so / phong)."""
    if not ma:
        return []
    dung = set(conn.execute(text("SELECT ma_tien_nghi FROM tien_nghi WHERE ma_tien_nghi = ANY(:m) AND pham_vi = :p"),
                            {"m": ma, "p": pham_vi}).scalars())
    return sorted(set(ma) - dung)


def so_thich_khong_ton_tai(conn: Connection, ma: list[int]) -> list[int]:
    if not ma:
        return []
    co = set(conn.execute(text("SELECT ma_so_thich FROM so_thich WHERE ma_so_thich = ANY(:m)"), {"m": ma}).scalars())
    return sorted(set(ma) - co)


def ghi_nhat_ky(conn: Connection, ma_quan_tri: int, hanh_dong: str, doi_tuong: str, ma_doi_tuong: int | None,
                ly_do: str | None = None) -> None:
    conn.execute(text(
        "INSERT INTO nhat_ky_quan_tri (ma_quan_tri, hanh_dong, doi_tuong, ma_doi_tuong, ly_do) "
        "VALUES (:q, :h, :d, :m, :l)"), {"q": ma_quan_tri, "h": hanh_dong, "d": doi_tuong, "m": ma_doi_tuong, "l": ly_do})


def khoa_tu_van(conn: Connection, *phan: object) -> None:
    """pg_advisory_xact_lock theo khoá nghiệp vụ; tự nhả khi giao dịch kết thúc."""
    conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": "|".join(map(str, phan))})
