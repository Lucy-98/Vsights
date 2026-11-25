"""T-013: chi tiết chỗ ở và bảng giá từng đêm (UC03, D-021, D-029(1), D-035, BR-03), B-023, B-028.
Ca nào sửa dữ liệu thì dùng tỉnh 30–33 (không ai khác dùng) để không ảnh hưởng ca khác."""
from datetime import date, timedelta

from tests.conftest import ngay


def _tim(client, **p):
    base = {"ma_tinh": 21, "ngay_nhan": ngay(10), "ngay_tra": ngay(12), "so_nguoi": 2, "kich_thuoc": 100}
    return client.get("/stays/search", params={**base, **p})


def _ct(client, ma, **p):
    base = {"ngay_nhan": ngay(10), "ngay_tra": ngay(12)}
    return client.get(f"/stays/{ma}", params={**base, **p})


def _ota(lp, ten):
    return next(o for o in lp["gia_theo_ota"] if o["ten_ota"] == ten)


def _co_so_tinh(sql, ma_tinh):
    return sql("SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh = :t ORDER BY ma_co_so", t=ma_tinh)[0]["ma_co_so"]


# ---------------------------------------------------------------- chi tiết: hợp đồng, quyền, dữ liệu vào
def test_chi_tiet_khong_ngay_va_co_ngay_dung_hop_dong(client):
    ma = _tim(client).json()["items"][0]["ma_co_so"]
    r = client.get(f"/stays/{ma}")                                   # khách vãng lai, không cần đăng nhập
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["ma_co_so"] == ma and b["so_dem"] is None and b["re_nhat"] is None and b["ngay_re_hon"] == []
    assert b["loai_phong"] and all(lp["gia_theo_ota"] == [] for lp in b["loai_phong"])
    assert "giá tham khảo" in b["ghi_chu"].lower() and "OTA" in b["ghi_chu"]
    c = _ct(client, ma).json()
    assert c["so_dem"] == 2 and c["re_nhat"] is not None
    assert "so_phong_con" not in str(c) and "còn phòng" not in str(c) and "đặt phòng" not in str(c)


def test_chi_tiet_404_va_422(client, qt):
    assert client.get("/stays/99999999").json()["ma_loi"] == "KHONG_TIM_THAY"
    ma = _tim(client).json()["items"][1]["ma_co_so"]
    assert client.post(f"/admin/stays/{ma}/an", json={"ly_do": "Kiểm thử T-013"}, headers=qt).status_code == 200
    try:
        r = client.get(f"/stays/{ma}")
        assert r.status_code == 404 and r.json()["ma_loi"] == "KHONG_TIM_THAY"    # ẩn = không lộ sự tồn tại
    finally:
        assert client.post(f"/admin/stays/{ma}/hien", headers=qt).status_code == 200
    assert client.get(f"/stays/{ma}", params={"ngay_nhan": ngay(10)}).json()["ma_loi"] == "NGAY_KHONG_HOP_LE"
    assert _ct(client, ma, ngay_nhan=ngay(-1)).json()["ma_loi"] == "NGAY_KHONG_HOP_LE"
    assert _ct(client, ma, ngay_tra=ngay(41)).json()["ma_loi"] == "QUA_SO_DEM"
    assert _ct(client, ma, so_nguoi=1, so_phong=2).json()["ma_loi"] == "SO_NGUOI_IT_HON_SO_PHONG"


# ---------------------------------------------------------------- rẻ nhất trùng với tìm kiếm (một quy tắc D-021)
def test_re_nhat_va_tong_trung_voi_the_tim_kiem(client):
    for so_phong, so_nguoi in ((1, 2), (2, 4)):
        for i in _tim(client, so_phong=so_phong, so_nguoi=so_nguoi).json()["items"][:6]:
            c = _ct(client, i["ma_co_so"], so_phong=so_phong, so_nguoi=so_nguoi).json()
            r = i["re_nhat"]
            assert c["re_nhat"] == [r["ma_loai_phong"], r["ma_lien_ket"]]
            lp = next(x for x in c["loai_phong"] if x["ma_loai_phong"] == r["ma_loai_phong"])
            o = next(x for x in lp["gia_theo_ota"] if x["ma_lien_ket"] == r["ma_lien_ket"])
            assert o["xep_hang_gia"] == 1 and o["tong_ca_chuyen"] == r["tong_ca_chuyen"]


# ---------------------------------------------------------------- bảng giá từng đêm, nhãn thuế phí, B-023
def test_bang_gia_tung_dem_theo_ota_va_nhan_thue_phi(client, sql):
    ma = next(i["ma_co_so"] for i in _tim(client).json()["items"] if i["gia_ngoai_phep_so"])   # có cả 3 OTA
    c = _ct(client, ma, ngay_tra=ngay(13)).json()
    goc = {(r["ma_loai_phong"], r["ten_ota"], r["ngay"].isoformat()): r["gia_dem"] for r in sql(
        "SELECT g.ma_loai_phong, o.ten_ota, g.ngay, g.gia_dem FROM gia_tham_khao g JOIN lien_ket_ota lk USING (ma_lien_ket) "
        "JOIN nguon_ota o USING (ma_ota) JOIN loai_phong lp USING (ma_loai_phong) WHERE lp.ma_co_so = :m", m=ma)}
    thay_traveloka = False
    for lp in c["loai_phong"]:
        for o in lp["gia_theo_ota"]:
            assert len(o["dem"]) == 3 and o["du_dem"]
            for d in o["dem"]:
                g = goc[(lp["ma_loai_phong"], o["ten_ota"], d["ngay"])]
                assert d["gia_dem"] == {"Agoda": g, "Booking.com": round(g * 1.15), "Traveloka": g}[o["ten_ota"]]
            if o["ten_ota"] == "Agoda":
                assert o["gom_thue_phi_goc"] and o["so_sanh_duoc"] and o["nhan_thue_phi"] == "đã gồm thuế, phí"
            elif o["ten_ota"] == "Booking.com":
                assert not o["gom_thue_phi_goc"] and o["so_sanh_duoc"]
                assert o["nhan_thue_phi"] == "đã quy đổi +15% thuế, phí"
            else:                                                    # D-021: hiện riêng, không so (B-023)
                thay_traveloka = True
                assert not o["so_sanh_duoc"] and o["xep_hang_gia"] is None
                assert o["nhan_thue_phi"] == "chưa gồm thuế, phí · không so"
            assert o["tong_ca_chuyen"] == sum(d["gia_dem"] for d in o["dem"])
            # OTA không so luôn đứng sau các OTA so được trong cùng loại phòng
        so = [o["so_sanh_duoc"] for o in lp["gia_theo_ota"]]
        assert so == sorted(so, reverse=True)
    assert thay_traveloka


def test_thieu_mot_dem_thi_khong_du_dem_khong_xep_hang(client, sql):
    ma = _co_so_tinh(sql, 30)
    lk = sql("SELECT lk.ma_lien_ket FROM lien_ket_ota lk JOIN nguon_ota o USING (ma_ota) "
             "WHERE lk.ma_co_so = :m AND o.ten_ota = 'Agoda'", m=ma)[0]["ma_lien_ket"]
    sql("DELETE FROM gia_tham_khao WHERE ma_lien_ket = :lk AND ngay = CAST(:d AS date)", lk=lk, d=ngay(11))
    c = _ct(client, ma).json()
    for lp in c["loai_phong"]:
        o = _ota(lp, "Agoda")
        assert not o["du_dem"] and o["tong_ca_chuyen"] is None and o["xep_hang_gia"] is None and len(o["dem"]) == 1
    assert c["re_nhat"] is None or c["re_nhat"][1] != lk


def test_gia_cu_qua_3_ngay_va_cap_nhat_la_lan_cu_nhat(client, sql):
    """BR-03: một đêm cập nhật 5 ngày trước → cả lựa chọn mang nhãn giá cũ, `cap_nhat_gia` là lần cũ nhất."""
    ma = _co_so_tinh(sql, 31)
    lk = sql("SELECT lk.ma_lien_ket FROM lien_ket_ota lk JOIN nguon_ota o USING (ma_ota) "
             "WHERE lk.ma_co_so = :m AND o.ten_ota = 'Booking.com'", m=ma)[0]["ma_lien_ket"]
    sql("UPDATE gia_tham_khao SET ngay_cap_nhat = now() - interval '5 days' "
        "WHERE ma_lien_ket = :lk AND ngay = CAST(:d AS date)", lk=lk, d=ngay(11))
    for lp in _ct(client, ma).json()["loai_phong"]:
        assert _ota(lp, "Booking.com")["gia_cu"] is True and _ota(lp, "Agoda")["gia_cu"] is False
        cu = date.fromisoformat(_ota(lp, "Booking.com")["cap_nhat_gia"][:10])
        assert (date.today() - cu).days >= 4


def test_suc_chua_chi_xep_hang_loai_phong_du_cho(client):
    ma = _tim(client, so_nguoi=4).json()["items"][0]["ma_co_so"]
    c = _ct(client, ma, so_nguoi=4).json()
    for lp in c["loai_phong"]:
        assert lp["du_suc_chua"] == (lp["suc_chua_nl"] >= 4)
        if not lp["du_suc_chua"]:
            assert all(o["xep_hang_gia"] is None for o in lp["gia_theo_ota"])
    hang = sorted(o["xep_hang_gia"] for lp in c["loai_phong"] for o in lp["gia_theo_ota"] if o["xep_hang_gia"])
    assert hang == list(range(1, len(hang) + 1))


def test_ngay_re_hon_trong_3_ngay(client, sql):
    """UC03-A4: hạ giá mọi OTA cho các đêm của khoảng dời +2 ngày → khoảng đó xuất hiện và rẻ hơn."""
    ma = _co_so_tinh(sql, 32)
    hien_tai = _ct(client, ma).json()
    assert hien_tai["re_nhat"]
    sql("UPDATE gia_tham_khao g SET gia_dem = 100000 FROM loai_phong lp WHERE lp.ma_loai_phong = g.ma_loai_phong "
        "AND lp.ma_co_so = :m AND g.ngay >= CAST(:a AS date) AND g.ngay < CAST(:b AS date)", m=ma, a=ngay(12), b=ngay(14))
    c = _ct(client, ma).json()
    tong_hien_tai = min(o["tong_ca_chuyen"] for lp in c["loai_phong"] for o in lp["gia_theo_ota"] if o["xep_hang_gia"] == 1)
    assert 1 <= len(c["ngay_re_hon"]) <= 3
    assert {"ngay_nhan": ngay(12), "ngay_tra": ngay(14)} == {k: c["ngay_re_hon"][0][k] for k in ("ngay_nhan", "ngay_tra")}
    for k in c["ngay_re_hon"]:
        assert k["tong_ca_chuyen"] < tong_hien_tai and k["ngay_nhan"] >= ngay(7) and k["ngay_nhan"] != ngay(10)
        assert (date.fromisoformat(k["ngay_tra"]) - date.fromisoformat(k["ngay_nhan"])).days == 2
    # Nhận phòng hôm nay: không gợi ý ngày trong quá khứ
    assert all(k["ngay_nhan"] >= ngay(0) for k in _ct(client, ma, ngay_nhan=ngay(0), ngay_tra=ngay(2)).json()["ngay_re_hon"])


def test_service_chay_trong_giao_dich_read_only(sql):
    """Công cụ chatbot `xem_cho_o` gọi đúng hàm này trong giao dịch READ ONLY (SA-017)."""
    from sqlalchemy import text
    from app.core.db import engine
    from app.services import gia
    from app.services.hop_dong import ChiTietChoO
    ma = _co_so_tinh(sql, 21)
    with engine().connect() as conn, conn.begin():
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text("SET LOCAL statement_timeout = '2s'"))
        kq = gia.chi_tiet_cho_o(conn, ma_co_so=ma, ngay_nhan=date.today() + timedelta(days=10),
                                ngay_tra=date.today() + timedelta(days=12), hom_nay=date.today())
    assert isinstance(kq, ChiTietChoO) and kq.so_dem == 2


# ---------------------------------------------------------------- B-023 trên /stays/search
def test_tim_kiem_hien_rieng_gia_chua_gom_thue_phi(client, sql):
    items = _tim(client).json()["items"]
    co = [i for i in items if i["gia_ngoai_phep_so"]]
    assert co, "dữ liệu mẫu tỉnh 21 phải có cơ sở có liên kết Traveloka"
    for i in co:
        for x in i["gia_ngoai_phep_so"]:
            assert x["ten_ota"] == "Traveloka" and x["nhan"] == "chưa gồm thuế, phí · không so"
            assert x["so_sanh_duoc"] is False and x["gom_thue_phi"] is False
            tho = sql("SELECT sum(gia_dem) s, count(*) n FROM gia_tham_khao WHERE ma_loai_phong = :lp AND ma_lien_ket = :lk "
                      "AND ngay >= CAST(:a AS date) AND ngay < CAST(:b AS date)",
                      lp=x["ma_loai_phong"], lk=x["ma_lien_ket"], a=ngay(10), b=ngay(12))[0]
            assert tho["n"] == 2 and x["tong_chua_gom_thue_phi"] == tho["s"]
        assert i["re_nhat"]["ten_ota"] != "Traveloka"
    assert all(i["gia_ngoai_phep_so"] == [] for i in items if i not in co)


# ---------------------------------------------------------------- B-028, trang vượt số trang
def test_goi_y_noi_dieu_kien_co_so_ket_qua_that(client):
    b = _tim(client, ngan_sach=1000, ma_tien_nghi=[2, 3]).json()
    assert b["tong"] == 0
    gy = {(g["dieu_kien"], str(g["gia_tri"])): g for g in b["goi_y_noi_dieu_kien"]}
    assert all({"dieu_kien", "gia_tri", "nhan", "so_ket_qua"} == set(g) for g in gy.values())
    g = gy[("ngan_sach", "None")]                                          # bỏ ngân sách thì có kết quả
    assert g["so_ket_qua"] == _tim(client, ma_tien_nghi=[2, 3]).json()["tong"] > 0
    assert all(k[0] != "ma_tien_nghi" for k in gy)                          # bỏ tiện nghi vẫn 0 kết quả → không gợi ý
    b2 = _tim(client, ma_tien_nghi=[2, 3], loai_hinh="nha_nghi").json()
    if b2["tong"] == 0:
        for g in b2["goi_y_noi_dieu_kien"]:
            assert g["so_ket_qua"] and g["so_ket_qua"] > 0
            if g["dieu_kien"] == "ma_tien_nghi" and g["gia_tri"]:
                con = [m for m in (2, 3) if m != g["gia_tri"]]
                assert _tim(client, ma_tien_nghi=con, loai_hinh="nha_nghi").json()["tong"] == g["so_ket_qua"]
                assert g["nhan"].startswith("Bỏ “")
            if g["dieu_kien"] == "loai_hinh":
                assert _tim(client, ma_tien_nghi=[2, 3]).json()["tong"] == g["so_ket_qua"]


def test_goi_y_doi_ngay_va_goi_y_chung(client, sql):
    sql("DELETE FROM gia_tham_khao g USING loai_phong lp, co_so_luu_tru cs WHERE lp.ma_loai_phong = g.ma_loai_phong "
        "AND cs.ma_co_so = lp.ma_co_so AND cs.ma_tinh = 33 AND g.ngay = CAST(:d AS date)", d=ngay(11))
    b = _tim(client, ma_tinh=33).json()
    assert b["tong"] == 0
    g = b["goi_y_noi_dieu_kien"][0]
    assert g["dieu_kien"] == "ngay_nhan" and g["gia_tri"] == {"ngay_nhan": ngay(9), "ngay_tra": ngay(11)}  # +1 vẫn chứa đêm thiếu → -1
    assert g["so_ket_qua"] == _tim(client, ma_tinh=33, **g["gia_tri"]).json()["tong"] > 0
    # Mọi liên kết của tỉnh hỏng → không nới được gì → một gợi ý chung, không có số
    sql("UPDATE lien_ket_ota SET trang_thai='hong' WHERE ma_co_so IN (SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh=33)")
    try:
        assert _tim(client, ma_tinh=33).json()["goi_y_noi_dieu_kien"] == [
            {"dieu_kien": "ma_tinh", "gia_tri": None, "nhan": "Thử tỉnh, thành khác hoặc ngày khác", "so_ket_qua": None}]
    finally:
        sql("UPDATE lien_ket_ota SET trang_thai='hoat_dong' WHERE ma_co_so IN (SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh=33)")


def test_xin_trang_vuot_so_trang_van_tra_dung_tong(client):
    tong = _tim(client).json()["tong"]
    b = _tim(client, kich_thuoc=10, trang=99).json()
    assert b["items"] == [] and b["tong"] == tong and b["goi_y_noi_dieu_kien"] == []
