"""Xác thực JWT + refresh cookie (base/02 mục 5, Cheat Sheet mục 8) và tự rà soát bảo mật BM-01…BM-08.

Mã BM-xx là bộ mã riêng của bản 0.6 (B-020), đối chiếu với L/E của base/02 mục 5.2 ở SA_T004 mục D.2:
BM-01 dò mật khẩu song song · BM-02 = L2 · BM-03 dò email qua đăng nhập · BM-04 = L3 · BM-05 = L4
BM-06 = L5 · BM-07 sửa claim vai trò · BM-08 token giả / hết hạn."""
import time
from concurrent.futures import ThreadPoolExecutor

import jwt as pyjwt

from tests.conftest import MAT_KHAU, ORIGIN, dang_nhap


def test_BM05_dang_nhap_tra_token_va_cookie_httponly(client):
    r = client.post("/auth/login", json={"email": "DuKhach@ViDu.vn", "mat_khau": MAT_KHAU, "thiet_bi": "pytest"},
                    headers=ORIGIN)
    assert r.status_code == 200
    b = r.json()
    assert b["token_type"] == "bearer" and b["expires_in"] == 900 and b["access_token"]
    sc = r.headers["set-cookie"]
    for co in ("vs_refresh=", "HttpOnly", "Secure", "SameSite=strict", "Path=/auth"):
        assert co.lower() in sc.lower(), sc
    assert r.headers["cache-control"] == "no-store"


def test_BM03_sai_mat_khau_va_email_khong_ton_tai_cung_mot_loi(client):
    a = client.post("/auth/login", json={"email": "dukhach@vidu.vn", "mat_khau": "sai-sai"}, headers=ORIGIN)
    b = client.post("/auth/login", json={"email": "khongco@vidu.vn", "mat_khau": "sai-sai"}, headers=ORIGIN)
    assert a.status_code == b.status_code == 401
    assert a.json()["ma_loi"] == b.json()["ma_loi"] == "SAI_THONG_TIN"
    assert a.json()["thong_bao"] == b.json()["thong_bao"]


def test_BM03_email_chua_xac_thuc_chi_bao_khi_dung_mat_khau(client):
    sai = client.post("/auth/login", json={"email": "chuaxacthuc@vidu.vn", "mat_khau": "x"}, headers=ORIGIN)
    assert sai.json()["ma_loi"] == "SAI_THONG_TIN"
    dung = client.post("/auth/login", json={"email": "chuaxacthuc@vidu.vn", "mat_khau": MAT_KHAU}, headers=ORIGIN)
    assert dung.status_code == 403 and dung.json()["ma_loi"] == "EMAIL_CHUA_XAC_THUC"


def test_tai_khoan_bi_khoa(client, sql):
    sql("INSERT INTO nguoi_dung (email, mat_khau_bam, ho_ten, email_da_xac_thuc, trang_thai) "
        "SELECT 'bikhoa@vidu.vn', mat_khau_bam, 'Bị khoá', TRUE, 'khoa' FROM nguoi_dung WHERE email='dukhach@vidu.vn' "
        "ON CONFLICT DO NOTHING")
    r = client.post("/auth/login", json={"email": "bikhoa@vidu.vn", "mat_khau": MAT_KHAU}, headers=ORIGIN)
    assert r.status_code == 403 and r.json()["ma_loi"] == "TAI_KHOAN_BI_KHOA"


def test_kiem_origin_o_ca_ba_endpoint_cookie(client):
    for path in ("/auth/login", "/auth/refresh", "/auth/logout"):
        for h in ({}, {"Origin": "https://ke-xau.example"}):
            r = client.post(path, json={"email": "dukhach@vidu.vn", "mat_khau": MAT_KHAU}, headers=h)
            assert r.status_code == 403 and r.json()["ma_loi"] == "NGUON_KHONG_HOP_LE", (path, h)


def test_du_lieu_vao_sai_tra_422_theo_truong(client):
    r = client.post("/auth/login", json={"email": "khong-phai-email", "mat_khau": ""}, headers=ORIGIN)
    assert r.status_code == 422 and r.json()["ma_loi"] == "DU_LIEU_KHONG_HOP_LE"
    assert {c["truong"] for c in r.json()["chi_tiet"]} == {"email", "mat_khau"}


def test_BM01_BM02_gioi_han_theo_cap_email_ip_va_retry_after(client, sql):
    email = "nguoidanhgia1@vidu.vn"
    sql("DELETE FROM dang_nhap_that_bai WHERE email_chuan = :e", e=email)
    ma = [client.post("/auth/login", json={"email": email, "mat_khau": "sai"}, headers=ORIGIN).status_code
          for _ in range(6)]
    assert ma[:5] == [401] * 5 and ma[5] == 429
    r = client.post("/auth/login", json={"email": email, "mat_khau": "sai"}, headers=ORIGIN)
    assert r.status_code == 429 and r.json()["ma_loi"] == "THU_QUA_NHIEU_LAN" and int(r.headers["retry-after"]) > 0
    # BM-02 (= L2 base/02): bị khoá theo CẶP (email, IP) — cùng email từ IP khác không bị khoá, nên kẻ xấu không khoá được người khác
    dem = sql("SELECT count(*) n FROM dang_nhap_that_bai WHERE email_chuan = :e", e=email)[0]["n"]
    assert dem == 1


def test_BM01_yeu_cau_song_song_khong_lot_qua_gioi_han(app, sql):
    """UPSERT nguyên tử: 12 lần sai song song thì không quá 5 lần được so mật khẩu (401)."""
    from fastapi.testclient import TestClient
    email = "nguoidanhgia2@vidu.vn"
    sql("DELETE FROM dang_nhap_that_bai WHERE email_chuan = :e", e=email)

    def thu(_):
        with TestClient(app, base_url="https://testserver") as c:
            return c.post("/auth/login", json={"email": email, "mat_khau": "sai"}, headers=ORIGIN).status_code
    with ThreadPoolExecutor(12) as ex:
        kq = list(ex.map(thu, range(12)))
    assert kq.count(401) <= 5 and kq.count(429) >= 7, kq


def test_me_tra_dung_hop_dong_va_vai_tro_tu_csdl(client, dk):
    r = client.get("/auth/me", headers=dk)
    assert r.status_code == 200
    assert set(r.json()) == {"ma_nguoi_dung", "email", "ho_ten", "vai_tro", "email_da_xac_thuc", "tao_luc"}
    assert r.json()["vai_tro"] == "du_khach"


def test_BM08_me_thieu_token_token_sai_token_het_han(client, dk):
    assert client.get("/auth/me").json()["ma_loi"] == "CHUA_DANG_NHAP"
    assert client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).json()["ma_loi"] == "TOKEN_KHONG_HOP_LE"
    from app.core.config import cai_dat
    cd = cai_dat()
    claims = pyjwt.decode(dk["Authorization"][7:], options={"verify_signature": False})
    claims["exp"] = int(time.time()) - 10
    het = pyjwt.encode(claims, cd.jwt_secret, algorithm="HS256")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {het}"})
    assert r.status_code == 401 and r.json()["ma_loi"] == "TOKEN_HET_HAN"
    # Ký bằng khoá khác → không hợp lệ
    gia = pyjwt.encode({**claims, "exp": int(time.time()) + 600}, "khoa-khac" * 5, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {gia}"}).json()["ma_loi"] == "TOKEN_KHONG_HOP_LE"


def test_BM04_refresh_xoay_vong_va_dung_lai_thu_hoi_ca_ho(client):
    dang_nhap(client)
    cu = client.cookies.get("vs_refresh")
    r1 = client.post("/auth/refresh", headers=ORIGIN)
    assert r1.status_code == 200 and r1.json()["access_token"]
    moi = client.cookies.get("vs_refresh")
    assert moi and moi != cu
    access_moi = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    assert client.get("/auth/me", headers=access_moi).status_code == 200
    # Kẻ trộm gửi lại token cũ đã xoay → 401 REFRESH_BI_DUNG_LAI, cả họ phiên bị thu hồi
    client.cookies.clear()
    r2 = client.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"vs_refresh={cu}"})
    assert r2.status_code == 401 and r2.json()["ma_loi"] == "REFRESH_BI_DUNG_LAI"
    assert "max-age=0" in r2.headers.get("set-cookie", "").lower()
    # Token mới của chủ thật cũng mất hiệu lực, access token đang dùng bị từ chối ngay
    r3 = client.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"vs_refresh={moi}"})
    assert r3.status_code == 401 and r3.json()["ma_loi"] == "REFRESH_KHONG_HOP_LE"
    assert client.get("/auth/me", headers=access_moi).json()["ma_loi"] == "PHIEN_DA_HUY"


def test_refresh_thieu_cookie_hoac_rac(client):
    assert client.post("/auth/refresh", headers=ORIGIN).json()["ma_loi"] == "REFRESH_KHONG_HOP_LE"
    r = client.post("/auth/refresh", headers={**ORIGIN, "Cookie": "vs_refresh=rac"})
    assert r.status_code == 401 and r.json()["ma_loi"] == "REFRESH_KHONG_HOP_LE"


def test_BM06_hai_refresh_cung_luc_cung_token_chi_mot_thanh_cong(app):
    """FOR UPDATE tuần tự hoá hai yêu cầu; yêu cầu thứ hai thấy token đã xoay. (Phía giao diện, Web Locks
    tránh trường hợp này bằng cách chỉ để một tab gọi refresh.)"""
    from fastapi.testclient import TestClient
    with TestClient(app, base_url="https://testserver") as c:
        dang_nhap(c)
        rt = c.cookies.get("vs_refresh")

    def goi(_):
        with TestClient(app, base_url="https://testserver") as c2:
            return c2.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"vs_refresh={rt}"}).status_code
    with ThreadPoolExecutor(2) as ex:
        kq = sorted(ex.map(goi, range(2)))
    assert kq == [200, 401]


def test_dang_xuat_huy_phien_ngay(client):
    h = dang_nhap(client)
    r = client.post("/auth/logout", headers=ORIGIN)
    assert r.status_code == 204 and "max-age=0" in r.headers["set-cookie"].lower()
    assert client.get("/auth/me", headers=h).json()["ma_loi"] == "PHIEN_DA_HUY"
    assert client.post("/auth/refresh", headers=ORIGIN).status_code == 401
    # Đăng xuất khi không có cookie vẫn 204
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204


def test_cors_cho_phep_localhost_5173_kem_credentials(client):
    r = client.options("/auth/login", headers={**ORIGIN, "Access-Control-Request-Method": "POST",
                                                "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"
    r2 = client.options("/auth/login", headers={"Origin": "https://ke-xau.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r2.headers


def test_cookie_xoa_theo_cau_hinh_secure(client, monkeypatch):
    """B-022: lệnh xoá cookie phải cùng cờ Secure với lúc đặt (VS_COOKIE_SECURE)."""
    from app.api import auth
    from app.core.config import cai_dat
    assert "Secure;" in auth.cookie_xoa()
    monkeypatch.setattr(cai_dat(), "cookie_secure", False)
    assert "secure" not in auth.cookie_xoa().lower() and "secure" not in auth._COOKIE_XOA.lower()
    r = client.post("/auth/refresh", headers={**ORIGIN, "Cookie": "vs_refresh=rac"})
    assert r.status_code == 401 and "max-age=0" in r.headers["set-cookie"].lower()
    assert "secure" not in r.headers["set-cookie"].lower()
