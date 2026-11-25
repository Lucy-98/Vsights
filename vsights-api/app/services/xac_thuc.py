"""Nghiệp vụ đăng nhập, làm mới, đăng xuất, đọc người dùng hiện tại (base/02 mục 5)."""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Connection

from app.core.config import cai_dat
from app.core.errors import AppError
from app.core.security import bam_token, giai_access_token, kiem_mat_khau, tao_access_token, tao_refresh_token
from app.repositories import xac_thuc as repo


@dataclass
class KetQuaPhien:
    access_token: str
    refresh_token: str
    expires_in: int
    het_han_refresh: datetime


def _cap_phien(conn: Connection, ma_nguoi_dung: int, ho: uuid.UUID, thiet_bi: str | None,
               het_han: datetime) -> KetQuaPhien:
    rt = tao_refresh_token()
    repo.tao_phien(conn, ma_nguoi_dung, ho, bam_token(rt), thiet_bi, het_han)
    return KetQuaPhien(tao_access_token(ma_nguoi_dung, ho), rt, cai_dat().access_ttl_giay, het_han)


def dang_nhap(conn: Connection, email: str, mat_khau: str, ip: str, thiet_bi: str | None) -> KetQuaPhien:
    cd = cai_dat()
    email = email.strip().lower()
    # Giao dịch 1: giữ chỗ lượt thử. Commit ngay để lượt thử được đếm kể cả khi bước sau lỗi.
    with conn.begin():
        luot = repo.giu_cho_luot_thu(conn, email, ip, cd.so_lan_sai_toi_da, cd.phut_khoa)
    if luot["khoa_den"] is not None and luot["khoa_den"] > datetime.now(timezone.utc):
        con_lai = max(1, int((luot["khoa_den"] - datetime.now(timezone.utc)).total_seconds()))
        raise AppError(429, "THU_QUA_NHIEU_LAN", "Bạn đã thử quá nhiều lần. Vui lòng thử lại sau.",
                       {"thu_lai_sau_giay": con_lai}, headers={"Retry-After": str(con_lai)})

    with conn.begin():
        nd = repo.tim_theo_email(conn, email)
        # Luôn chạy Argon2 (hash giả khi không có người dùng) để không lộ email qua thời gian trả lời
        if not kiem_mat_khau(nd["mat_khau_bam"] if nd else None, mat_khau):
            raise AppError(401, "SAI_THONG_TIN", "Email hoặc mật khẩu không đúng.")
        # Chỉ báo các trạng thái này SAU khi mật khẩu đúng (không dò được email)
        if nd["trang_thai"] != "hoat_dong":
            raise AppError(403, "TAI_KHOAN_BI_KHOA", "Tài khoản đang bị khoá.")
        if not nd["email_da_xac_thuc"]:
            raise AppError(403, "EMAIL_CHUA_XAC_THUC", "Vui lòng xác thực email trước khi đăng nhập.")
        repo.xoa_luot_thu(conn, email, ip)
        het_han = datetime.now(timezone.utc) + timedelta(days=cd.refresh_ttl_ngay)
        return _cap_phien(conn, nd["ma_nguoi_dung"], uuid.uuid4(), thiet_bi, het_han)


def lam_moi(conn: Connection, refresh_token: str | None) -> KetQuaPhien:
    if not refresh_token:
        raise AppError(401, "REFRESH_KHONG_HOP_LE", "Phiên đăng nhập không hợp lệ.")
    bi_dung_lai = False
    with conn.begin():
        p = repo.khoa_phien_theo_token(conn, bam_token(refresh_token))
        if p is None or p["da_het_han"]:
            raise AppError(401, "REFRESH_KHONG_HOP_LE", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
        if p["xoay_luc"] is not None:
            # Token đã xoay bị gửi lại → coi như bị đánh cắp, thu hồi cả họ phiên (RFC 9700 mục 4.14)
            repo.xoa_ho_phien(conn, p["ma_ho_phien"])
            bi_dung_lai = True
        else:
            nd = repo.tim_theo_ma(conn, p["ma_nguoi_dung"])
            if nd is None or nd["trang_thai"] != "hoat_dong":
                repo.xoa_ho_phien(conn, p["ma_ho_phien"])
                raise AppError(401, "REFRESH_KHONG_HOP_LE", "Tài khoản không còn hoạt động.")
            repo.danh_dau_da_xoay(conn, p["ma_phien"])
            return _cap_phien(conn, p["ma_nguoi_dung"], p["ma_ho_phien"], p["thiet_bi"], p["het_han"])
    if bi_dung_lai:  # ném sau khi commit việc thu hồi
        raise AppError(401, "REFRESH_BI_DUNG_LAI", "Phát hiện phiên đăng nhập bị dùng lại. Vui lòng đăng nhập lại.")
    raise AssertionError


def dang_xuat(conn: Connection, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    with conn.begin():
        p = repo.khoa_phien_theo_token(conn, bam_token(refresh_token))
        if p is not None:
            repo.xoa_ho_phien(conn, p["ma_ho_phien"])


def nguoi_dung_hien_tai(conn: Connection, access_token: str | None) -> dict:
    if not access_token:
        raise AppError(401, "CHUA_DANG_NHAP", "Vui lòng đăng nhập.", headers={"WWW-Authenticate": "Bearer"})
    claims = giai_access_token(access_token)
    try:
        ma = int(claims["sub"])
        uuid.UUID(claims["sid"])
    except (ValueError, TypeError):
        raise AppError(401, "TOKEN_KHONG_HOP_LE", "Token không hợp lệ.")
    if not repo.ho_phien_con_hieu_luc(conn, claims["sid"], ma):
        raise AppError(401, "PHIEN_DA_HUY", "Phiên đã kết thúc, vui lòng đăng nhập lại.")
    nd = repo.tim_theo_ma(conn, ma)   # vai trò đọc lại từ CSDL, không tin claim trong token
    if nd is None or nd["trang_thai"] != "hoat_dong":
        raise AppError(401, "PHIEN_DA_HUY", "Tài khoản không còn hoạt động.")
    conn.rollback()  # kết thúc giao dịch ngầm của các câu đọc, để Service sau tự mở giao dịch của mình
    return dict(nd)
