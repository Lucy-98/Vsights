"""Danh mục, /places và tìm chỗ ở theo dải ngày (D-021, D-028b, D-031, BR-04)."""
import uuid

from tests.conftest import ngay


def test_danh_muc_34_tinh(client):
    t = client.get("/catalog/provinces").json()
    assert len(t) == 34 and {"ma_tinh", "ten_tinh", "ma_vung"} <= set(t[0])
    assert len(client.get("/catalog/amenities").json()) == 14


def test_places_loc_va_phan_trang(client):
    r = client.get("/places", params={"ma_tinh": 21, "nhom": "an_uong", "kich_thuoc": 4}).json()
    assert r["tong"] == 6 and len(r["items"]) == 4 and r["trang"] == 1 and r["kich_thuoc"] == 4
    assert all(i["loai"]["nhom"] == "an_uong" and i["la_du_lieu_mau"] for i in r["items"])
    trang2 = client.get("/places", params={"ma_tinh": 21, "nhom": "an_uong", "kich_thuoc": 4, "trang": 2}).json()
    assert len(trang2["items"]) == 2
    assert not {i["ma_dia_diem"] for i in r["items"]} & {i["ma_dia_diem"] for i in trang2["items"]}
    # Tìm không dấu
    assert client.get("/places", params={"ma_tinh": 21, "q": "cho dem"}).json()["tong"] >= 1
    assert client.get("/places", params={"kich_thuoc": 101}).status_code == 422


def _tim(client, **p):
    base = {"ma_tinh": 21, "ngay_nhan": ngay(10), "ngay_tra": ngay(12), "so_nguoi": 2, "kich_thuoc": 100}
    return client.get("/stays/search", params={**base, **p})


def test_tim_tra_dung_hop_dong(client):
    r = _tim(client)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["so_dem"] == 2 and b["tong"] > 0 and "giá tham khảo" in b["ghi_chu"].lower()
    i = b["items"][0]
    assert {"ma_co_so", "ten", "loai_hinh", "dia_chi", "diem_danh_gia", "so_thich_khop", "so_lua_chon",
            "la_du_lieu_mau", "re_nhat"} <= set(i)
    assert {"ten_loai_phong", "ten_ota", "ma_lien_ket", "tong_ca_chuyen", "gia_tb_moi_dem_moi_phong",
            "gom_thue_phi", "cap_nhat_gia"} <= set(i["re_nhat"])
    assert "so_phong_con" not in str(b) and "còn phòng" not in str(b)


def test_tinh_khong_ton_tai_bi_chan_truoc_khong_lo_rang_buoc(client, sql):
    """B-024: mã tỉnh sai → 422 MA_KHONG_TON_TAI ngay, không ghi lượt tìm, không lộ tên ràng buộc CSDL."""
    truoc = sql("SELECT count(*) n FROM luot_tim_kiem")[0]["n"]
    r = _tim(client, ma_tinh=999)
    assert r.status_code == 422 and r.json()["ma_loi"] == "MA_KHONG_TON_TAI"
    assert "fkey" not in r.text and r.json()["chi_tiet"] == {"ma_tinh": 999}
    assert sql("SELECT count(*) n FROM luot_tim_kiem")[0]["n"] == truoc


def test_tim_kiem_du_lieu_vao(client):
    assert _tim(client, ngay_nhan=ngay(-1)).json()["ma_loi"] == "NGAY_KHONG_HOP_LE"
    assert _tim(client, ngay_tra=ngay(10)).json()["ma_loi"] == "NGAY_KHONG_HOP_LE"
    assert _tim(client, ngay_tra=ngay(41)).json()["ma_loi"] == "QUA_SO_DEM"
    r = _tim(client, so_nguoi=1, so_phong=2)
    assert r.status_code == 422 and r.json()["ma_loi"] == "SO_NGUOI_IT_HON_SO_PHONG"


def test_kha_dung_la_co_gia_du_moi_dem_tren_cung_mot_ota(client, sql):
    """Xoá giá 1 đêm của mọi OTA cho mọi loại phòng của một cơ sở → cơ sở biến khỏi kết quả."""
    ma = _tim(client).json()["items"][0]["ma_co_so"]
    sql("DELETE FROM gia_tham_khao g USING loai_phong lp WHERE lp.ma_loai_phong = g.ma_loai_phong "
        "AND lp.ma_co_so = :m AND g.ngay = CAST(:d AS date)", m=ma, d=ngay(11))
    assert ma not in [i["ma_co_so"] for i in _tim(client).json()["items"]]
    # Dải ngày không chứa đêm đó thì vẫn khả dụng
    assert ma in [i["ma_co_so"] for i in _tim(client, ngay_nhan=ngay(12), ngay_tra=ngay(14)).json()["items"]]


def test_d021_so_gia_tren_gia_da_gom_thue_phi(client, sql):
    """Dữ liệu mẫu: Booking.com niêm yết RẺ HƠN Agoda nhưng chưa gồm thuế phí (+15%); Agoda đã gồm.
    So thô sẽ chọn Booking.com; so đúng (D-021) chọn Agoda. Traveloka chưa gồm, chưa có tỷ lệ → không vào phép so."""
    b = _tim(client).json()
    assert all(i["re_nhat"]["ten_ota"] in ("Booking.com", "Agoda") for i in b["items"])
    i = b["items"][0]
    tong = {r["ten_ota"]: r for r in sql(
        "SELECT o.ten_ota, sum(g.gia_dem) tho, CASE WHEN bool_and(g.gom_thue_phi) THEN sum(g.gia_dem) "
        "ELSE round(sum(g.gia_dem) * (1 + max(o.ty_le_thue_phi)/100)) END quy_doi "
        "FROM gia_tham_khao g JOIN lien_ket_ota lk USING (ma_lien_ket) JOIN nguon_ota o USING (ma_ota) "
        "WHERE g.ma_loai_phong = :lp AND g.ngay >= CAST(:a AS date) AND g.ngay < CAST(:b AS date) GROUP BY o.ten_ota",
        lp=i["re_nhat"]["ma_loai_phong"], a=ngay(10), b=ngay(12))}
    assert tong["Booking.com"]["tho"] < tong["Agoda"]["tho"]            # so thô: Booking.com "rẻ hơn"
    assert tong["Booking.com"]["quy_doi"] > tong["Agoda"]["quy_doi"]    # đã gồm thuế phí: Agoda rẻ hơn
    assert i["re_nhat"]["ten_ota"] == "Agoda" and i["re_nhat"]["tong_ca_chuyen"] == tong["Agoda"]["quy_doi"]


def test_ngan_sach_theo_dem_va_ca_chuyen(client):
    moi_dem = _tim(client, ngan_sach=600000, loai_ngan_sach="moi_dem").json()
    assert moi_dem["tong"] > 0 and all(i["re_nhat"]["gia_tb_moi_dem_moi_phong"] <= 600000 for i in moi_dem["items"])
    ca = _tim(client, ngan_sach=600000, loai_ngan_sach="ca_chuyen").json()
    assert all(i["re_nhat"]["tong_ca_chuyen"] <= 600000 for i in ca["items"]) and ca["tong"] < moi_dem["tong"]
    rong = _tim(client, ngan_sach=1000, ma_tien_nghi=[2]).json()
    assert rong["tong"] == 0 and rong["goi_y_noi_dieu_kien"]


def test_loc_tien_nghi_loai_hinh_suc_chua(client, sql):
    co_ho_boi = {r["ma_co_so"] for r in sql("SELECT ma_co_so FROM co_so_tien_nghi WHERE ma_tien_nghi = 2")}
    kq = _tim(client, ma_tien_nghi=[2]).json()["items"]
    assert kq and all(i["ma_co_so"] in co_ho_boi for i in kq)
    assert all(i["loai_hinh"] == "resort" for i in _tim(client, loai_hinh="resort").json()["items"])
    # 4 người 1 phòng: chỉ còn loại phòng gia đình (sức chứa 4)
    assert all(i["re_nhat"]["ten_loai_phong"] == "Phòng Gia đình" for i in _tim(client, so_nguoi=4).json()["items"])


def test_sap_xep_br04(client):
    g = [i["re_nhat"]["tong_ca_chuyen"] for i in _tim(client, sap_xep="gia_tang").json()["items"]]
    assert g == sorted(g)
    p = [(-i["so_thich_khop"], i["re_nhat"]["tong_ca_chuyen"]) for i in _tim(client, ma_so_thich=[1, 3]).json()["items"]]
    assert p == sorted(p)
    d = [i["diem_danh_gia"] for i in _tim(client, sap_xep="danh_gia").json()["items"] if i["diem_danh_gia"] is not None]
    assert d == sorted(d, reverse=True)


def test_an_cho_o_thi_bien_khoi_tim_kiem_hien_lai_thi_co_lai(client, qt):
    """Ảnh minh chứng #5 (B-019)."""
    ma = _tim(client).json()["items"][0]["ma_co_so"]
    assert client.post(f"/admin/stays/{ma}/an", json={"ly_do": "Kiểm thử ẩn"}, headers=qt).status_code == 200
    assert ma not in [i["ma_co_so"] for i in _tim(client).json()["items"]]
    assert client.post(f"/admin/stays/{ma}/hien", headers=qt).status_code == 200
    assert ma in [i["ma_co_so"] for i in _tim(client).json()["items"]]


def test_lien_ket_hong_khong_vao_ket_qua(client, sql):
    sql("UPDATE lien_ket_ota SET trang_thai='hong' WHERE ma_co_so IN (SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh=22)")
    assert _tim(client, ma_tinh=22).json()["tong"] == 0
    sql("UPDATE lien_ket_ota SET trang_thai='hoat_dong' WHERE ma_co_so IN (SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh=22)")


def test_ghi_luot_tim_kiem_kem_loai_ngan_sach(client, sql):
    n = uuid.uuid4().int % 900000 + 100000
    _tim(client, ngan_sach=n, loai_ngan_sach="ca_chuyen")
    r = sql("SELECT loai_ngan_sach, so_ket_qua FROM luot_tim_kiem WHERE ngan_sach = :n", n=n)
    assert r and r[0]["loai_ngan_sach"] == "ca_chuyen"


def test_rang_buoc_csdl_chan_trung_dem_trong_lich_trinh(sql):
    """EXCLUDE USING gist: hai chỗ ở trùng đêm trong cùng lịch trình bị CSDL từ chối (23P01)."""
    import psycopg
    import pytest
    from sqlalchemy.exc import IntegrityError
    lt = sql("INSERT INTO lich_trinh (ma_chu, ma_tinh, ten, ngay_bat_dau, ngay_ket_thuc, so_nguoi) "
             "VALUES (2, 21, 'Kiểm thử', CAST(:a AS date), CAST(:b AS date), 2) RETURNING ma_lich_trinh",
             a=ngay(20), b=ngay(24))[0]["ma_lich_trinh"]
    sql("INSERT INTO cho_o_cua_toi (ma_nguoi_dung, ma_co_so, ma_lich_trinh, ngay_nhan, ngay_tra) "
        "VALUES (2, 1, :lt, CAST(:a AS date), CAST(:b AS date))", lt=lt, a=ngay(20), b=ngay(22))
    with pytest.raises(IntegrityError) as e:
        sql("INSERT INTO cho_o_cua_toi (ma_nguoi_dung, ma_co_so, ma_lich_trinh, ngay_nhan, ngay_tra) "
            "VALUES (2, 2, :lt, CAST(:a AS date), CAST(:b AS date))", lt=lt, a=ngay(21), b=ngay(23))
    assert isinstance(e.value.orig, psycopg.errors.ExclusionViolation)
    # Nối tiếp [20,22) và [22,24) không trùng (khoảng nửa mở)
    sql("INSERT INTO cho_o_cua_toi (ma_nguoi_dung, ma_co_so, ma_lich_trinh, ngay_nhan, ngay_tra) "
        "VALUES (2, 2, :lt, CAST(:a AS date), CAST(:b AS date))", lt=lt, a=ngay(22), b=ngay(24))
