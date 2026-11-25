"""Endpoint công khai (khách vãng lai dùng được): danh mục, địa điểm, tìm chỗ ở."""
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app.api.deps import phan_trang, trang_ra
from app.api.schemas import LoaiHinh
from app.core.db import lay_ket_noi
from app.core.errors import AppError, khong_tim_thay
from app.repositories import danh_muc as repo_dm
from app.repositories import dia_diem as repo_dd
from app.services import gia, so_sanh, tim_kiem
from app.services.hop_dong import ChiTietChoO, Diem, SoSanh

router = APIRouter()
GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/catalog/provinces", tags=["Danh mục"])
def tinh_thanh(conn: Connection = Depends(lay_ket_noi)):
    return [dict(r) for r in repo_dm.tinh_thanh(conn)]


@router.get("/catalog/amenities", tags=["Danh mục"])
def tien_nghi(conn: Connection = Depends(lay_ket_noi)):
    return [dict(r) for r in repo_dm.tien_nghi(conn)]


@router.get("/catalog/interests", tags=["Danh mục"])
def so_thich(conn: Connection = Depends(lay_ket_noi)):
    return [dict(r) for r in repo_dm.so_thich(conn)]


@router.get("/catalog/place-types", tags=["Danh mục"])
def loai_dia_diem(conn: Connection = Depends(lay_ket_noi)):
    return [dict(r) for r in repo_dm.loai_dia_diem(conn)]


@router.get("/places", tags=["Địa điểm, quán ăn"])
def tim_dia_diem(ma_tinh: int | None = Query(None, ge=1), nhom: Literal["tham_quan", "an_uong"] | None = None,
                 ma_loai: int | None = Query(None, ge=1), ma_so_thich: int | None = Query(None, ge=1),
                 q: str | None = Query(None, min_length=1, max_length=100),
                 pt: tuple[int, int] = Depends(phan_trang), conn: Connection = Depends(lay_ket_noi)):
    rows, tong = repo_dd.tim(conn, chi_hien=True, ma_tinh=ma_tinh, nhom=nhom, ma_loai=ma_loai,
                             ma_so_thich=ma_so_thich, q=q.strip() if q else None, trang=pt[0], kich_thuoc=pt[1])
    return trang_ra(rows, tong, *pt)


@router.get("/places/{ma}", tags=["Địa điểm, quán ăn"])
def chi_tiet_dia_diem(ma: int, conn: Connection = Depends(lay_ket_noi)):
    d = repo_dd.lay(conn, ma)
    if d is None or d["trang_thai"] != "hien":
        raise khong_tim_thay("địa điểm")
    return dict(d)


@router.get("/stays/search", tags=["Tìm chỗ ở"],
            responses={422: {"description": "NGAY_KHONG_HOP_LE / QUA_SO_DEM / SO_NGUOI_IT_HON_SO_PHONG"}})
def tim_cho_o(ma_tinh: int = Query(..., ge=1), ngay_nhan: date = Query(...), ngay_tra: date = Query(...),
              so_nguoi: int = Query(2, ge=1, le=60), so_phong: int = Query(1, ge=1, le=20),
              ngan_sach: int | None = Query(None, gt=0),
              loai_ngan_sach: Literal["moi_dem", "ca_chuyen"] = Query("moi_dem",
                  description="Ngân sách tính theo một đêm một phòng (moi_dem) hay cho cả chuyến (ca_chuyen)"),
              loai_hinh: LoaiHinh | None = None,
              ma_tien_nghi: list[int] = Query(default_factory=list, max_length=20),
              ma_so_thich: list[int] = Query(default_factory=list, max_length=20),
              sap_xep: Literal["phu_hop", "gia_tang", "danh_gia"] = "phu_hop",
              pt: tuple[int, int] = Depends(phan_trang), conn: Connection = Depends(lay_ket_noi)):
    return tim_kiem.tim(conn, ma_tinh=ma_tinh, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_nguoi=so_nguoi,
                        so_phong=so_phong, ngan_sach=ngan_sach, loai_ngan_sach=loai_ngan_sach, loai_hinh=loai_hinh,
                        ma_tien_nghi=ma_tien_nghi, ma_so_thich=ma_so_thich, sap_xep=sap_xep, trang=pt[0],
                        kich_thuoc=pt[1], ma_nguoi_dung=None, hom_nay=datetime.now(GIO_VN).date())


def _doc_diem(gia_tri: str) -> Diem:
    loai, _, ma = gia_tri.partition(":")
    if loai not in ("dia_diem", "cho_o") or not ma.isdigit():
        raise AppError(422, "DU_LIEU_KHONG_HOP_LE", "Điểm tham chiếu phải có dạng dia_diem:<mã> hoặc cho_o:<mã>.",
                       {"diem": gia_tri})
    return Diem(loai=loai, ma=int(ma))


@router.get("/stays/compare", tags=["Tìm chỗ ở"], response_model=SoSanh,
            responses={404: {"description": "KHONG_TIM_THAY (chỗ ở hoặc điểm không có / đang ẩn)"},
                       422: {"description": "SO_LUONG_SO_SANH / KHAC_TINH / QUA_SO_DIEM / NGAY_KHONG_HOP_LE / …"}})
def so_sanh_cho_o(ma_co_so: list[int] = Query(..., description="2–3 mã chỗ ở cùng tỉnh"),
                  ngay_nhan: date = Query(...), ngay_tra: date = Query(...),
                  so_nguoi: int = Query(2, ge=1, le=60), so_phong: int = Query(1, ge=1, le=20),
                  ma_tien_nghi: list[int] = Query(default_factory=list, max_length=20),
                  diem: list[str] = Query(default_factory=list, max_length=5,
                                          description="Điểm du khách chọn: dia_diem:<mã> hoặc cho_o:<mã>"),
                  conn: Connection = Depends(lay_ket_noi)):
    """UC09 (W07/M07): so sánh theo các hàng D-022 + D-029(4). Mở cho khách vãng lai; chỉ \"Lưu\" cần đăng nhập."""
    with conn.begin():
        return so_sanh.so_sanh(conn, ma_co_so=ma_co_so, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_nguoi=so_nguoi,
                               so_phong=so_phong, diem_tham_chieu=[_doc_diem(x) for x in diem],
                               hom_nay=datetime.now(GIO_VN).date(), ma_tien_nghi=ma_tien_nghi)


@router.get("/stays/{ma}", tags=["Tìm chỗ ở"], response_model=ChiTietChoO,
            responses={404: {"description": "KHONG_TIM_THAY (không có hoặc đang ẩn)"},
                       422: {"description": "NGAY_KHONG_HOP_LE / QUA_SO_DEM / SO_NGUOI_IT_HON_SO_PHONG"}})
def chi_tiet_cho_o(ma: int, ngay_nhan: date | None = None, ngay_tra: date | None = None,
                   so_nguoi: int = Query(2, ge=1, le=60), so_phong: int = Query(1, ge=1, le=20),
                   conn: Connection = Depends(lay_ket_noi)):
    """UC03: chi tiết chỗ ở; có dải ngày thì kèm bảng giá từng đêm theo OTA, tổng chuyến, lựa chọn rẻ nhất
    (đã gồm thuế, phí — D-021) và tối đa 3 khoảng ngày rẻ hơn (±3 ngày). Mở cho khách vãng lai."""
    with conn.begin():
        return gia.chi_tiet_cho_o(conn, ma_co_so=ma, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_nguoi=so_nguoi,
                                  so_phong=so_phong, hom_nay=datetime.now(GIO_VN).date())
