"""Nghiệp vụ quản trị danh mục: chỗ ở, loại phòng, địa điểm (UC14). "Xoá" = ẩn kèm lý do; không xoá cứng.
Mọi thao tác ghi kèm một dòng NHAT_KY_QUAN_TRI trong cùng giao dịch."""
from sqlalchemy import Connection

from app.core.errors import AppError, khong_tim_thay
from app.repositories import cho_o as repo_cs
from app.repositories import danh_muc as repo_dm
from app.repositories import dia_diem as repo_dd


def _kiem_tien_nghi(conn: Connection, ma: list[int] | None, pham_vi: str) -> None:
    sai = repo_dm.tien_nghi_sai_pham_vi(conn, ma or [], pham_vi)
    if sai:
        raise AppError(422, "TIEN_NGHI_KHONG_HOP_LE",
                       f"Mã tiện nghi không tồn tại hoặc không thuộc phạm vi '{pham_vi}'.", {"ma_tien_nghi": sai})


def _doi_trang_thai(trang_thai_cu: str, moi: str) -> None:
    if trang_thai_cu == moi:
        raise AppError(409, "TRANG_THAI_KHONG_DOI", "Bản ghi đã ở trạng thái này.", {"trang_thai": moi})


# ---------------- Chỗ ở ----------------
def tao_co_so(conn: Connection, qt: int, du_lieu: dict) -> dict:
    tn = du_lieu.pop("ma_tien_nghi", [])
    with conn.begin():
        _kiem_tien_nghi(conn, tn, "co_so")
        # Khoá tư vấn theo (tỉnh, tên, địa chỉ): yêu cầu song song cùng cơ sở xếp hàng, chỉ 1 cái tạo được
        repo_dm.khoa_tu_van(conn, "co_so", du_lieu["ma_tinh"], du_lieu["ten"].lower(), du_lieu["dia_chi"].lower())
        trung = repo_cs.co_so_trung(conn, du_lieu["ma_tinh"], du_lieu["ten"], du_lieu["dia_chi"])
        if trung:
            raise AppError(409, "CO_SO_DA_TON_TAI", "Đã có chỗ ở cùng tỉnh, tên và địa chỉ.", {"ma_co_so": trung})
        ma = repo_cs.tao_co_so(conn, du_lieu)
        repo_cs.dat_tien_nghi_co_so(conn, ma, tn)
        repo_dm.ghi_nhat_ky(conn, qt, "tao", "co_so_luu_tru", ma)
        return dict(repo_cs.lay_co_so(conn, ma))


def sua_co_so(conn: Connection, qt: int, ma: int, du_lieu: dict) -> dict:
    tn = du_lieu.pop("ma_tien_nghi", None)
    with conn.begin():
        cu = repo_cs.lay_co_so(conn, ma, khoa=True)
        if cu is None:
            raise khong_tim_thay("chỗ ở")
        if tn is not None:
            _kiem_tien_nghi(conn, tn, "co_so")
        if {"ma_tinh", "ten", "dia_chi"} & du_lieu.keys():
            t, ten, dc = (du_lieu.get(k, cu[k]) for k in ("ma_tinh", "ten", "dia_chi"))
            repo_dm.khoa_tu_van(conn, "co_so", t, ten.lower(), dc.lower())
            trung = repo_cs.co_so_trung(conn, t, ten, dc, tru_ma=ma)
            if trung:
                raise AppError(409, "CO_SO_DA_TON_TAI", "Đã có chỗ ở cùng tỉnh, tên và địa chỉ.", {"ma_co_so": trung})
        repo_cs.sua_co_so(conn, ma, du_lieu)
        if tn is not None:
            repo_cs.dat_tien_nghi_co_so(conn, ma, tn)
        repo_dm.ghi_nhat_ky(conn, qt, "sua", "co_so_luu_tru", ma)
        return dict(repo_cs.lay_co_so(conn, ma))


def an_hien_co_so(conn: Connection, qt: int, ma: int, trang_thai: str, ly_do: str | None) -> dict:
    with conn.begin():
        cu = repo_cs.lay_co_so(conn, ma, khoa=True)
        if cu is None:
            raise khong_tim_thay("chỗ ở")
        _doi_trang_thai(cu["trang_thai"], trang_thai)
        repo_cs.doi_trang_thai_co_so(conn, ma, trang_thai)
        repo_dm.ghi_nhat_ky(conn, qt, trang_thai, "co_so_luu_tru", ma, ly_do)
        return dict(repo_cs.lay_co_so(conn, ma))


# ---------------- Loại phòng ----------------
def tao_loai_phong(conn: Connection, qt: int, ma_co_so: int, du_lieu: dict) -> dict:
    tn = du_lieu.pop("ma_tien_nghi", [])
    with conn.begin():
        if repo_cs.lay_co_so(conn, ma_co_so, khoa=True) is None:
            raise khong_tim_thay("chỗ ở")
        _kiem_tien_nghi(conn, tn, "phong")
        ma = repo_cs.tao_loai_phong(conn, {**du_lieu, "ma_co_so": ma_co_so})
        repo_cs.dat_tien_nghi_loai_phong(conn, ma, tn)
        repo_dm.ghi_nhat_ky(conn, qt, "tao", "loai_phong", ma)
        return dict(repo_cs.lay_loai_phong(conn, ma))


def sua_loai_phong(conn: Connection, qt: int, ma: int, du_lieu: dict) -> dict:
    tn = du_lieu.pop("ma_tien_nghi", None)
    with conn.begin():
        if repo_cs.lay_loai_phong(conn, ma, khoa=True) is None:
            raise khong_tim_thay("loại phòng")
        if tn is not None:
            _kiem_tien_nghi(conn, tn, "phong")
        repo_cs.sua_loai_phong(conn, ma, du_lieu)
        if tn is not None:
            repo_cs.dat_tien_nghi_loai_phong(conn, ma, tn)
        repo_dm.ghi_nhat_ky(conn, qt, "sua", "loai_phong", ma)
        return dict(repo_cs.lay_loai_phong(conn, ma))


def an_hien_loai_phong(conn: Connection, qt: int, ma: int, trang_thai: str, ly_do: str | None) -> dict:
    with conn.begin():
        cu = repo_cs.lay_loai_phong(conn, ma, khoa=True)
        if cu is None:
            raise khong_tim_thay("loại phòng")
        _doi_trang_thai(cu["trang_thai"], trang_thai)
        repo_cs.doi_trang_thai_loai_phong(conn, ma, trang_thai)
        repo_dm.ghi_nhat_ky(conn, qt, trang_thai, "loai_phong", ma, ly_do)
        return dict(repo_cs.lay_loai_phong(conn, ma))


# ---------------- Địa điểm ----------------
def _kiem_dia_diem(conn: Connection, du_lieu: dict, cu: dict | None = None) -> None:
    tu = du_lieu.get("muc_gia_nguoi_tu", cu["muc_gia_nguoi_tu"] if cu else None)
    den = du_lieu.get("muc_gia_nguoi_den", cu["muc_gia_nguoi_den"] if cu else None)
    if tu is not None and den is not None and den < tu:
        raise AppError(422, "KHOANG_GIA_KHONG_HOP_LE", "Mức giá đến phải lớn hơn hoặc bằng mức giá từ.")
    sai = repo_dm.so_thich_khong_ton_tai(conn, du_lieu.get("ma_so_thich") or [])
    if sai:
        raise AppError(422, "SO_THICH_KHONG_HOP_LE", "Mã sở thích không tồn tại.", {"ma_so_thich": sai})
    gio = du_lieu.get("gio_mo_cua") or []
    if len({(g["thu_trong_tuan"], g["ca"]) for g in gio}) != len(gio):
        raise AppError(422, "GIO_MO_CUA_TRUNG", "Mỗi (thứ, ca) chỉ được khai một lần.")


def _ghi_bang_con_dia_diem(conn: Connection, ma: int, du_lieu: dict) -> None:
    if du_lieu.get("gio_mo_cua") is not None:
        repo_dd.dat_gio_mo_cua(conn, ma, du_lieu["gio_mo_cua"])
    if du_lieu.get("gia_ve") is not None:
        repo_dd.dat_gia_ve(conn, ma, du_lieu["gia_ve"])
    if du_lieu.get("ma_so_thich") is not None:
        repo_dd.dat_so_thich(conn, ma, du_lieu["ma_so_thich"])


def tao_dia_diem(conn: Connection, qt: int, du_lieu: dict) -> dict:
    with conn.begin():
        _kiem_dia_diem(conn, du_lieu)
        ma = repo_dd.tao(conn, du_lieu)
        _ghi_bang_con_dia_diem(conn, ma, du_lieu)
        repo_dm.ghi_nhat_ky(conn, qt, "tao", "dia_diem", ma)
        return dict(repo_dd.lay(conn, ma))


def sua_dia_diem(conn: Connection, qt: int, ma: int, du_lieu: dict) -> dict:
    with conn.begin():
        cu = repo_dd.lay(conn, ma, khoa=True)
        if cu is None:
            raise khong_tim_thay("địa điểm")
        _kiem_dia_diem(conn, du_lieu, cu)
        repo_dd.sua_dia_diem(conn, ma, du_lieu)
        _ghi_bang_con_dia_diem(conn, ma, du_lieu)
        repo_dm.ghi_nhat_ky(conn, qt, "sua", "dia_diem", ma)
        return dict(repo_dd.lay(conn, ma))


def an_hien_dia_diem(conn: Connection, qt: int, ma: int, trang_thai: str, ly_do: str | None) -> dict:
    with conn.begin():
        cu = repo_dd.lay(conn, ma, khoa=True)
        if cu is None:
            raise khong_tim_thay("địa điểm")
        _doi_trang_thai(cu["trang_thai"], trang_thai)
        repo_dd.doi_trang_thai(conn, ma, trang_thai)
        repo_dm.ghi_nhat_ky(conn, qt, trang_thai, "dia_diem", ma, ly_do)
        return dict(repo_dd.lay(conn, ma))
