"""Chi tiết chỗ ở và bảng giá từng đêm theo OTA (T-013; UC03; D-021, D-029(1), D-035; B-023).

Cài đặt `hop_dong.DichVuGia` (chữ ký chốt ở T-024, SA-017) — công cụ chatbot `xem_cho_o` gọi đúng hàm này.

Quy tắc giá (một nguồn cho cả /stays/search và /stays/{ma}):
- OTA niêm yết đã gồm thuế, phí → dùng nguyên giá.
- OTA niêm yết chưa gồm, CÓ `ty_le_thue_phi` → quy đổi: tổng = Σ giá đã gồm + round(Σ giá chưa gồm × (1 + tỷ lệ/100)),
  nhân số phòng. Đây đúng là biểu thức SQL của repositories/tim_kiem.py, nên "rẻ nhất" ở trang chi tiết
  trùng với thẻ kết quả tìm kiếm. Giá từng đêm hiển thị được quy đổi và làm tròn từng đêm.
- OTA chưa gồm, CHƯA có tỷ lệ (Traveloka trong dữ liệu mẫu) → `so_sanh_duoc = False`: vẫn hiện giá gốc với nhãn
  "chưa gồm thuế, phí · không so", không xếp hạng, không chọn rẻ nhất (D-021, B-023).
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Connection

from app.core.errors import AppError, khong_tim_thay
from app.repositories import gia as repo
from app.services.hop_dong import ChiTietChoO, GiaDem, GiaOta, KhoangNgay, LoaiPhongGia
from app.services.tim_kiem import kiem_dai_ngay

GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
SO_NGAY_GIA_CU = 3          # BR-03: quá 3 ngày chưa cập nhật → "Giá có thể đã thay đổi"
LECH_NGAY_TOI_DA = 3        # UC03-A4: thử dời ±3 ngày
SO_KHOANG_RE_HON = 3
NHAN_DA_GOM = "đã gồm thuế, phí"
NHAN_KHONG_SO = "chưa gồm thuế, phí · không so"
GHI_CHU = ("Giá tham khảo theo từng đêm, đã gồm thuế, phí (trừ dòng ghi \"không so\"); giá cuối cùng xem trên OTA. "
           "Vsights không nhận đặt chỗ; phòng trống do OTA xác nhận.")


def _lam_tron(x: Decimal) -> int:
    return int(x.quantize(Decimal(1), rounding=ROUND_HALF_UP))   # = round() numeric của PostgreSQL với số dương


def _he_so(ty_le) -> Decimal:
    return 1 + Decimal(ty_le) / 100


def _nhan_quy_doi(ty_le) -> str:
    so = format(Decimal(ty_le).normalize(), "f").replace(".", ",")
    return f"đã quy đổi +{so}% thuế, phí"


def tong_da_gom(dem: list[dict], ty_le, so_phong: int) -> int:
    """Tổng cả chuyến đã gồm thuế, phí — cùng biểu thức với SQL tìm kiếm (D-021)."""
    gom = sum(d["gia_dem"] for d in dem if d["gom_thue_phi"])
    chua = sum(d["gia_dem"] for d in dem if not d["gom_thue_phi"])
    return (gom + (_lam_tron(chua * _he_so(ty_le)) if chua else 0)) * so_phong


def _so_sanh_duoc(dem: list[dict], ty_le) -> bool:
    return all(d["gom_thue_phi"] for d in dem) or ty_le is not None


def _cac_dem(nhan: date, tra: date) -> list[date]:
    return [nhan + timedelta(days=i) for i in range((tra - nhan).days)]


def _re_nhat_trong_dai(nhom: dict, du_suc_chua: set[int], nhan: date, tra: date, so_phong: int):
    """(tổng, mã loại phòng, mã liên kết) rẻ nhất trong phép so cho dải [nhan, tra); None nếu không có."""
    can = set(_cac_dem(nhan, tra))
    tot = None
    for (lp, lk), ds in nhom.items():
        if lp not in du_suc_chua:
            continue
        dem = [d for d in ds if d["ngay"] in can]
        if len(dem) != len(can) or not _so_sanh_duoc(dem, ds[0]["ty_le_thue_phi"]):
            continue
        k = (tong_da_gom(dem, ds[0]["ty_le_thue_phi"], so_phong), lp, lk)
        tot = k if tot is None or k < tot else tot
    return tot


def chi_tiet_cho_o(conn: Connection, *, ma_co_so: int, ngay_nhan: date | None, ngay_tra: date | None,
                   so_nguoi: int = 2, so_phong: int = 1, hom_nay: date) -> ChiTietChoO:
    if (ngay_nhan is None) != (ngay_tra is None):
        raise AppError(422, "NGAY_KHONG_HOP_LE", "Cần cả ngày nhận phòng và ngày trả phòng, hoặc bỏ cả hai.")
    if so_nguoi < so_phong:
        raise AppError(422, "SO_NGUOI_IT_HON_SO_PHONG", "Số người phải lớn hơn hoặc bằng số phòng.")
    so_dem = kiem_dai_ngay(ngay_nhan, ngay_tra, so_nguoi, so_phong, hom_nay) if ngay_nhan else None

    cs = repo.co_so_hien(conn, ma_co_so)
    if cs is None:
        raise khong_tim_thay("chỗ ở")
    cac_lp = repo.loai_phong_hien(conn, ma_co_so)
    du_suc_chua = {lp["ma_loai_phong"] for lp in cac_lp if lp["suc_chua_nl"] * so_phong >= so_nguoi}

    nhom: dict[tuple[int, int], list[dict]] = defaultdict(list)
    if ngay_nhan:
        tu = max(hom_nay, ngay_nhan - timedelta(days=LECH_NGAY_TOI_DA))
        for g in repo.gia_trong_dai(conn, ma_co_so, tu, ngay_tra + timedelta(days=LECH_NGAY_TOI_DA)):
            nhom[(g["ma_loai_phong"], g["ma_lien_ket"])].append(dict(g))

    # ---- bảng giá từng đêm theo OTA, cho từng loại phòng
    cac_dem = set(_cac_dem(ngay_nhan, ngay_tra)) if ngay_nhan else set()
    gia_lp: dict[int, list[dict]] = defaultdict(list)
    for (lp, lk), ds in nhom.items():
        dem = [d for d in ds if d["ngay"] in cac_dem]
        if not dem:
            continue
        ty_le, du_dem = ds[0]["ty_le_thue_phi"], len(dem) == so_dem
        so_duoc = _so_sanh_duoc(dem, ty_le)
        gom_goc = all(d["gom_thue_phi"] for d in dem)
        cap_nhat = min(d["ngay_cap_nhat"] for d in dem)
        gia_lp[lp].append({
            "ma_lien_ket": lk, "ten_ota": ds[0]["ten_ota"], "url": ds[0]["url"],
            "gom_thue_phi_goc": gom_goc, "so_sanh_duoc": so_duoc,
            "nhan_thue_phi": NHAN_DA_GOM if gom_goc else (_nhan_quy_doi(ty_le) if so_duoc else NHAN_KHONG_SO),
            "du_dem": du_dem,
            "dem": [GiaDem(ngay=d["ngay"], gia_dem=d["gia_dem"] if d["gom_thue_phi"] or not so_duoc
                           else _lam_tron(d["gia_dem"] * _he_so(ty_le))) for d in dem],
            "tong_ca_chuyen": (tong_da_gom(dem, ty_le, so_phong) if so_duoc else sum(d["gia_dem"] for d in dem) * so_phong)
                              if du_dem else None,
            "cap_nhat_gia": cap_nhat,
            "gia_cu": (hom_nay - cap_nhat.astimezone(GIO_VN).date()).days > SO_NGAY_GIA_CU,
            "_xep": lp in du_suc_chua and so_duoc and du_dem,
        })

    # Xếp hạng giá trong phép so của CƠ SỞ (chỉ loại phòng đủ sức chứa); thứ tự giống DISTINCT ON của tìm kiếm
    hang = sorted(((o["tong_ca_chuyen"], lp, o["ma_lien_ket"]) for lp, ds in gia_lp.items() for o in ds if o["_xep"]))
    vi_tri = {(lp, lk): i + 1 for i, (_, lp, lk) in enumerate(hang)}
    re_nhat = (hang[0][1], hang[0][2]) if hang else None

    loai_phong = []
    for lp in cac_lp:
        m = lp["ma_loai_phong"]
        ds = sorted(gia_lp.get(m, []), key=lambda o: (not o["so_sanh_duoc"], o["tong_ca_chuyen"] is None,
                                                      o["tong_ca_chuyen"] or 0, o["ten_ota"]))
        loai_phong.append(LoaiPhongGia(
            ma_loai_phong=m, ten_loai_phong=lp["ten_loai_phong"], loai_giuong=lp["loai_giuong"],
            suc_chua_nl=lp["suc_chua_nl"], suc_chua_te=lp["suc_chua_te"], du_suc_chua=m in du_suc_chua,
            dien_tich=float(lp["dien_tich"]) if lp["dien_tich"] is not None else None,
            co_bua_sang=lp["co_bua_sang"], thanh_toan_tai_cho=lp["thanh_toan_tai_cho"],
            so_ngay_huy_mien_phi=lp["so_ngay_huy_mien_phi"], dieu_kien_huy=lp["dieu_kien_huy"],
            tien_nghi=list(lp["tien_nghi"]),
            gia_theo_ota=[GiaOta(**{k: v for k, v in o.items() if k != "_xep"},
                                 xep_hang_gia=vi_tri.get((m, o["ma_lien_ket"]))) for o in ds]))

    # ---- UC03-A4: các khoảng cùng số đêm, dời tối đa ±3 ngày, rẻ hơn lựa chọn hiện tại
    ngay_re_hon = []
    if ngay_nhan:
        hien_tai = hang[0][0] if hang else None
        for lech in range(-LECH_NGAY_TOI_DA, LECH_NGAY_TOI_DA + 1):
            n = ngay_nhan + timedelta(days=lech)
            if lech == 0 or n < hom_nay:
                continue
            t = n + timedelta(days=so_dem)
            k = _re_nhat_trong_dai(nhom, du_suc_chua, n, t, so_phong)
            if k and (hien_tai is None or k[0] < hien_tai):
                ngay_re_hon.append(KhoangNgay(ngay_nhan=n, ngay_tra=t, tong_ca_chuyen=k[0]))
        ngay_re_hon = sorted(ngay_re_hon, key=lambda x: (x.tong_ca_chuyen, x.ngay_nhan))[:SO_KHOANG_RE_HON]

    return ChiTietChoO(
        ma_co_so=cs["ma_co_so"], ma_tinh=cs["ma_tinh"], ten=cs["ten"], loai_hinh=cs["loai_hinh"],
        dia_chi=cs["dia_chi"], khu_vuc=cs["khu_vuc"], hang_sao=cs["hang_sao"],
        vi_do=float(cs["vi_do"]) if cs["vi_do"] is not None else None,
        kinh_do=float(cs["kinh_do"]) if cs["kinh_do"] is not None else None,
        diem_danh_gia=float(cs["diem_tb"]) if cs["diem_tb"] is not None and cs["so_luot_danh_gia"] >= 3 else None,
        so_luot_danh_gia=cs["so_luot_danh_gia"], la_du_lieu_mau=cs["la_du_lieu_mau"], mo_ta=cs["mo_ta"],
        tien_nghi=list(cs["tien_nghi"]), so_thich=list(cs["so_thich"]),
        ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_dem=so_dem, so_nguoi=so_nguoi, so_phong=so_phong,
        loai_phong=loai_phong, re_nhat=re_nhat, ngay_re_hon=ngay_re_hon, ghi_chu=GHI_CHU)
