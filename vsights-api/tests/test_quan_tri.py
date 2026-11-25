"""CRUD quản trị chỗ ở, loại phòng, địa điểm. "Xoá" = ẩn kèm lý do; không có DELETE."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import jwt as pyjwt
import pytest

from tests.conftest import ORIGIN


def _co_so(**them):
    return {"ma_tinh": 21, "ten": f"Khách sạn Kiểm Thử {uuid.uuid4().hex[:6]}", "loai_hinh": "khach_san",
            "dia_chi": "1 đường Kiểm thử, Đà Nẵng", "hang_sao": 3, "ma_tien_nghi": [1, 2], **them}


@pytest.mark.parametrize("method,path", [
    ("get", "/admin/stays"), ("post", "/admin/stays"), ("get", "/admin/stays/1"), ("patch", "/admin/stays/1"),
    ("post", "/admin/stays/1/an"), ("post", "/admin/stays/1/hien"), ("get", "/admin/stays/1/room-types"),
    ("post", "/admin/stays/1/room-types"), ("get", "/admin/room-types/1"), ("patch", "/admin/room-types/1"),
    ("post", "/admin/room-types/1/an"), ("get", "/admin/places"), ("post", "/admin/places"),
    ("patch", "/admin/places/1"), ("post", "/admin/places/1/an")])
def test_quyen_401_khi_thieu_token_403_khi_khong_phai_quan_tri(client, dk, method, path):
    assert getattr(client, method)(path).status_code == 401
    r = getattr(client, method)(path, headers=dk) if method == "get" else getattr(client, method)(path, headers=dk, json={})
    assert r.status_code == 403 and r.json()["ma_loi"] == "KHONG_DU_QUYEN"


def test_BM07_sua_claim_vai_tro_trong_token_khong_co_tac_dung(client, dk):
    claims = pyjwt.decode(dk["Authorization"][7:], options={"verify_signature": False})
    gia = pyjwt.encode({**claims, "role": "quan_tri", "vai_tro": "quan_tri"}, "khoa-doan-mo" * 4, algorithm="HS256")
    assert client.get("/admin/stays", headers={"Authorization": f"Bearer {gia}"}).status_code == 401


def test_khong_co_endpoint_delete(client, qt):
    for p in ("/admin/stays/1", "/admin/room-types/1", "/admin/places/1"):
        assert client.delete(p, headers=qt).status_code == 405


def test_tao_doc_sua_co_so_va_ghi_nhat_ky(client, qt, sql):
    r = client.post("/admin/stays", json=_co_so(), headers=qt)
    assert r.status_code == 201, r.text
    cs = r.json()
    assert cs["trang_thai"] == "hien" and cs["ma_tien_nghi"] == [1, 2] and cs["ten_tinh"] == "Đà Nẵng"
    ma = cs["ma_co_so"]
    assert client.get(f"/admin/stays/{ma}", headers=qt).json()["ten"] == cs["ten"]
    r = client.patch(f"/admin/stays/{ma}", json={"hang_sao": 5, "ma_tien_nghi": [3]}, headers=qt)
    assert r.status_code == 200 and r.json()["hang_sao"] == 5 and r.json()["ma_tien_nghi"] == [3]
    assert r.json()["ten"] == cs["ten"]                         # PATCH chỉ đổi trường gửi lên
    nk = sql("SELECT hanh_dong FROM nhat_ky_quan_tri WHERE doi_tuong='co_so_luu_tru' AND ma_doi_tuong=:m "
             "ORDER BY ma_nhat_ky", m=ma)
    assert [x["hanh_dong"] for x in nk] == ["tao", "sua"]


def test_tao_co_so_du_lieu_sai(client, qt):
    r = client.post("/admin/stays", json=_co_so(hang_sao=9, loai_hinh="lau_dai"), headers=qt)
    assert r.status_code == 422 and {c["truong"] for c in r.json()["chi_tiet"]} >= {"hang_sao", "loai_hinh"}
    r = client.post("/admin/stays", json=_co_so(ma_tinh=999), headers=qt)
    assert r.status_code == 422 and r.json()["ma_loi"] == "MA_KHONG_TON_TAI"
    r = client.post("/admin/stays", json=_co_so(ma_tien_nghi=[9]), headers=qt)   # 9 = Điều hoà, phạm vi phòng
    assert r.status_code == 422 and r.json()["ma_loi"] == "TIEN_NGHI_KHONG_HOP_LE"
    r = client.patch("/admin/stays/1", json={"ten": None}, headers=qt)
    assert r.status_code == 422


def test_chan_trung_co_so_ke_ca_khi_gui_song_song(app, qt):
    from fastapi.testclient import TestClient
    body = _co_so()

    def tao(_):
        with TestClient(app, base_url="https://testserver") as c:
            return c.post("/admin/stays", json=body, headers=qt).status_code
    with ThreadPoolExecutor(4) as ex:
        kq = sorted(ex.map(tao, range(4)))
    assert kq == [201, 409, 409, 409]


def test_an_can_ly_do_va_khong_doi_trang_thai_thi_409(client, qt):
    ma = client.post("/admin/stays", json=_co_so(), headers=qt).json()["ma_co_so"]
    assert client.post(f"/admin/stays/{ma}/an", json={"ly_do": "x"}, headers=qt).status_code == 422
    assert client.post(f"/admin/stays/{ma}/hien", headers=qt).json()["ma_loi"] == "TRANG_THAI_KHONG_DOI"
    r = client.post(f"/admin/stays/{ma}/an", json={"ly_do": "Cơ sở ngừng kinh doanh"}, headers=qt)
    assert r.status_code == 200 and r.json()["trang_thai"] == "an"
    r = client.post(f"/admin/stays/{ma}/an", json={"ly_do": "Lần hai"}, headers=qt)
    assert r.status_code == 409 and r.json()["ma_loi"] == "TRANG_THAI_KHONG_DOI"
    assert client.post(f"/admin/stays/{ma}/hien", headers=qt).json()["trang_thai"] == "hien"
    assert client.get("/admin/stays/999999", headers=qt).json()["ma_loi"] == "KHONG_TIM_THAY"


def test_loai_phong_crud_co_cot_d031(client, qt):
    ma = client.post("/admin/stays", json=_co_so(), headers=qt).json()["ma_co_so"]
    body = {"ten_loai_phong": "Phòng Đôi", "suc_chua_nl": 2, "suc_chua_te": 1, "co_bua_sang": True,
            "thanh_toan_tai_cho": True, "so_ngay_huy_mien_phi": 2, "ma_tien_nghi": [9, 10]}
    r = client.post(f"/admin/stays/{ma}/room-types", json=body, headers=qt)
    assert r.status_code == 201, r.text
    lp = r.json()
    assert lp["thanh_toan_tai_cho"] is True and lp["so_ngay_huy_mien_phi"] == 2 and lp["ma_tien_nghi"] == [9, 10]
    assert [x["ma_loai_phong"] for x in client.get(f"/admin/stays/{ma}/room-types", headers=qt).json()] == [lp["ma_loai_phong"]]
    r = client.patch(f"/admin/room-types/{lp['ma_loai_phong']}", json={"suc_chua_nl": 3, "so_ngay_huy_mien_phi": None}, headers=qt)
    assert r.json()["suc_chua_nl"] == 3 and r.json()["so_ngay_huy_mien_phi"] is None
    assert client.post(f"/admin/stays/{ma}/room-types", json={**body, "suc_chua_nl": 0}, headers=qt).status_code == 422
    assert client.post(f"/admin/stays/{ma}/room-types", json={**body, "ma_tien_nghi": [1]}, headers=qt).json()["ma_loi"] \
        == "TIEN_NGHI_KHONG_HOP_LE"
    assert client.post("/admin/stays/999999/room-types", json=body, headers=qt).status_code == 404
    r = client.post(f"/admin/room-types/{lp['ma_loai_phong']}/an", json={"ly_do": "Ngừng bán"}, headers=qt)
    assert r.json()["trang_thai"] == "an"


def test_dia_diem_crud_va_an_khoi_trang_cong_khai(client, qt):
    body = {"ma_tinh": 21, "ma_loai": 1, "ten": f"Đỉnh Kiểm Thử {uuid.uuid4().hex[:6]}", "muc_gia_nguoi_tu": 0,
            "muc_gia_nguoi_den": 50000, "ma_so_thich": [2, 5],
            "gio_mo_cua": [{"thu_trong_tuan": 1, "gio_mo": "07:00", "gio_dong": "17:00"}],
            "gia_ve": [{"loai_khach": "Người lớn", "gia": 50000}]}
    r = client.post("/admin/places", json=body, headers=qt)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["ma_so_thich"] == [2, 5] and d["gio_mo_cua"][0]["gio_mo"] == "07:00" and d["gia_ve"][0]["gia"] == 50000
    ma = d["ma_dia_diem"]
    r = client.patch(f"/admin/places/{ma}", json={"muc_gia_nguoi_tu": 90000}, headers=qt)
    assert r.status_code == 422 and r.json()["ma_loi"] == "KHOANG_GIA_KHONG_HOP_LE"
    r = client.patch(f"/admin/places/{ma}", json={"gio_mo_cua": [{"thu_trong_tuan": 1, "gio_mo": "18:00", "gio_dong": "08:00"}]}, headers=qt)
    assert r.status_code == 422
    assert client.get(f"/places/{ma}").status_code == 200
    assert any(x["ma_dia_diem"] == ma for x in client.get("/places", params={"ma_tinh": 21, "q": body["ten"]}).json()["items"])
    assert client.post(f"/admin/places/{ma}/an", json={"ly_do": "Đóng cửa sửa chữa"}, headers=qt).status_code == 200
    assert client.get(f"/places/{ma}").status_code == 404
    assert client.get("/places", params={"ma_tinh": 21, "q": body["ten"]}).json()["tong"] == 0
    assert client.get("/admin/places", params={"trang_thai": "an", "q": body["ten"]}, headers=qt).json()["tong"] == 1
