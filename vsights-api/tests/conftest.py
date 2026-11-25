"""Kiểm thử tích hợp trên PostgreSQL THẬT (không mock CSDL).
Mỗi lần chạy pytest: tạo lại CSDL `vsights_test` từ db/01–03 rồi chạy toàn bộ ca.
Kết nối lấy từ biến PG* chuẩn (PGHOST, PGPORT, PGUSER, PGPASSWORD); mặc định localhost:5432, user postgres."""
import os
import secrets
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

# "Hôm nay" của ca kiểm thử phải trùng "hôm nay" giờ Việt Nam mà API dùng (kiem_dai_ngay). Máy chạy ở múi giờ
# khác (CI, máy ảo UTC) sẽ lệch một ngày trong khoảng 17:00–24:00 UTC nếu không đặt TZ (tests/test_gia ngay_re_hon).
os.environ["TZ"] = "Asia/Ho_Chi_Minh"
if hasattr(__import__("time"), "tzset"):
    __import__("time").tzset()

GOC = Path(__file__).resolve().parents[1]
DB = "vsights_test"
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGUSER", "postgres")
_pw = os.environ.get("PGPASSWORD")
os.environ["VS_DATABASE_URL"] = (
    f"postgresql+psycopg://{os.environ['PGUSER']}{':' + _pw if _pw else ''}@{os.environ['PGHOST']}:"
    f"{os.environ.get('PGPORT', '5432')}/{DB}")
os.environ["VS_JWT_SECRET"] = secrets.token_urlsafe(40)

ORIGIN = {"Origin": "http://localhost:5173"}
MAT_KHAU = "matkhau123"


def pytest_sessionstart(session):
    subprocess.run([str(GOC / "scripts" / "nap_csdl.sh"), DB], check=True, capture_output=True)


@pytest.fixture(scope="session")
def app():
    from app.main import app as a
    return a


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    # base_url https để TestClient gửi lại cookie Secure như trình duyệt
    with TestClient(app, base_url="https://testserver") as c:
        yield c


def dang_nhap(client, email="dukhach@vidu.vn", mat_khau=MAT_KHAU):
    r = client.post("/auth/login", json={"email": email, "mat_khau": mat_khau}, headers=ORIGIN)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def qt(client):
    return dang_nhap(client, "quantri@vidu.vn")


@pytest.fixture()
def dk(client):
    return dang_nhap(client, "dukhach@vidu.vn")


def ngay(sau: int) -> str:
    return (date.today() + timedelta(days=sau)).isoformat()


@pytest.fixture()
def sql():
    """Chạy SQL trực tiếp để chuẩn bị/kiểm tra dữ liệu."""
    from sqlalchemy import text
    from app.core.db import engine

    def chay(cau: str, **p):
        with engine().begin() as c:
            r = c.execute(text(cau), p)
            return r.mappings().all() if r.returns_rows else r.rowcount
    return chay
