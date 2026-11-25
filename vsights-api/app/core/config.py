"""Cấu hình đọc từ biến môi trường (tiền tố VS_) hoặc tệp .env. Không có bí mật mặc định dùng cho production."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CaiDat(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VS_", env_file=".env", extra="ignore")

    # DSN kiểu SQLAlchemy + psycopg 3. Mật khẩu PostgreSQL: đặt trong DSN hoặc biến PGPASSWORD.
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/vsights"

    # Khoá ký JWT HS256. BẮT BUỘC đặt VS_JWT_SECRET (>= 32 ký tự) khi chạy thật.
    jwt_secret: str = ""
    jwt_issuer: str = "vsights-api"
    jwt_audience: str = "vsights-web"
    access_ttl_giay: int = 15 * 60
    refresh_ttl_ngay: int = 30

    # Nguồn được phép gọi /auth/login|refresh|logout và được CORS cho phép (có credentials)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Swagger ở chính API cũng gọi được /auth/*
    origin_them: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Cookie refresh: Secure vẫn dùng được trên http://localhost (trình duyệt coi localhost là ngữ cảnh an toàn)
    cookie_secure: bool = True

    # Giới hạn đăng nhập sai theo cặp (email, IP)
    so_lan_sai_toi_da: int = 5
    phut_khoa: int = 15

    @property
    def origin_hop_le(self) -> set[str]:
        return set(self.cors_origins) | set(self.origin_them)


@lru_cache
def cai_dat() -> CaiDat:
    cd = CaiDat()
    if len(cd.jwt_secret) < 32:
        raise RuntimeError("Thiếu VS_JWT_SECRET (tối thiểu 32 ký tự). Xem README, mục Cấu hình.")
    return cd
