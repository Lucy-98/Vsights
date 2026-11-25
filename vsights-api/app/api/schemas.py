"""Schema Pydantic cho dữ liệu vào. Chỉ kiểm hình thức; quy tắc nghiệp vụ nằm ở Service."""
from datetime import time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

LoaiHinh = Literal["khach_san", "homestay", "resort", "can_ho", "nha_nghi"]


class _Goc(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DangNhapVao(_Goc):
    email: EmailStr
    mat_khau: str = Field(min_length=1, max_length=128)
    thiet_bi: str | None = Field(default=None, max_length=200)


class TokenRa(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AnVao(_Goc):
    ly_do: str = Field(min_length=3, max_length=500)


# ---------------- Chỗ ở ----------------
class _CoSoChung(_Goc):
    khu_vuc: str | None = Field(default=None, max_length=100)
    vi_do: Decimal | None = Field(default=None, ge=-90, le=90)
    kinh_do: Decimal | None = Field(default=None, ge=-180, le=180)
    hang_sao: int | None = Field(default=None, ge=1, le=5)
    mo_ta: str | None = None
    gio_nhan_phong: time | None = None
    gio_tra_phong: time | None = None
    chinh_sach_huy: str | None = None
    chinh_sach_khac: str | None = None


class CoSoTao(_CoSoChung):
    ma_tinh: int = Field(ge=1)
    ten: str = Field(min_length=2, max_length=200)
    loai_hinh: LoaiHinh
    dia_chi: str = Field(min_length=5, max_length=300)
    la_du_lieu_mau: bool = False
    ma_tien_nghi: list[int] = Field(default_factory=list, max_length=50)


class CoSoSua(_CoSoChung):
    ma_tinh: int | None = Field(default=None, ge=1)
    ten: str | None = Field(default=None, min_length=2, max_length=200)
    loai_hinh: LoaiHinh | None = None
    dia_chi: str | None = Field(default=None, min_length=5, max_length=300)
    la_du_lieu_mau: bool | None = None
    ma_tien_nghi: list[int] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _khong_rong_bat_buoc(self):
        for f in ("ma_tinh", "ten", "loai_hinh", "dia_chi", "la_du_lieu_mau"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} không được để rỗng")
        return self


# ---------------- Loại phòng ----------------
class _LoaiPhongChung(_Goc):
    loai_giuong: str | None = Field(default=None, max_length=100)
    dien_tich: Decimal | None = Field(default=None, gt=0, le=9999)
    dieu_kien_huy: str | None = None
    thanh_toan_tai_cho: bool | None = None                        # D-031(2)
    so_ngay_huy_mien_phi: int | None = Field(default=None, ge=0, le=60)  # D-031(2), ngày


class LoaiPhongTao(_LoaiPhongChung):
    ten_loai_phong: str = Field(min_length=2, max_length=150)
    suc_chua_nl: int = Field(ge=1, le=20)
    suc_chua_te: int = Field(default=0, ge=0, le=10)
    co_bua_sang: bool = False
    ma_tien_nghi: list[int] = Field(default_factory=list, max_length=50)


class LoaiPhongSua(_LoaiPhongChung):
    ten_loai_phong: str | None = Field(default=None, min_length=2, max_length=150)
    suc_chua_nl: int | None = Field(default=None, ge=1, le=20)
    suc_chua_te: int | None = Field(default=None, ge=0, le=10)
    co_bua_sang: bool | None = None
    ma_tien_nghi: list[int] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _khong_rong_bat_buoc(self):
        for f in ("ten_loai_phong", "suc_chua_nl", "suc_chua_te", "co_bua_sang"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} không được để rỗng")
        return self


# ---------------- Địa điểm ----------------
class GioMoCua(_Goc):
    thu_trong_tuan: int = Field(ge=1, le=7)
    ca: int = Field(default=1, ge=1, le=3)
    gio_mo: time
    gio_dong: time

    @model_validator(mode="after")
    def _thu_tu(self):
        if self.gio_dong <= self.gio_mo:
            raise ValueError("gio_dong phải sau gio_mo")
        return self


class GiaVe(_Goc):
    loai_khach: str = Field(min_length=1, max_length=60)
    dieu_kien: str | None = Field(default=None, max_length=200)
    gia: int = Field(ge=0)


class _DiaDiemChung(_Goc):
    dia_chi: str | None = Field(default=None, max_length=300)
    vi_do: Decimal | None = Field(default=None, ge=-90, le=90)
    kinh_do: Decimal | None = Field(default=None, ge=-180, le=180)
    mo_ta: str | None = None
    luu_y: str | None = None
    thoi_diem_dep: str | None = Field(default=None, max_length=100)
    thoi_luong_goi_y: int | None = Field(default=None, ge=5, le=1440)
    muc_gia_nguoi_tu: int | None = Field(default=None, ge=0)
    muc_gia_nguoi_den: int | None = Field(default=None, ge=0)
    lien_ket_mua_ve: str | None = Field(default=None, max_length=500)

    @field_validator("lien_ket_mua_ve")
    @classmethod
    def _url(cls, v):
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("lien_ket_mua_ve phải là URL http(s)")
        return v


class DiaDiemTao(_DiaDiemChung):
    ma_tinh: int = Field(ge=1)
    ma_loai: int = Field(ge=1)
    ten: str = Field(min_length=2, max_length=200)
    la_du_lieu_mau: bool = False
    gio_mo_cua: list[GioMoCua] = Field(default_factory=list, max_length=21)
    gia_ve: list[GiaVe] = Field(default_factory=list, max_length=20)
    ma_so_thich: list[int] = Field(default_factory=list, max_length=20)


class DiaDiemSua(_DiaDiemChung):
    ma_tinh: int | None = Field(default=None, ge=1)
    ma_loai: int | None = Field(default=None, ge=1)
    ten: str | None = Field(default=None, min_length=2, max_length=200)
    la_du_lieu_mau: bool | None = None
    gio_mo_cua: list[GioMoCua] | None = Field(default=None, max_length=21)
    gia_ve: list[GiaVe] | None = Field(default=None, max_length=20)
    ma_so_thich: list[int] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _khong_rong_bat_buoc(self):
        for f in ("ma_tinh", "ma_loai", "ten", "la_du_lieu_mau"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} không được để rỗng")
        return self
