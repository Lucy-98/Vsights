"""T-014: so sánh 2–3 chỗ ở — GET /stays/compare, services/so_sanh.so_sanh (UC09; D-022, D-029(4), D-031; SA_T003).
Ca nào sửa dữ liệu thì dùng tỉnh 26–29 và trả lại trong finally."""
from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt

from tests.conftest import ngay

HANG_CO_DINH = ["gia_ca_chuyen", "gia_tb_dem", "ota_re_nhat", "diem_danh_gia", "hang_sao", "loai_phong", "bua_sang",
                "chinh_sach_huy", "huy_mien_phi", "thanh_toan_tai_cho", "suc_chua", "dien_tich"]


def _ss(client, ma, **p):
    base = {"ma_co_so": ma, "ngay_nhan": ngay(10), "ngay_tra": ngay(12)}
    return client.get("/stays/compare", params={**base, **p})


def _tim(client, ma_tinh=21, **p):
    r = client.get("/stays/search", params={"ma_tinh": ma_tinh, "ngay_nhan": ngay(10), "ngay_tra": ngay(12),
                                            "kich_thuoc": 100, **p})
    return r.json()["items"]


def _hang(b, ma):
    return next(h for h in b["hang"] if h["ma_hang"] == ma)


def _o(h, ma_co_so):
    return next(o for o in h["cac_o"] if o["ma_co_so"] == ma_co_so)


def _co_so_tinh(sql, t, n=3):
    return [r["ma_co_so"] for r in sql("SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh = :t AND trang_thai = 'hien' "
                                       "ORDER BY ma_co_so LIMIT :n", t=t, n=n)]


def test_hop_dong_hang_va_gia_trung_the_tim_kiem(client):
    items = _tim(client)[:3]
    ma = [i["ma_co_so"] for i in items]
    r = _ss(client, ma)                                           # khách vãng lai, không token
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["ma_co_so"] == ma and b["so_dem"] == 2
    assert [h["ma_hang"] for h in b["hang"] if not h["ma_hang"].startswith(("khoang_cach", "tien_nghi", "gia_khong_so"))] \
        == HANG_CO_DINH
    t = r.text.lower()
    for cam in ("còn phòng", "đặt phòng", "so_phong_con", "chỉ còn", "tốt nhất tổng"):
        assert cam not in t, cam
    assert "giá tham khảo" in b["ghi_chu"].lower() and "không chọn hộ" in b["ghi_chu"]
    g = _hang(b, "gia_ca_chuyen")
    assert g["la_tien"] and _hang(b, "gia_tb_dem")["la_tien"] and not _hang(b, "hang_sao")["la_tien"]
    for i in items:
        o = _o(g, i["ma_co_so"])
        assert o["gia_tri"] == i["re_nhat"]["tong_ca_chuyen"] and "đã gồm thuế, phí" in o["hien_thi"]
        assert _o(_hang(b, "ota_re_nhat"), i["ma_co_so"])["gia_tri"] == i["re_nhat"]["ten_ota"]
        assert _o(_hang(b, "gia_tb_dem"), i["ma_co_so"])["gia_tri"] == i["re_nhat"]["gia_tb_moi_dem_moi_phong"]
    re_nhat = min(i["re_nhat"]["tong_ca_chuyen"] for i in items)
    assert g["o_tot_nhat"] == [i["ma_co_so"] for i in items if i["re_nhat"]["tong_ca_chuyen"] == re_nhat]
    assert _hang(b, "ota_re_nhat")["o_tot_nhat"] == [] and _hang(b, "suc_chua")["o_tot_nhat"] == []


def test_hai_phong_va_so_nguoi(client):
    items = _tim(client, so_nguoi=4, so_phong=2)[:2]
    b = _ss(client, [i["ma_co_so"] for i in items], so_nguoi=4, so_phong=2).json()
    for i in items:
        assert _o(_hang(b, "gia_ca_chuyen"), i["ma_co_so"])["gia_tri"] == i["re_nhat"]["tong_ca_chuyen"]
        assert _o(_hang(b, "loai_phong"), i["ma_co_so"])["gia_tri"] == i["re_nhat"]["ten_loai_phong"]


def test_loi_dau_vao(client, sql, qt):
    a, b, c, d = _co_so_tinh(sql, 21, 4)
    khac = _co_so_tinh(sql, 22, 1)[0]
    assert _ss(client, [a]).json()["ma_loi"] == "SO_LUONG_SO_SANH"
    assert _ss(client, [a, a]).json()["ma_loi"] == "SO_LUONG_SO_SANH"          # trùng mã tính một lần
    assert _ss(client, [a, b, c, d]).json()["ma_loi"] == "SO_LUONG_SO_SANH"
    assert _ss(client, [a, khac]).json()["ma_loi"] == "KHAC_TINH"
    assert _ss(client, [a, 99999999]).status_code == 404
    assert _ss(client, [a, b], ngay_nhan=ngay(-1)).json()["ma_loi"] == "NGAY_KHONG_HOP_LE"
    assert _ss(client, [a, b], ngay_tra=ngay(45)).json()["ma_loi"] == "QUA_SO_DEM"
    assert _ss(client, [a, b], so_nguoi=1, so_phong=2).json()["ma_loi"] == "SO_NGUOI_IT_HON_SO_PHONG"
    assert _ss(client, [a, b], diem=["bien:1"]).json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert _ss(client, [a, b], diem=["dia_diem:99999999"]).status_code == 404
    dd_khac = sql("SELECT ma_dia_diem FROM dia_diem WHERE ma_tinh = 22 LIMIT 1")[0]["ma_dia_diem"]
    assert _ss(client, [a, b], diem=[f"dia_diem:{dd_khac}"]).json()["ma_loi"] == "KHAC_TINH"
    assert _ss(client, [a, b], ma_tien_nghi=[999]).json()["ma_loi"] == "MA_KHONG_TON_TAI"
    assert client.post(f"/admin/stays/{b}/an", json={"ly_do": "Kiểm thử T-014"}, headers=qt).status_code == 200
    try:
        r = _ss(client, [a, b])
        assert r.status_code == 404 and r.json()["ma_loi"] == "KHONG_TIM_THAY"
    finally:
        assert client.post(f"/admin/stays/{b}/hien", headers=qt).status_code == 200


def test_chua_co_thong_tin_va_chua_du_danh_gia(client, sql):
    a, b = _co_so_tinh(sql, 26, 2)
    cu_cs = sql("SELECT ma_co_so, hang_sao, so_luot_danh_gia, chinh_sach_huy FROM co_so_luu_tru WHERE ma_co_so = :a", a=a)[0]
    cu_lp = sql("SELECT ma_loai_phong, dien_tich, so_ngay_huy_mien_phi, thanh_toan_tai_cho, dieu_kien_huy "
                "FROM loai_phong WHERE ma_co_so = :a", a=a)
    try:
        sql("UPDATE co_so_luu_tru SET hang_sao = NULL, so_luot_danh_gia = 2, chinh_sach_huy = NULL WHERE ma_co_so = :a", a=a)
        sql("UPDATE loai_phong SET dien_tich = NULL, so_ngay_huy_mien_phi = NULL, thanh_toan_tai_cho = NULL, "
            "dieu_kien_huy = NULL WHERE ma_co_so = :a", a=a)
        bb = _ss(client, [a, b]).json()
        assert _o(_hang(bb, "diem_danh_gia"), a) == {"ma_co_so": a, "hien_thi": "Chưa đủ đánh giá", "gia_tri": None}
        for ma_hang in ("hang_sao", "dien_tich", "huy_mien_phi", "thanh_toan_tai_cho", "chinh_sach_huy"):
            o = _o(_hang(bb, ma_hang), a)
            assert o["hien_thi"] == "Chưa có thông tin" and o["gia_tri"] is None, ma_hang
            assert a not in _hang(bb, ma_hang)["o_tot_nhat"]
    finally:
        sql("UPDATE co_so_luu_tru SET hang_sao = :h, so_luot_danh_gia = :s, chinh_sach_huy = :c WHERE ma_co_so = :a",
            h=cu_cs["hang_sao"], s=cu_cs["so_luot_danh_gia"], c=cu_cs["chinh_sach_huy"], a=a)
        for r in cu_lp:
            sql("UPDATE loai_phong SET dien_tich = :d, so_ngay_huy_mien_phi = :n, thanh_toan_tai_cho = :t, "
                "dieu_kien_huy = :k WHERE ma_loai_phong = :m", d=r["dien_tich"], n=r["so_ngay_huy_mien_phi"],
                t=r["thanh_toan_tai_cho"], k=r["dieu_kien_huy"], m=r["ma_loai_phong"])


def test_han_huy_mien_phi_va_cac_hang_co_khong(client, sql):
    """Hạn huỷ: ít ngày (> 0) hơn là tốt hơn, 0 = 'Không huỷ miễn phí' không được tô; bữa sáng, thanh toán tại chỗ:
    tô ô 'Có' khi các ô khác nhau; mọi ô bằng nhau thì không tô."""
    a, b, c = _co_so_tinh(sql, 27, 3)
    cu = sql("SELECT ma_loai_phong, so_ngay_huy_mien_phi, co_bua_sang, thanh_toan_tai_cho FROM loai_phong "
             "WHERE ma_co_so = ANY(:m)", m=[a, b, c])
    try:
        for m, han, sang, tt in ((a, 0, True, True), (b, 3, False, False), (c, 1, False, True)):
            sql("UPDATE loai_phong SET so_ngay_huy_mien_phi = :h, co_bua_sang = :s, thanh_toan_tai_cho = :t "
                "WHERE ma_co_so = :m", h=han, s=sang, t=tt, m=m)
        bb = _ss(client, [a, b, c]).json()
        h = _hang(bb, "huy_mien_phi")
        assert _o(h, a)["hien_thi"] == "Không huỷ miễn phí"
        assert _o(h, b)["hien_thi"] == "Huỷ miễn phí trước 3 ngày nhận phòng"
        assert h["o_tot_nhat"] == [c]
        assert _hang(bb, "bua_sang")["o_tot_nhat"] == [a] and _o(_hang(bb, "bua_sang"), b)["hien_thi"] == "Không gồm bữa sáng"
        assert _hang(bb, "thanh_toan_tai_cho")["o_tot_nhat"] == [a, c]
        sql("UPDATE loai_phong SET co_bua_sang = TRUE WHERE ma_co_so = ANY(:m)", m=[a, b, c])
        assert _hang(_ss(client, [a, b, c]).json(), "bua_sang")["o_tot_nhat"] == []
    finally:
        for r in cu:
            sql("UPDATE loai_phong SET so_ngay_huy_mien_phi = :h, co_bua_sang = :s, thanh_toan_tai_cho = :t "
                "WHERE ma_loai_phong = :m", h=r["so_ngay_huy_mien_phi"], s=r["co_bua_sang"],
                t=r["thanh_toan_tai_cho"], m=r["ma_loai_phong"])


def test_tien_nghi_da_loc_doi_chieu_csdl(client, sql):
    ma = [i["ma_co_so"] for i in _tim(client)[:3]]
    tn = [r["ma_tien_nghi"] for r in sql("SELECT ma_tien_nghi FROM tien_nghi ORDER BY 1")]
    bb = _ss(client, ma, ma_tien_nghi=tn).json()
    lp_so = {m: _o(_hang(bb, "loai_phong"), m)["gia_tri"] for m in ma}
    for t in tn:
        h = _hang(bb, f"tien_nghi:{t}")
        for m in ma:
            co = sql("SELECT EXISTS (SELECT 1 FROM co_so_tien_nghi WHERE ma_co_so = :m AND ma_tien_nghi = :t) OR EXISTS ("
                     "SELECT 1 FROM loai_phong_tien_nghi x JOIN loai_phong lp USING (ma_loai_phong) WHERE lp.ma_co_so = :m "
                     "AND lp.ten_loai_phong = :lp AND lp.trang_thai = 'hien' AND x.ma_tien_nghi = :t) AS co",
                     m=m, t=t, lp=lp_so[m])[0]["co"]
            assert _o(h, m)["gia_tri"] is co and _o(h, m)["hien_thi"] == ("Có" if co else "Không")
        vals = [_o(h, m)["gia_tri"] for m in ma]
        assert h["o_tot_nhat"] == ([] if len(set(vals)) == 1 else [m for m in ma if _o(h, m)["gia_tri"]])


def _km(a, b, c, d):
    a, b, c, d = map(lambda v: radians(float(v)), (a, b, c, d))
    return round(2 * 6371.0 * asin(sqrt(sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2)), 1)


def test_khoang_cach_toi_diem_du_khach_chon(client, sql):
    ma = [i["ma_co_so"] for i in _tim(client)[:3]]
    dd = sql("SELECT ma_dia_diem, ten, vi_do, kinh_do FROM dia_diem WHERE ma_tinh = 21 AND trang_thai = 'hien' "
             "ORDER BY ma_dia_diem LIMIT 1")[0]
    bb = _ss(client, ma, diem=[f"dia_diem:{dd['ma_dia_diem']}", f"cho_o:{ma[0]}"]).json()
    h = _hang(bb, f"khoang_cach:dia_diem:{dd['ma_dia_diem']}")
    assert h["nhan"] == f"Khoảng cách tới {dd['ten']}"
    for m in ma:
        cs = sql("SELECT vi_do, kinh_do FROM co_so_luu_tru WHERE ma_co_so = :m", m=m)[0]
        o = _o(h, m)
        assert o["gia_tri"] == _km(cs["vi_do"], cs["kinh_do"], dd["vi_do"], dd["kinh_do"])
        assert o["hien_thi"].endswith("km (ước tính)")
    assert h["o_tot_nhat"] == [m for m in ma if _o(h, m)["gia_tri"] == min(_o(h, x)["gia_tri"] for x in ma)]
    tu_cho_o = _hang(bb, f"khoang_cach:cho_o:{ma[0]}")
    assert _o(tu_cho_o, ma[0])["gia_tri"] == 0.0 and tu_cho_o["o_tot_nhat"] == [ma[0]]
    assert not any(h["ma_hang"] == "khoang_cach_toi_bien" for h in bb["hang"])        # D-022b: không cố định "Tới biển"
    assert _ss(client, ma, diem=[f"dia_diem:{dd['ma_dia_diem']}"] * 6).status_code == 422


def test_gia_khong_so_hien_rieng_khong_to(client):
    items = _tim(client)
    co = [i for i in items if i["gia_ngoai_phep_so"]][:1]
    khong = [i for i in items if i not in co][:1]
    bb = _ss(client, [co[0]["ma_co_so"], khong[0]["ma_co_so"]]).json()
    h = _hang(bb, "gia_khong_so")
    assert h["la_tien"] and h["o_tot_nhat"] == []
    o = _o(h, co[0]["ma_co_so"])
    assert o["gia_tri"] == min(x["tong_chua_gom_thue_phi"] for x in co[0]["gia_ngoai_phep_so"])
    assert "chưa gồm thuế, phí · không so" in o["hien_thi"] and "Traveloka" in o["hien_thi"]
    assert _o(h, khong[0]["ma_co_so"])["hien_thi"] == "Không có"
    assert all(x["gia_tri"] != "Traveloka" for x in _hang(bb, "ota_re_nhat")["cac_o"])


def test_co_so_chua_du_gia_khong_duoc_to(client, sql):
    a, b = _co_so_tinh(sql, 28, 2)
    sql("DELETE FROM gia_tham_khao g USING loai_phong lp WHERE lp.ma_loai_phong = g.ma_loai_phong AND lp.ma_co_so = :a "
        "AND g.ngay = CAST(:n AS date)", a=a, n=ngay(11))
    bb = _ss(client, [a, b]).json()
    for ma_hang in ("gia_ca_chuyen", "gia_tb_dem", "ota_re_nhat"):
        assert _o(_hang(bb, ma_hang), a)["hien_thi"] == "Chưa có giá cho đủ các đêm"
    assert _hang(bb, "gia_ca_chuyen")["o_tot_nhat"] == [b]
    assert _o(_hang(bb, "loai_phong"), a)["gia_tri"] is not None        # vẫn so loại phòng đủ sức chứa đầu tiên


def test_service_chay_trong_giao_dich_read_only(sql):
    """Công cụ chatbot `so_sanh_cho_o` gọi đúng hàm này trong giao dịch READ ONLY (SA-017)."""
    from sqlalchemy import text
    from app.core.db import engine
    from app.services import so_sanh
    from app.services.hop_dong import Diem, SoSanh
    a, b = _co_so_tinh(sql, 21, 2)
    with engine().connect() as conn, conn.begin():
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text("SET LOCAL statement_timeout = '2s'"))
        kq = so_sanh.so_sanh(conn, ma_co_so=[a, b], ngay_nhan=date.today() + timedelta(days=10),
                             ngay_tra=date.today() + timedelta(days=12), so_nguoi=2, so_phong=1,
                             diem_tham_chieu=[Diem(loai="cho_o", ma=a)], hom_nay=date.today())
    assert isinstance(kq, SoSanh) and kq.so_dem == 2 and len(kq.hang) >= 13
