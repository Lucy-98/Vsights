"""Hợp đồng service mà công cụ chatbot gọi (T-024, SA-017). Chốt 2026-11-19, trước hạn 26/11 của AI.

Tệp này CHỈ chứa kiểu dữ liệu và chữ ký (Protocol). SA cài đặt hàm thật ở T-013 (giá, chi tiết), T-014 (so sánh),
T-015 (địa điểm quanh, ước tính di chuyển, xếp lịch trình, lưu/áp dụng), T-016 (đề xuất nhóm). AI viết bản giả lập
theo đúng các Protocol này; khi hàm thật có thì đổi chỗ nối, không đổi công cụ.

Quy ước chung (mọi hàm):
- Tham số đầu là `conn: sqlalchemy.Connection`; mọi tham số khác là keyword-only.
- Hàm ĐỌC không tự mở giao dịch nếu `conn.in_transaction()`; công cụ chatbot gọi trong giao dịch
  `READ ONLY` + `SET LOCAL statement_timeout = '2s'` (lớp chặn thứ hai: công cụ không ghi được).
- Hàm GHI (lich_trinh.*, nhom.*) KHÔNG tự commit: người gọi (luồng xác nhận đề xuất D3) giữ giao dịch.
- Tiền là `int` đồng (VND). Giá dùng để so luôn đã gồm thuế, phí (D-021, D-035). Lớp công cụ của AI tự bỏ số
  tiền trước khi đưa cho mô hình (AI-001); service vẫn trả đủ để `dung_the` dựng thẻ.
- Ngày là `date` theo giờ Việt Nam; `hom_nay` do người gọi truyền (kiểm thử được, không gọi đồng hồ bên trong).
- Lỗi chỉ qua `AppError(status, ma_loi, thong_bao, chi_tiet)`; không lộ tên bảng, ràng buộc (SA-016). Mã lỗi dùng:
  KHONG_TIM_THAY (404, kể cả khi không có quyền — không lộ sự tồn tại), NGAY_KHONG_HOP_LE, QUA_SO_DEM,
  QUA_SO_NGAY (lịch trình > 14 ngày), SO_NGUOI_IT_HON_SO_PHONG, MA_KHONG_TON_TAI, KHAC_TINH (BR-08),
  DEM_DA_DAT (gắn nơi nghỉ vào đêm đã có chỗ ở "Đã đặt"), PHIEN_BAN_DA_DOI (409), CHI_CHU_AP_DUNG (403, BR-13).
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection

PhuongTien = Literal["di_bo", "xe_may", "o_to"]
NhipDo = Literal["thong_tha", "vua", "day"]
KieuNhom = Literal["mot_minh", "cap_doi", "gia_dinh", "ban_be"]
LoaiNganSach = Literal["moi_dem", "ca_chuyen"]
LoaiMuc = Literal["tham_quan", "an_uong", "nghi", "di_chuyen", "tu_do"]


class _Kieu(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Diem(_Kieu):
    """Tham chiếu một chỗ ở (cơ sở lưu trú) hoặc một địa điểm."""
    loai: Literal["cho_o", "dia_diem"]
    ma: int


# =====================================================================  T-013: chi tiết chỗ ở, giá từng đêm
class GiaDem(_Kieu):
    ngay: date
    gia_dem: int                  # mỗi phòng; đã gồm thuế, phí nếu so_sanh_duoc, ngược lại là giá gốc OTA


class GiaOta(_Kieu):
    ma_lien_ket: int
    ten_ota: str
    url: str
    gom_thue_phi_goc: bool        # OTA niêm yết đã gồm thuế, phí?
    so_sanh_duoc: bool            # False = chưa gồm thuế, phí và OTA chưa có tỷ lệ quy đổi → hiện riêng, không so (B-023)
    nhan_thue_phi: str            # "đã gồm thuế, phí" | "đã quy đổi +15% thuế, phí" | "chưa gồm thuế, phí · không so"
    du_dem: bool                  # có giá cho đủ mọi đêm của dải ngày
    dem: list[GiaDem]
    tong_ca_chuyen: int | None    # chỉ khi du_dem; so_sanh_duoc: Σ giá đã gồm + round(Σ chưa gồm × hệ số), × so_phong (= SQL tìm kiếm); không so: Σ giá gốc × so_phong
    cap_nhat_gia: datetime | None  # lần cập nhật CŨ NHẤT trong dải (QC S12)
    gia_cu: bool                  # quá 3 ngày chưa cập nhật → nhãn "Giá có thể đã thay đổi" (BR-03)
    xep_hang_gia: int | None      # 1 = rẻ nhất trong các lựa chọn so_sanh_duoc và du_dem của CƠ SỞ này


class LoaiPhongGia(_Kieu):
    ma_loai_phong: int
    ten_loai_phong: str
    loai_giuong: str | None
    suc_chua_nl: int
    suc_chua_te: int
    du_suc_chua: bool             # đủ cho so_nguoi / so_phong
    dien_tich: float | None
    co_bua_sang: bool
    thanh_toan_tai_cho: bool | None      # None = "Chưa có thông tin"
    so_ngay_huy_mien_phi: int | None
    dieu_kien_huy: str | None
    tien_nghi: list[str]
    gia_theo_ota: list[GiaOta]    # rỗng khi không truyền ngày


class KhoangNgay(_Kieu):
    ngay_nhan: date
    ngay_tra: date
    tong_ca_chuyen: int


class ChiTietChoO(_Kieu):
    ma_co_so: int
    ma_tinh: int
    ten: str
    loai_hinh: str
    dia_chi: str | None
    khu_vuc: str | None
    hang_sao: int | None
    vi_do: float | None
    kinh_do: float | None
    diem_danh_gia: float | None   # None khi < 3 lượt
    so_luot_danh_gia: int
    la_du_lieu_mau: bool
    mo_ta: str | None             # văn bản tự do: công cụ PHẢI bọc <tai_lieu> trước khi đưa mô hình
    tien_nghi: list[str]
    so_thich: list[str]
    ngay_nhan: date | None
    ngay_tra: date | None
    so_dem: int | None
    so_nguoi: int
    so_phong: int
    loai_phong: list[LoaiPhongGia]
    re_nhat: tuple[int, int] | None        # (ma_loai_phong, ma_lien_ket) rẻ nhất trong phép so
    ngay_re_hon: list[KhoangNgay]          # UC03-A4: tối đa 3 khoảng cùng số đêm, lệch ±3 ngày, rẻ hơn
    ghi_chu: str


class DichVuGia(Protocol):        # app/services/gia.py
    def chi_tiet_cho_o(self, conn: Connection, *, ma_co_so: int, ngay_nhan: date | None, ngay_tra: date | None,
                       so_nguoi: int = 2, so_phong: int = 1, hom_nay: date) -> ChiTietChoO: ...


# =====================================================================  T-014: so sánh
class OSoSanh(_Kieu):
    ma_co_so: int
    hien_thi: str                 # "Chưa có thông tin" giữ nguyên chữ
    gia_tri: int | float | bool | str | None


class HangSoSanh(_Kieu):
    ma_hang: str                  # theo SA_T003 (D-022, D-029(4)), ví dụ "gia_ca_chuyen", "huy_mien_phi", "khoang_cach"
    nhan: str
    la_tien: bool                 # True → lớp công cụ bỏ hien_thi/gia_tri trước khi đưa mô hình
    cac_o: list[OSoSanh]
    o_tot_nhat: list[int]         # mã cơ sở tốt nhất CỦA HÀNG (có thể nhiều); rỗng nếu hàng không có thứ tự / mọi ô bằng nhau


class SoSanh(_Kieu):
    ma_co_so: list[int]
    ngay_nhan: date
    ngay_tra: date
    so_dem: int
    hang: list[HangSoSanh]
    ghi_chu: str


class DichVuSoSanh(Protocol):     # app/services/so_sanh.py
    def so_sanh(self, conn: Connection, *, ma_co_so: list[int], ngay_nhan: date, ngay_tra: date, so_nguoi: int,
                so_phong: int, diem_tham_chieu: list[Diem] = (), hom_nay: date,
                ma_tien_nghi: list[int] = ()) -> SoSanh: ...
        # 2–3 cơ sở cùng tỉnh; khác tỉnh → KHAC_TINH; cơ sở ẩn → KHONG_TIM_THAY
        # ma_tien_nghi: thêm ở T-014 (có mặc định, không phá chữ ký đã chốt) — tiện nghi đã lọc → hàng "tien_nghi:<mã>"
        # ma_hang đã cài (T-014): gia_ca_chuyen, gia_tb_dem, ota_re_nhat, gia_khong_so (chỉ khi có), diem_danh_gia,
        # hang_sao, khoang_cach:<loai>:<ma>, tien_nghi:<ma>, loai_phong, bua_sang, chinh_sach_huy, huy_mien_phi,
        # thanh_toan_tai_cho, suc_chua, dien_tich


# =====================================================================  T-015: địa điểm quanh, di chuyển
class DiaDiemGan(_Kieu):
    ma_dia_diem: int
    ten: str
    ma_loai: int
    ten_loai: str
    nhom: str
    khoang_cach_km: float | None  # ước tính; None khi không truyền `quanh`
    gio_mo_cua_ngay_do: list[str] | None   # ["07:00–11:00", "13:30–17:00"]; None khi không truyền `ngay`
    dong_cua_ngay_do: bool | None
    diem_danh_gia: float | None
    co_thu_phi: bool | None
    la_du_lieu_mau: bool


class DichVuDiaDiem(Protocol):    # app/services/dia_diem.py (hàm mới; repositories.dia_diem.tim giữ cho /places)
    def tim_quanh(self, conn: Connection, *, ma_tinh: int, nhom: str | None = None, ma_loai: int | None = None,
                  ma_so_thich: list[int] = (), tu_khoa: str | None = None, quanh: Diem | None = None,
                  ban_kinh_km: float = 40, ngay: date | None = None, gioi_han: int = 20) -> list[DiaDiemGan]: ...
        # có `quanh`: lọc ≤ ban_kinh_km (≤ 40, D-023), sắp khoảng cách tăng; không có: thứ tự công khai như /places


class UocTinh(_Kieu):
    km: float
    phut: int
    nguon: Literal["bo_dem", "cong_thuc", "ban_do"]
    nhan: Literal["ước tính"] = "ước tính"


class DichVuBanDo(Protocol):      # app/services/ban_do.py (đọc/ghi bộ đệm THOI_GIAN_DI_CHUYEN; adapter bản đồ phía sau)
    def uoc_tinh(self, conn: Connection, *, tu: Diem, den: Diem, phuong_tien: PhuongTien) -> UocTinh: ...


# =====================================================================  T-015: xếp lịch trình (không ghi)
class NoiNghiDem(_Kieu):
    thu_tu_ngay: int
    ma_co_so: int


class YeuCauLichTrinh(_Kieu):
    ma_tinh: int
    khu_vuc: str | None = None
    ngay_bat_dau: date
    ngay_ket_thuc: date           # tối đa 14 ngày
    so_nguoi: int = Field(ge=1, le=30)
    kieu_nhom: KieuNhom = "mot_minh"
    nhip_do: NhipDo = "vua"
    phuong_tien: PhuongTien = "xe_may"
    ma_so_thich: list[int] = []
    ngan_sach: int | None = None
    loai_ngan_sach: LoaiNganSach | None = None
    gio_den: time | None = None
    gio_ve: time | None = None
    gio_bat_dau_ngay: time | None = None   # D-034
    gio_ket_thuc_ngay: time | None = None
    noi_nghi: list[NoiNghiDem] = []        # nơi nghỉ dự kiến (D-039a), không phải "Đã đặt"
    diem_bat_buoc: list[int] = []
    diem_tranh: list[int] = []


class CanhBao(_Kieu):
    ma: Literal["chang_qua_90_phut", "vuot_ngan_sach", "dong_cua", "ngoai_ban_kinh", "thieu_dia_diem"]
    thu_tu_ngay: int | None = None
    thu_tu_muc: int | None = None
    thong_bao: str


class MucNhap(_Kieu):
    thu_tu: int
    loai_muc: LoaiMuc
    ma_dia_diem: int | None
    gio_bat_dau: time | None
    gio_ket_thuc: time | None
    phuong_tien: PhuongTien | None
    km: float | None              # ước tính, chặng từ mục trước
    phut: int | None
    chi_phi_uoc_tinh: int | None
    da_ghim: bool = False


class NgayNhap(_Kieu):
    thu_tu_ngay: int
    ngay: date
    ma_co_so_nghi: int | None
    noi_nghi: Literal["du_kien", "da_dat"] | None   # "Nơi nghỉ dự kiến · chưa đặt" vs "Đã đặt (tự khai)"
    ma_cho_o: int | None
    muc: list[MucNhap]
    canh_bao: list[CanhBao]
    chi_phi_uoc_tinh: int | None


class DiemBiLoai(_Kieu):
    ma_dia_diem: int
    ly_do: str


class BanNhap(_Kieu):
    v: Literal[1] = 1
    yeu_cau: YeuCauLichTrinh
    ngay: list[NgayNhap]
    diem_bi_loai: list[DiemBiLoai]
    chi_phi_uoc_tinh: int | None
    bam: str                      # sha256 của JSON chuẩn hoá (không gồm `bam`) — đề xuất ghi đúng nội dung đã xem


class ThemDiem(_Kieu):
    loai: Literal["them_diem"] = "them_diem"
    thu_tu_ngay: int
    ma_dia_diem: int
    vi_tri: int | None = None     # None = để bộ xếp chọn


class BoDiem(_Kieu):
    loai: Literal["bo_diem"] = "bo_diem"
    thu_tu_ngay: int
    ma_dia_diem: int


class DoiThuTu(_Kieu):
    loai: Literal["doi_thu_tu"] = "doi_thu_tu"
    thu_tu_ngay: int
    ma_dia_diem_theo_thu_tu: list[int]


class DoiNhipDo(_Kieu):
    loai: Literal["doi_nhip_do"] = "doi_nhip_do"
    thu_tu_ngay: int | None = None  # None = cả lịch trình
    nhip_do: NhipDo


class GanNoiNghi(_Kieu):
    loai: Literal["gan_noi_nghi"] = "gan_noi_nghi"
    thu_tu_ngay: list[int]
    ma_co_so: int | None          # None = bỏ nơi nghỉ dự kiến; đêm đã "Đã đặt" → DEM_DA_DAT


class DoiGioNgay(_Kieu):
    loai: Literal["doi_gio_ngay"] = "doi_gio_ngay"
    thu_tu_ngay: int | None = None
    gio_bat_dau_ngay: time | None
    gio_ket_thuc_ngay: time | None


ThaoTac = Annotated[ThemDiem | BoDiem | DoiThuTu | DoiNhipDo | GanNoiNghi | DoiGioNgay, Field(discriminator="loai")]


class ThayDoi(_Kieu):
    loai: Literal["them", "bo", "doi_gio", "doi_thu_tu", "doi_noi_nghi", "doi_nhip_do"]
    thu_tu_ngay: int | None
    doi_tuong: Diem | None
    truoc: str | None
    sau: str | None


class XemTruoc(_Kieu):
    nguon: Literal["ban_nhap", "lich_trinh"]
    ma_lich_trinh: int | None
    phien_ban_goc: int | None     # ma_phien_ban mới nhất của PHIEN_BAN_LICH_TRINH lúc xem trước (khoá lạc quan)
    ban_nhap_moi: BanNhap
    thay_doi: list[ThayDoi]
    canh_bao_moi: list[CanhBao]


class DichVuLapLich(Protocol):    # app/services/lap_lich.py — KHÔNG ghi CSDL
    def tao_nhap(self, conn: Connection, *, yeu_cau: YeuCauLichTrinh, hom_nay: date) -> BanNhap: ...

    def xem_truoc_sua(self, conn: Connection, *, nguon: BanNhap | int, ma_nguoi_dung: int | None,
                      thao_tac: list[ThaoTac], hom_nay: date) -> XemTruoc: ...
        # nguon int = ma_lich_trinh: người đọc phải là chủ hoặc thành viên, không thì KHONG_TIM_THAY


# =====================================================================  T-015 / T-016: ghi (chỉ sau khi người dùng xác nhận)
class DichVuLichTrinh(Protocol):  # app/services/lich_trinh.py — người gọi giữ giao dịch
    def luu_tu_ban_nhap(self, conn: Connection, *, ma_nguoi_dung: int, ban_nhap: BanNhap,
                        ten: str | None = None) -> int: ...
        # kiểm lại `bam`; ghi LICH_TRINH ('da_luu'), NGAY_, MUC_, LICH_TRINH_SO_THICH, PHIEN_BAN 1; trả ma_lich_trinh

    def ap_dung(self, conn: Connection, *, ma_nguoi_dung: int, xem_truoc: XemTruoc) -> int: ...
        # chỉ chủ (thành viên → CHI_CHU_AP_DUNG); SELECT … FOR UPDATE lịch trình; phien_ban_goc khác → PHIEN_BAN_DA_DOI;
        # ghi phiên bản mới, trả ma_phien_ban; lịch trình nhóm → THONG_BAO cho thành viên (X6)


class DichVuNhom(Protocol):       # app/services/nhom.py
    def tao_de_xuat_sua(self, conn: Connection, *, ma_lich_trinh: int, ma_nguoi_dung: int, noi_dung: str,
                        qua_tro_ly: bool = False) -> int: ...
        # người gọi phải là thành viên; ghi DE_XUAT_SUA ('cho_duyet', qua_tro_ly) + THONG_BAO cho chủ; trả ma_de_xuat
