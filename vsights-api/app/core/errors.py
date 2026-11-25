"""Lỗi thống nhất {ma_loi, thong_bao, chi_tiet}. Service chỉ ném AppError, không biết HTTP."""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, ma_loi: str, thong_bao: str, chi_tiet: Any = None,
                 headers: dict[str, str] | None = None):
        self.status, self.ma_loi, self.thong_bao, self.chi_tiet, self.headers = status, ma_loi, thong_bao, chi_tiet, headers


_log = logging.getLogger("vsights.loi")


def khong_tim_thay(doi_tuong: str) -> AppError:
    return AppError(404, "KHONG_TIM_THAY", f"Không tìm thấy {doi_tuong}.")


def _json(status: int, ma_loi: str, thong_bao: str, chi_tiet: Any = None, headers=None) -> JSONResponse:
    return JSONResponse({"ma_loi": ma_loi, "thong_bao": thong_bao, "chi_tiet": chi_tiet}, status_code=status, headers=headers)


# SQLSTATE → lỗi API. Ràng buộc CSDL là lớp chặn cuối cùng.
_SQLSTATE = {
    "23505": (409, "TRUNG_DU_LIEU", "Dữ liệu bị trùng."),
    "23P01": (409, "TRUNG_KHOANG_NGAY", "Khoảng ngày bị trùng với bản ghi khác."),
    "23503": (422, "MA_KHONG_TON_TAI", "Mã tham chiếu không tồn tại."),
    "23514": (422, "VI_PHAM_RANG_BUOC", "Giá trị không thoả ràng buộc dữ liệu."),
    "22001": (422, "VI_PHAM_RANG_BUOC", "Chuỗi quá dài."),
}


def gan_xu_ly_loi(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app(_: Request, e: AppError):
        return _json(e.status, e.ma_loi, e.thong_bao, e.chi_tiet, e.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        chi_tiet = [
            {"truong": str(err["loc"][-1]) if err.get("loc") else "", "loc": list(err.get("loc", [])),
             "thong_bao": err.get("msg", "")}
            for err in e.errors()
        ]
        return _json(422, "DU_LIEU_KHONG_HOP_LE", "Dữ liệu gửi lên không hợp lệ.", chi_tiet)

    @app.exception_handler(DBAPIError)
    async def _db(request: Request, e: DBAPIError):
        sqlstate = getattr(e.orig, "sqlstate", None)
        if sqlstate in _SQLSTATE:
            status, ma, tb = _SQLSTATE[sqlstate]
            # Tên ràng buộc chỉ ghi log, không trả cho client (B-024: không lộ cấu trúc CSDL)
            rang_buoc = getattr(getattr(e.orig, "diag", None), "constraint_name", None)
            _log.info("Lỗi ràng buộc CSDL %s (%s) tại %s", sqlstate, rang_buoc, request.url.path)
            return _json(status, ma, tb)
        raise e

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        ma = {404: "KHONG_TIM_THAY", 405: "PHUONG_THUC_KHONG_HO_TRO"}.get(e.status_code, "LOI_HTTP")
        return _json(e.status_code, ma, str(e.detail))
