"""/auth — đăng nhập JWT + refresh token xoay vòng trong cookie HttpOnly."""
from datetime import timezone

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import Connection

from app.api.deps import ip_khach, kiem_origin, nguoi_dung
from app.api.schemas import DangNhapVao, TokenRa
from app.core.config import cai_dat
from app.core.db import lay_ket_noi
from app.core.errors import AppError
from app.services import xac_thuc

router = APIRouter(prefix="/auth", tags=["Xác thực"])
COOKIE = "vs_refresh"


def cookie_xoa() -> str:
    """Header Set-Cookie xoá vs_refresh, cùng cờ Secure với lúc đặt (theo VS_COOKIE_SECURE) — B-022.
    Nếu lúc xoá có Secure mà lúc đặt không có (http, Safari máy cá nhân), trình duyệt bỏ qua lệnh xoá."""
    return f'{COOKIE}=""; Max-Age=0; Path=/auth; HttpOnly;{" Secure;" if cai_dat().cookie_secure else ""} SameSite=Strict'


def __getattr__(ten: str):
    # Giữ tên cũ _COOKIE_XOA cho mã/ca kiểm thử đang dùng; giá trị luôn tính theo cấu hình hiện tại
    if ten == "_COOKIE_XOA":
        return cookie_xoa()
    raise AttributeError(ten)

_LOI = {401: {"description": "SAI_THONG_TIN / REFRESH_KHONG_HOP_LE / REFRESH_BI_DUNG_LAI"},
        403: {"description": "EMAIL_CHUA_XAC_THUC / TAI_KHOAN_BI_KHOA / NGUON_KHONG_HOP_LE"},
        429: {"description": "THU_QUA_NHIEU_LAN (kèm Retry-After)"}}


def _dat_cookie(resp: Response, kq: xac_thuc.KetQuaPhien) -> None:
    resp.set_cookie(COOKIE, kq.refresh_token, expires=kq.het_han_refresh.astimezone(timezone.utc), httponly=True,
                    secure=cai_dat().cookie_secure, samesite="strict", path="/auth")


def _xoa_cookie(resp: Response) -> None:
    resp.delete_cookie(COOKIE, path="/auth", httponly=True, secure=cai_dat().cookie_secure, samesite="strict")


@router.post("/login", response_model=TokenRa, responses=_LOI, dependencies=[Depends(kiem_origin)])
def dang_nhap(vao: DangNhapVao, resp: Response, ip: str = Depends(ip_khach), conn: Connection = Depends(lay_ket_noi)):
    kq = xac_thuc.dang_nhap(conn, vao.email, vao.mat_khau, ip, vao.thiet_bi)
    _dat_cookie(resp, kq)
    resp.headers["Cache-Control"] = "no-store"
    return TokenRa(access_token=kq.access_token, expires_in=kq.expires_in)


@router.post("/refresh", response_model=TokenRa, responses=_LOI, dependencies=[Depends(kiem_origin)])
def lam_moi(resp: Response, vs_refresh: str | None = Cookie(default=None), conn: Connection = Depends(lay_ket_noi)):
    try:
        kq = xac_thuc.lam_moi(conn, vs_refresh)
    except AppError as e:
        # Refresh hỏng thì xoá luôn cookie để trình duyệt không gửi lại token chết
        e.headers = {**(e.headers or {}), "Set-Cookie": cookie_xoa()}
        raise
    _dat_cookie(resp, kq)
    resp.headers["Cache-Control"] = "no-store"
    return TokenRa(access_token=kq.access_token, expires_in=kq.expires_in)


@router.post("/logout", status_code=204, dependencies=[Depends(kiem_origin)])
def dang_xuat(vs_refresh: str | None = Cookie(default=None), conn: Connection = Depends(lay_ket_noi)):
    xac_thuc.dang_xuat(conn, vs_refresh)
    resp = Response(status_code=204)
    _xoa_cookie(resp)
    return resp


@router.get("/me", responses={401: {"description": "TOKEN_HET_HAN / TOKEN_KHONG_HOP_LE / PHIEN_DA_HUY"}})
def toi(nd: dict = Depends(nguoi_dung)):
    return {k: nd[k] for k in ("ma_nguoi_dung", "email", "ho_ten", "vai_tro", "email_da_xac_thuc", "tao_luc")}
