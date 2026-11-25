"""Phụ thuộc dùng chung cho Controller: kết nối, người dùng hiện tại, quyền quản trị, kiểm Origin."""
import ipaddress

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Connection

from app.core.config import cai_dat
from app.core.db import lay_ket_noi
from app.core.errors import AppError
from app.services import xac_thuc

_bearer = HTTPBearer(auto_error=False)


def nguoi_dung(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
               conn: Connection = Depends(lay_ket_noi)) -> dict:
    return xac_thuc.nguoi_dung_hien_tai(conn, cred.credentials if cred else None)


def quan_tri(nd: dict = Depends(nguoi_dung)) -> dict:
    # Vai trò lấy từ CSDL (trong nguoi_dung_hien_tai), nên sửa claim trong token không có tác dụng
    if nd["vai_tro"] != "quan_tri":
        raise AppError(403, "KHONG_DU_QUYEN", "Bạn không có quyền thực hiện thao tác này.")
    return nd


def kiem_origin(request: Request) -> None:
    """Chống CSRF cho 3 endpoint dùng cookie: chỉ nhận Origin trong danh sách (thiếu Origin cũng bị chặn)."""
    if request.headers.get("origin") not in cai_dat().origin_hop_le:
        raise AppError(403, "NGUON_KHONG_HOP_LE", "Yêu cầu đến từ nguồn không được phép.")


def ip_khach(request: Request) -> str:
    # Chạy sau reverse proxy thì thay bằng IP từ X-Forwarded-For đã được proxy tin cậy ghi.
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host))
    except (TypeError, ValueError):
        return "0.0.0.0"


def phan_trang(trang: int = Query(1, ge=1, le=10000), kich_thuoc: int = Query(20, ge=1, le=100)) -> tuple[int, int]:
    return trang, kich_thuoc


def trang_ra(items, tong: int, trang: int, kich_thuoc: int) -> dict:
    return {"items": [dict(i) for i in items], "tong": tong, "trang": trang, "kich_thuoc": kich_thuoc}
