"""Nghiệp vụ tìm chỗ ở theo dải ngày (UC02, D-021, D-028b, D-029)."""
from contextlib import nullcontext
from datetime import date, timedelta

from sqlalchemy import Connection

from app.core.errors import AppError
from app.repositories import danh_muc as repo_dm
from app.repositories import tim_kiem as repo

SO_DEM_TOI_DA = 30
GHI_CHU = ("Giá tham khảo cho cả chuyến, đã gồm thuế, phí; giá ghi \"chưa gồm thuế, phí · không so\" chỉ hiện riêng, "
           "không dùng để so. Giá cuối cùng do OTA quyết định. "
           "Vsights không nhận đặt chỗ; phòng trống do OTA xác nhận.")


def kiem_dai_ngay(ngay_nhan: date, ngay_tra: date, so_nguoi: int, so_phong: int, hom_nay: date) -> int:
    """Kiểm dải ngày và số người, dùng chung cho /stays/search và /stays/{ma} (T-013). Trả số đêm."""
    if ngay_nhan < hom_nay:
        raise AppError(422, "NGAY_KHONG_HOP_LE", "Ngày nhận phòng không được ở quá khứ.")
    if ngay_tra <= ngay_nhan:
        raise AppError(422, "NGAY_KHONG_HOP_LE", "Ngày trả phòng phải sau ngày nhận phòng.")
    so_dem = (ngay_tra - ngay_nhan).days
    if so_dem > SO_DEM_TOI_DA:
        raise AppError(422, "QUA_SO_DEM", f"Mỗi lần ở tối đa {SO_DEM_TOI_DA} đêm.", {"so_dem": so_dem})
    if so_nguoi < so_phong:
        raise AppError(422, "SO_NGUOI_IT_HON_SO_PHONG", "Số người phải lớn hơn hoặc bằng số phòng.")
    return so_dem


SO_TIEN_NGHI_GOI_Y = 5     # tối đa số tiện nghi được thử bỏ từng cái (mỗi lần thử = một truy vấn đếm)
NHAN_NGOAI_PHEP_SO = "chưa gồm thuế, phí · không so"


def _ngay_vn(d: date) -> str:
    return d.strftime("%d/%m")


def goi_y_noi_dieu_kien(conn: Connection, *, ma_tinh: int, ngay_nhan: date, ngay_tra: date, so_nguoi: int,
                        so_phong: int, ngan_sach: int | None, loai_ngan_sach: str, loai_hinh: str | None,
                        ma_tien_nghi: list[int], loai_tru: list[int], hom_nay: date) -> list[dict]:
    """B-028 (FR-09, W03/M03): khi không có kết quả, thử nới TỪNG điều kiện và đếm số kết quả thật.
    Mỗi gợi ý: {dieu_kien, gia_tri, nhan, so_ket_qua}. `dieu_kien` là tên tham số của /stays/search mà giao diện
    phải bỏ/đổi; `gia_tri` là mã tiện nghi cần bỏ (ma_tien_nghi), hoặc {ngay_nhan, ngay_tra} mới (ngay_nhan).
    Chỉ trả gợi ý có so_ket_qua > 0; không gợi ý nào có kết quả thì trả một gợi ý chung, so_ket_qua = None."""
    goc = dict(ma_tinh=ma_tinh, nhan=ngay_nhan, tra=ngay_tra, so_nguoi=so_nguoi, so_phong=so_phong,
               ngan_sach=ngan_sach, loai_ngan_sach=loai_ngan_sach, loai_hinh=loai_hinh,
               tien_nghi=list(ma_tien_nghi), loai_tru=list(loai_tru))
    dem = lambda **doi: repo.dem_ket_qua(conn, **{**goc, **doi})  # noqa: E731
    g = []
    if ma_tien_nghi:
        ten = {r["ma_tien_nghi"]: r["ten_tien_nghi"] for r in repo_dm.tien_nghi(conn)}
        for m in list(dict.fromkeys(ma_tien_nghi))[:SO_TIEN_NGHI_GOI_Y]:
            g.append({"dieu_kien": "ma_tien_nghi", "gia_tri": m, "nhan": f"Bỏ “{ten.get(m, m)}”",
                      "so_ket_qua": dem(tien_nghi=[x for x in ma_tien_nghi if x != m])})
        if len(set(ma_tien_nghi)) > 1:
            g.append({"dieu_kien": "ma_tien_nghi", "gia_tri": None, "nhan": "Bỏ mọi tiện nghi đang lọc",
                      "so_ket_qua": dem(tien_nghi=[])})
    if ngan_sach is not None:
        g.append({"dieu_kien": "ngan_sach", "gia_tri": None, "nhan": "Bỏ giới hạn ngân sách",
                  "so_ket_qua": dem(ngan_sach=None)})
    if loai_hinh:
        g.append({"dieu_kien": "loai_hinh", "gia_tri": None, "nhan": "Mọi loại hình chỗ ở",
                  "so_ket_qua": dem(loai_hinh=None)})
    so_dem = (ngay_tra - ngay_nhan).days
    for lech in (1, -1, 2, -2, 3, -3):          # cùng số đêm, dời gần nhất trước; không về quá khứ
        n = ngay_nhan + timedelta(days=lech)
        if n < hom_nay:
            continue
        t = n + timedelta(days=so_dem)
        k = dem(nhan=n, tra=t)
        if k:
            g.append({"dieu_kien": "ngay_nhan", "gia_tri": {"ngay_nhan": n.isoformat(), "ngay_tra": t.isoformat()},
                      "nhan": f"Nhận phòng {_ngay_vn(n)}, trả {_ngay_vn(t)}", "so_ket_qua": k})
            break
    g = [x for x in g if x["so_ket_qua"]]
    return g or [{"dieu_kien": "ma_tinh", "gia_tri": None, "nhan": "Thử tỉnh, thành khác hoặc ngày khác",
                  "so_ket_qua": None}]


def tim(conn: Connection, *, ma_tinh: int, ngay_nhan: date, ngay_tra: date, so_nguoi: int, so_phong: int,
        ngan_sach: int | None, loai_ngan_sach: str, loai_hinh: str | None, ma_tien_nghi: list[int],
        ma_so_thich: list[int], sap_xep: str, trang: int, kich_thuoc: int, ma_nguoi_dung: int | None,
        hom_nay: date, ghi_luot: bool = True, loai_tru: list[int] = ()) -> dict:
    """Chữ ký ổn định cho công cụ chatbot `tim_cho_o` (SA-017, T-024).
    ghi_luot=False: không ghi LUOT_TIM_KIEM (lượt tìm của trợ lý thống kê riêng, L9 của AI).
    loai_tru: mã cơ sở du khách đã loại trong hội thoại (AI-015), lọc ngay trong SQL nên `tong` đúng.
    Nếu conn đang trong giao dịch (công cụ chạy trong giao dịch READ ONLY) thì không mở giao dịch mới."""
    so_dem = kiem_dai_ngay(ngay_nhan, ngay_tra, so_nguoi, so_phong, hom_nay)

    with (nullcontext() if conn.in_transaction() else conn.begin()):
        # B-024: kiểm mã tỉnh trước khi chạy truy vấn tìm (không trông vào khoá ngoại khi ghi lượt tìm)
        if not repo_dm.tinh_ton_tai(conn, ma_tinh):
            raise AppError(422, "MA_KHONG_TON_TAI", "Tỉnh, thành không tồn tại.", {"ma_tinh": ma_tinh})
        rows, tong, ct, ngoai = repo.tim_cho_o(
            conn, ma_tinh=ma_tinh, nhan=ngay_nhan, tra=ngay_tra, so_nguoi=so_nguoi, so_phong=so_phong,
            ngan_sach=ngan_sach, loai_ngan_sach=loai_ngan_sach, loai_hinh=loai_hinh, tien_nghi=ma_tien_nghi,
            so_thich=ma_so_thich, sap_xep=sap_xep, trang=trang, kich_thuoc=kich_thuoc, loai_tru=loai_tru)
        goi_y = [] if tong else goi_y_noi_dieu_kien(
            conn, ma_tinh=ma_tinh, ngay_nhan=ngay_nhan, ngay_tra=ngay_tra, so_nguoi=so_nguoi, so_phong=so_phong,
            ngan_sach=ngan_sach, loai_ngan_sach=loai_ngan_sach, loai_hinh=loai_hinh, ma_tien_nghi=ma_tien_nghi,
            loai_tru=loai_tru, hom_nay=hom_nay)
        if ghi_luot:
            repo.ghi_luot_tim(conn, ma_nguoi_dung=ma_nguoi_dung, ma_tinh=ma_tinh, nhan=ngay_nhan, tra=ngay_tra,
                              so_nguoi=so_nguoi, so_phong=so_phong, ngan_sach=ngan_sach,
                              loai_ngan_sach=loai_ngan_sach, so_ket_qua=tong)

    items = []
    for r in rows:
        c = ct[(r["ma_loai_phong"], r["ma_lien_ket"])]
        items.append({
            "ma_co_so": r["ma_co_so"], "ten": r["ten"], "loai_hinh": r["loai_hinh"], "dia_chi": r["dia_chi"],
            "khu_vuc": r["khu_vuc"], "hang_sao": r["hang_sao"],
            "diem_danh_gia": r["diem_xep"], "so_luot_danh_gia": r["so_luot_danh_gia"],
            "so_thich_khop": r["so_thich_khop"], "so_lua_chon": r["so_lua_chon"],
            "la_du_lieu_mau": r["la_du_lieu_mau"],
            "re_nhat": {
                "ma_loai_phong": r["ma_loai_phong"], "ten_loai_phong": c["ten_loai_phong"],
                "ten_ota": c["ten_ota"], "ma_lien_ket": r["ma_lien_ket"],
                "tong_ca_chuyen": r["tong_ca_chuyen"],
                "gia_tb_moi_dem_moi_phong": round(r["tong_ca_chuyen"] / so_dem / so_phong),
                "gom_thue_phi": True,                      # luôn là giá đã quy đổi (D-021)
                "gia_goc_gom_thue_phi": c["gia_goc_gom_thue_phi"],
                "cap_nhat_gia": c["cap_nhat_gia"],
            },
            # B-023 (D-021): OTA chưa gồm thuế, phí và chưa có tỷ lệ quy đổi → hiện riêng, KHÔNG vào phép so
            "gia_ngoai_phep_so": [{
                "ten_ota": x["ten_ota"], "ma_lien_ket": x["ma_lien_ket"], "ma_loai_phong": x["ma_loai_phong"],
                "ten_loai_phong": x["ten_loai_phong"], "tong_chua_gom_thue_phi": x["tong_chua_gom_thue_phi"],
                "gom_thue_phi": False, "so_sanh_duoc": False, "nhan": NHAN_NGOAI_PHEP_SO,
                "cap_nhat_gia": x["cap_nhat_gia"],
            } for x in ngoai.get(r["ma_co_so"], [])],
        })

    return {"items": items, "tong": tong, "trang": trang, "kich_thuoc": kich_thuoc, "so_dem": so_dem,
            "ghi_chu": GHI_CHU, "goi_y_noi_dieu_kien": goi_y}
