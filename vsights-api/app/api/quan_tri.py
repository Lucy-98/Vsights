"""/admin — CRUD chỗ ở, loại phòng, địa điểm cho quản trị viên. Không có DELETE: "Xoá" = POST .../an {ly_do}."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app.api.deps import phan_trang, quan_tri, trang_ra
from app.api.schemas import AnVao, CoSoSua, CoSoTao, DiaDiemSua, DiaDiemTao, LoaiPhongSua, LoaiPhongTao
from app.core.db import lay_ket_noi
from app.core.errors import khong_tim_thay
from app.repositories import cho_o as repo_cs
from app.repositories import dia_diem as repo_dd
from app.services import quan_tri as sv

_LOI = {401: {"description": "Thiếu hoặc sai token"}, 403: {"description": "KHONG_DU_QUYEN"},
        404: {"description": "KHONG_TIM_THAY"}, 409: {"description": "TRANG_THAI_KHONG_DOI / CO_SO_DA_TON_TAI"}}
router = APIRouter(prefix="/admin", responses=_LOI)
TrangThai = Literal["hien", "an"]


def _dump(m) -> dict:
    return m.model_dump(mode="python", exclude_unset=True)


# ---------------- Chỗ ở ----------------
@router.get("/stays", tags=["Quản trị: chỗ ở"])
def ds_co_so(ma_tinh: int | None = Query(None, ge=1), trang_thai: TrangThai | None = None,
             q: str | None = Query(None, max_length=100), pt=Depends(phan_trang),
             _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    rows, tong = repo_cs.danh_sach_co_so(conn, ma_tinh, trang_thai, q, *pt)
    return trang_ra(rows, tong, *pt)


@router.post("/stays", status_code=201, tags=["Quản trị: chỗ ở"])
def tao_co_so(vao: CoSoTao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.tao_co_so(conn, qt["ma_nguoi_dung"], vao.model_dump(mode="python"))


@router.get("/stays/{ma}", tags=["Quản trị: chỗ ở"])
def xem_co_so(ma: int, _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    cs = repo_cs.lay_co_so(conn, ma)
    if cs is None:
        raise khong_tim_thay("chỗ ở")
    return dict(cs)


@router.patch("/stays/{ma}", tags=["Quản trị: chỗ ở"])
def sua_co_so(ma: int, vao: CoSoSua, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.sua_co_so(conn, qt["ma_nguoi_dung"], ma, _dump(vao))


@router.post("/stays/{ma}/an", tags=["Quản trị: chỗ ở"], summary="Ẩn chỗ ở kèm lý do (thay cho xoá)")
def an_co_so(ma: int, vao: AnVao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_co_so(conn, qt["ma_nguoi_dung"], ma, "an", vao.ly_do)


@router.post("/stays/{ma}/hien", tags=["Quản trị: chỗ ở"], summary="Hiện lại chỗ ở đã ẩn")
def hien_co_so(ma: int, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_co_so(conn, qt["ma_nguoi_dung"], ma, "hien", None)


# ---------------- Loại phòng ----------------
@router.get("/stays/{ma}/room-types", tags=["Quản trị: loại phòng"])
def ds_loai_phong(ma: int, _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    if repo_cs.lay_co_so(conn, ma) is None:
        raise khong_tim_thay("chỗ ở")
    return [dict(r) for r in repo_cs.loai_phong_cua_co_so(conn, ma)]


@router.post("/stays/{ma}/room-types", status_code=201, tags=["Quản trị: loại phòng"])
def tao_loai_phong(ma: int, vao: LoaiPhongTao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.tao_loai_phong(conn, qt["ma_nguoi_dung"], ma, vao.model_dump(mode="python"))


@router.get("/room-types/{ma}", tags=["Quản trị: loại phòng"])
def xem_loai_phong(ma: int, _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    lp = repo_cs.lay_loai_phong(conn, ma)
    if lp is None:
        raise khong_tim_thay("loại phòng")
    return dict(lp)


@router.patch("/room-types/{ma}", tags=["Quản trị: loại phòng"])
def sua_loai_phong(ma: int, vao: LoaiPhongSua, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.sua_loai_phong(conn, qt["ma_nguoi_dung"], ma, _dump(vao))


@router.post("/room-types/{ma}/an", tags=["Quản trị: loại phòng"])
def an_loai_phong(ma: int, vao: AnVao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_loai_phong(conn, qt["ma_nguoi_dung"], ma, "an", vao.ly_do)


@router.post("/room-types/{ma}/hien", tags=["Quản trị: loại phòng"])
def hien_loai_phong(ma: int, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_loai_phong(conn, qt["ma_nguoi_dung"], ma, "hien", None)


# ---------------- Địa điểm ----------------
@router.get("/places", tags=["Quản trị: địa điểm"])
def ds_dia_diem(ma_tinh: int | None = Query(None, ge=1), nhom: Literal["tham_quan", "an_uong"] | None = None,
                trang_thai: TrangThai | None = None, q: str | None = Query(None, max_length=100),
                pt=Depends(phan_trang), _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    rows, tong = repo_dd.tim(conn, chi_hien=False, ma_tinh=ma_tinh, nhom=nhom, q=q, trang_thai=trang_thai,
                             trang=pt[0], kich_thuoc=pt[1])
    return trang_ra(rows, tong, *pt)


@router.post("/places", status_code=201, tags=["Quản trị: địa điểm"])
def tao_dia_diem(vao: DiaDiemTao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.tao_dia_diem(conn, qt["ma_nguoi_dung"], vao.model_dump(mode="python"))


@router.get("/places/{ma}", tags=["Quản trị: địa điểm"])
def xem_dia_diem(ma: int, _: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    d = repo_dd.lay(conn, ma)
    if d is None:
        raise khong_tim_thay("địa điểm")
    return dict(d)


@router.patch("/places/{ma}", tags=["Quản trị: địa điểm"])
def sua_dia_diem(ma: int, vao: DiaDiemSua, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.sua_dia_diem(conn, qt["ma_nguoi_dung"], ma, _dump(vao))


@router.post("/places/{ma}/an", tags=["Quản trị: địa điểm"])
def an_dia_diem(ma: int, vao: AnVao, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_dia_diem(conn, qt["ma_nguoi_dung"], ma, "an", vao.ly_do)


@router.post("/places/{ma}/hien", tags=["Quản trị: địa điểm"])
def hien_dia_diem(ma: int, qt: dict = Depends(quan_tri), conn: Connection = Depends(lay_ket_noi)):
    return sv.an_hien_dia_diem(conn, qt["ma_nguoi_dung"], ma, "hien", None)
