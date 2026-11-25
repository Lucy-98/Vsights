"""So sánh 2–3 chỗ ở cùng tỉnh (T-014; UC09, W07/M07; D-022, D-029(4), D-031; SA_T003).

Cài đặt `hop_dong.DichVuSoSanh` — công cụ chatbot `so_sanh_cho_o` gọi đúng hàm này (SA-017).

- Mọi hàng giá lấy từ `services/gia.chi_tiet_cho_o`, nên "rẻ nhất" và tổng chuyến trùng thẻ tìm kiếm và trang chi tiết
  (một quy tắc D-021, SA-019). Giá OTA "không so" hiện ở hàng riêng, không tô.
- Các hàng theo loại phòng (bữa sáng, huỷ, thanh toán tại chỗ, sức chứa, diện tích) lấy **loại phòng rẻ nhất trong
  phép so** của từng cơ sở; chưa có giá thì lấy loại phòng đủ sức chứa đầu tiên. Hàng "Loại phòng" cho biết đang so
  loại nào.
- Ô tốt nhất tô **theo từng hàng** (`o_tot_nhat`), không có nhãn "tốt nhất" tổng thể (D-022c). Hàng không có thứ tự
  (OTA, chính sách huỷ, sức chứa) hoặc mọi ô bằng nhau thì không tô.
- Trường rỗng hiện đúng chữ "Chưa có thông tin"; dưới 3 lượt đánh giá hiện "Chưa đủ đánh giá" (SA_T003).
- Khoảng cách: đường chim bay giữa toạ độ, nhãn "(ước tính)" (D-022b, không cố định "Tới biển"). Ở T-015 đổi sang
  `ban_do.uoc_tinh` mà không đổi hợp đồng.
- Không có `so_phong_con`, không có chữ "còn phòng", "đặt phòng" (D-029(5), SA-015).
"""
from datetime import date
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import Connection, text

from app.core.errors import AppError, khong_tim_thay
from app.services import gia
from app.services.hop_dong import ChiTietChoO, Diem, HangSoSanh, LoaiPhongGia, OSoSanh, SoSanh
from app.services.tim_kiem import kiem_dai_ngay

CHUA_CO = "Chưa có thông tin"
CHUA_DU_DANH_GIA = "Chưa đủ đánh giá"
SO_DIEM_TOI_DA = 5
GHI_CHU = ("Giá tham khảo, đã gồm thuế, phí (dòng \"chưa gồm thuế, phí · không so\" chỉ để tham khảo, không dùng để so); "
           "giá cuối cùng do OTA quyết định. Khoảng cách là ước tính đường chim bay. Ô được tô là tốt nhất của từng "
           "hàng, Vsights không chọn hộ chỗ ở tốt nhất.")


def _tien(x: int) -> str:
    return f"{x:,}".replace(",", ".") + " ₫"


def _km(a_lat, a_lon, b_lat, b_lon) -> float:
    a_lat, a_lon, b_lat, b_lon = map(lambda v: radians(float(v)), (a_lat, a_lon, b_lat, b_lon))
    h = sin((b_lat - a_lat) / 2) ** 2 + cos(a_lat) * cos(b_lat) * sin((b_lon - a_lon) / 2) ** 2
    return round(2 * 6371.0 * asin(sqrt(h)), 1)


def _so_vn(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _tot_nhat(cac: list[tuple[int, object]], chieu: str | None) -> list[int]:
    """Mã cơ sở tốt nhất của hàng: 'nho' / 'lon' / 'dung' (True tốt hơn). Bỏ ô rỗng; mọi ô bằng nhau → không tô."""
    if chieu is None:
        return []
    co = [(m, v) for m, v in cac if v is not None]
    gia_tri = {v for _, v in co}
    if not co or (len(gia_tri) == 1 and len(co) == len(cac)):
        return []
    if chieu == "dung":
        return [m for m, v in co if v is True]
    tot = min(gia_tri) if chieu == "nho" else max(gia_tri)
    return [m for m, v in co if v == tot]


def _hang(ma_hang: str, nhan: str, la_tien: bool, o: list[OSoSanh], chieu: str | None) -> HangSoSanh:
    return HangSoSanh(ma_hang=ma_hang, nhan=nhan, la_tien=la_tien, cac_o=o,
                      o_tot_nhat=_tot_nhat([(x.ma_co_so, x.gia_tri) for x in o], chieu))


def _o(ma: int, gia_tri, hien_thi: str | None = None) -> OSoSanh:
    return OSoSanh(ma_co_so=ma, gia_tri=gia_tri, hien_thi=hien_thi if hien_thi is not None else
                   (CHUA_CO if gia_tri is None else str(gia_tri)))


def _loai_phong_so(ct: ChiTietChoO) -> LoaiPhongGia | None:
    if ct.re_nhat:
        return next(lp for lp in ct.loai_phong if lp.ma_loai_phong == ct.re_nhat[0])
    return next((lp for lp in ct.loai_phong if lp.du_suc_chua), None)


def _diem(conn: Connection, d: Diem):
    if d.loai == "dia_diem":
        r = conn.execute(text("SELECT ten, ma_tinh, vi_do, kinh_do FROM dia_diem WHERE ma_dia_diem = :m "
                              "AND trang_thai = 'hien'"), {"m": d.ma}).mappings().first()
    else:
        r = conn.execute(text("SELECT ten, ma_tinh, vi_do, kinh_do FROM co_so_luu_tru WHERE ma_co_so = :m "
                              "AND trang_thai = 'hien'"), {"m": d.ma}).mappings().first()
    if r is None:
        raise khong_tim_thay("địa điểm" if d.loai == "dia_diem" else "chỗ ở")
    return r


def so_sanh(conn: Connection, *, ma_co_so: list[int], ngay_nhan: date, ngay_tra: date, so_nguoi: int,
            so_phong: int, diem_tham_chieu: list[Diem] = (), hom_nay: date, ma_tien_nghi: list[int] = ()) -> SoSanh:
    """`ma_tien_nghi` (tuỳ chọn, thêm ở T-014, không phá chữ ký đã chốt): tiện nghi du khách đã lọc → mỗi tiện nghi
    một hàng có/không (D-022b)."""
    ds = list(dict.fromkeys(ma_co_so))
    if not 2 <= len(ds) <= 3:
        raise AppError(422, "SO_LUONG_SO_SANH", "Chọn từ 2 đến 3 chỗ ở khác nhau để so sánh.", {"so_luong": len(ds)})
    if len(diem_tham_chieu) > SO_DIEM_TOI_DA:
        raise AppError(422, "QUA_SO_DIEM", f"Chọn tối đa {SO_DIEM_TOI_DA} điểm để tính khoảng cách.")
    so_dem = kiem_dai_ngay(ngay_nhan, ngay_tra, so_nguoi, so_phong, hom_nay)

    cts = [gia.chi_tiet_cho_o(conn, ma_co_so=m, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_nguoi=so_nguoi,
                              so_phong=so_phong, hom_nay=hom_nay) for m in ds]       # cơ sở ẩn → 404 ở đây
    tinh = {ct.ma_tinh for ct in cts}
    if len(tinh) > 1:
        raise AppError(422, "KHAC_TINH", "Chỉ so sánh các chỗ ở trong cùng một tỉnh, thành.")
    diem = [(d, _diem(conn, d)) for d in diem_tham_chieu]
    if any(r["ma_tinh"] not in tinh for _, r in diem):
        raise AppError(422, "KHAC_TINH", "Điểm tham chiếu phải cùng tỉnh, thành với các chỗ ở.")

    lps = {ct.ma_co_so: _loai_phong_so(ct) for ct in cts}
    hang: list[HangSoSanh] = []

    # ---- giá (D-022b, D-029(1)): cùng gốc với thẻ tìm kiếm
    tong, tb, ota, ngoai = [], [], [], []
    for ct in cts:
        m = ct.ma_co_so
        o = None
        if ct.re_nhat:
            lp = lps[m]
            o = next(x for x in lp.gia_theo_ota if x.ma_lien_ket == ct.re_nhat[1])
        if o:
            t = o.tong_ca_chuyen
            tong.append(_o(m, t, f"{_tien(t)} / {so_dem} đêm · đã gồm thuế, phí"
                                 + (" · Giá có thể đã thay đổi" if o.gia_cu else "")))
            moi_dem = round(t / so_dem / so_phong)
            tb.append(_o(m, moi_dem, f"{_tien(moi_dem)} / đêm"))
            ota.append(_o(m, o.ten_ota, f"Rẻ nhất trên {o.ten_ota}"))
        else:
            tong.append(_o(m, None, "Chưa có giá cho đủ các đêm"))
            tb.append(_o(m, None, "Chưa có giá cho đủ các đêm"))
            ota.append(_o(m, None, "Chưa có giá cho đủ các đêm"))
        khong_so = [x for lp in ct.loai_phong if lp.du_suc_chua for x in lp.gia_theo_ota
                    if not x.so_sanh_duoc and x.du_dem]
        if khong_so:
            x = min(khong_so, key=lambda x: x.tong_ca_chuyen)
            ngoai.append(_o(m, x.tong_ca_chuyen, f"{_tien(x.tong_ca_chuyen)} trên {x.ten_ota} · {x.nhan_thue_phi}"))
        else:
            ngoai.append(_o(m, None, "Không có"))
    hang += [_hang("gia_ca_chuyen", "Giá cả chuyến", True, tong, "nho"),
             _hang("gia_tb_dem", "Giá trung bình mỗi đêm, mỗi phòng", True, tb, "nho"),
             _hang("ota_re_nhat", "OTA có giá rẻ nhất", False, ota, None)]
    if any(x.gia_tri is not None for x in ngoai):
        hang.append(_hang("gia_khong_so", "Giá chưa gồm thuế, phí (không so)", True, ngoai, None))

    # ---- cơ sở
    hang.append(_hang("diem_danh_gia", "Điểm đánh giá", False,
                      [_o(ct.ma_co_so, ct.diem_danh_gia,
                          f"{_so_vn(ct.diem_danh_gia)}/5 · {ct.so_luot_danh_gia} lượt" if ct.diem_danh_gia is not None
                          else CHUA_DU_DANH_GIA) for ct in cts], "lon"))
    hang.append(_hang("hang_sao", "Hạng sao", False,
                      [_o(ct.ma_co_so, ct.hang_sao, f"{ct.hang_sao} sao" if ct.hang_sao else CHUA_CO) for ct in cts],
                      "lon"))
    for d, r in diem:
        o = []
        for ct in cts:
            if None in (ct.vi_do, ct.kinh_do, r["vi_do"], r["kinh_do"]):
                o.append(_o(ct.ma_co_so, None))
            else:
                km = _km(ct.vi_do, ct.kinh_do, r["vi_do"], r["kinh_do"])
                o.append(_o(ct.ma_co_so, km, f"{_so_vn(km)} km (ước tính)"))
        hang.append(_hang(f"khoang_cach:{d.loai}:{d.ma}", f"Khoảng cách tới {r['ten']}", False, o, "nho"))

    # ---- tiện nghi du khách đã lọc (D-022b): có ở cơ sở hoặc ở loại phòng đang so
    if ma_tien_nghi:
        ten = {r["ma_tien_nghi"]: r["ten_tien_nghi"] for r in conn.execute(text(
            "SELECT ma_tien_nghi, ten_tien_nghi FROM tien_nghi WHERE ma_tien_nghi = ANY(CAST(:m AS smallint[]))"),
            {"m": list(ma_tien_nghi)}).mappings()}
        for m in dict.fromkeys(ma_tien_nghi):
            if m not in ten:
                raise AppError(422, "MA_KHONG_TON_TAI", "Tiện nghi không tồn tại.", {"ma_tien_nghi": m})
            o = []
            for ct in cts:
                lp = lps[ct.ma_co_so]
                co = ten[m] in ct.tien_nghi or (lp is not None and ten[m] in lp.tien_nghi)
                o.append(_o(ct.ma_co_so, co, "Có" if co else "Không"))
            hang.append(_hang(f"tien_nghi:{m}", ten[m], False, o, "dung"))

    # ---- theo loại phòng đang so (D-022b, D-029(4), D-031)
    def theo_lp(ham):
        return [ham(ct.ma_co_so, lps[ct.ma_co_so]) for ct in cts]

    hang.append(_hang("loai_phong", "Loại phòng đang so", False, theo_lp(
        lambda m, lp: _o(m, lp.ten_loai_phong if lp else None)), None))
    hang.append(_hang("bua_sang", "Bữa sáng", False, theo_lp(
        lambda m, lp: _o(m, lp.co_bua_sang if lp else None,
                         None if lp is None else ("Có bữa sáng" if lp.co_bua_sang else "Không gồm bữa sáng"))), "dung"))
    hang.append(_hang("chinh_sach_huy", "Chính sách huỷ", False, theo_lp(
        lambda m, lp: _o(m, (lp.dieu_kien_huy if lp else None) or _chinh_sach_co_so(conn, m))), None))
    hang.append(_hang("huy_mien_phi", "Hạn huỷ miễn phí", False, theo_lp(
        lambda m, lp: _o(m, None if lp is None or lp.so_ngay_huy_mien_phi is None else lp.so_ngay_huy_mien_phi,
                         None if lp is None or lp.so_ngay_huy_mien_phi is None else
                         ("Không huỷ miễn phí" if lp.so_ngay_huy_mien_phi == 0
                          else f"Huỷ miễn phí trước {lp.so_ngay_huy_mien_phi} ngày nhận phòng"))), None))
    # Hạn huỷ: ít ngày hơn (mà > 0) là tốt hơn; 0 = không huỷ miễn phí → tô riêng
    h = hang[-1]
    duong = [(o.ma_co_so, o.gia_tri) for o in h.cac_o if isinstance(o.gia_tri, int) and o.gia_tri > 0]
    tot = [m for m, v in duong if v == min(v for _, v in duong)] if duong else []
    if len({o.gia_tri for o in h.cac_o}) > 1:
        hang[-1] = h.model_copy(update={"o_tot_nhat": tot})
    hang.append(_hang("thanh_toan_tai_cho", "Thanh toán tại chỗ", False, theo_lp(
        lambda m, lp: _o(m, None if lp is None else lp.thanh_toan_tai_cho,
                         None if lp is None or lp.thanh_toan_tai_cho is None else
                         ("Có" if lp.thanh_toan_tai_cho else "Không"))), "dung"))
    hang.append(_hang("suc_chua", "Sức chứa mỗi phòng", False, theo_lp(
        lambda m, lp: _o(m, None if lp is None else f"{lp.suc_chua_nl} người lớn"
                         + (f", {lp.suc_chua_te} trẻ em" if lp.suc_chua_te else ""))), None))
    hang.append(_hang("dien_tich", "Diện tích", False, theo_lp(
        lambda m, lp: _o(m, None if lp is None else lp.dien_tich,
                         None if lp is None or lp.dien_tich is None else f"{_so_vn(lp.dien_tich).rstrip('0').rstrip(',')} m²")),
        "lon"))
    return SoSanh(ma_co_so=ds, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_dem=so_dem, hang=hang, ghi_chu=GHI_CHU)


def _chinh_sach_co_so(conn: Connection, ma: int) -> str | None:
    return conn.execute(text("SELECT chinh_sach_huy FROM co_so_luu_tru WHERE ma_co_so = :m"), {"m": ma}).scalar()
