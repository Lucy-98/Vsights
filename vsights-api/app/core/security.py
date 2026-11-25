"""Băm mật khẩu (Argon2id), JWT HS256, refresh token ngẫu nhiên (chỉ lưu SHA-256)."""
import hashlib
import secrets
import time
import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import cai_dat
from app.core.errors import AppError

_ph = PasswordHasher()
# Hash giả để thời gian trả lời như nhau khi email không tồn tại (chống dò email qua thời gian)
_HASH_GIA = _ph.hash("khong-phai-mat-khau-that")


def bam_mat_khau(mat_khau: str) -> str:
    return _ph.hash(mat_khau)


def kiem_mat_khau(hash_luu: str | None, mat_khau: str) -> bool:
    try:
        return _ph.verify(hash_luu or _HASH_GIA, mat_khau) and hash_luu is not None
    except (VerificationError, InvalidHashError):
        return False


def tao_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def bam_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def tao_access_token(ma_nguoi_dung: int, ma_ho_phien: uuid.UUID) -> str:
    cd = cai_dat()
    now = int(time.time())
    return jwt.encode(
        {"sub": str(ma_nguoi_dung), "sid": str(ma_ho_phien), "iss": cd.jwt_issuer, "aud": cd.jwt_audience,
         "iat": now, "exp": now + cd.access_ttl_giay, "jti": secrets.token_hex(8)},
        cd.jwt_secret, algorithm="HS256",
    )


def giai_access_token(token: str) -> dict:
    cd = cai_dat()
    try:
        return jwt.decode(token, cd.jwt_secret, algorithms=["HS256"], audience=cd.jwt_audience,
                          issuer=cd.jwt_issuer, options={"require": ["sub", "sid", "exp", "iss", "aud"]})
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_HET_HAN", "Phiên đã hết hạn, vui lòng làm mới.", headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        raise AppError(401, "TOKEN_KHONG_HOP_LE", "Token không hợp lệ.", headers={"WWW-Authenticate": "Bearer"})
