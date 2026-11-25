"""Điểm vào ứng dụng: `uvicorn app.main:app --reload` → http://localhost:8000/docs"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cong_khai, quan_tri
from app.core.config import cai_dat
from app.core.errors import gan_xu_ly_loi

PHIEN_BAN = "0.6.4"


def tao_app() -> FastAPI:
    cd = cai_dat()
    app = FastAPI(title="Vsights API", version=PHIEN_BAN,
                  description="Backend Vsights — bản viết lại cho giữa kỳ (T-006). Giá luôn là giá tham khảo; "
                              "Vsights chỉ điều hướng sang OTA, không nhận đặt chỗ.")
    # allow_credentials để trình duyệt gửi/nhận cookie vs_refresh từ localhost:5173
    app.add_middleware(CORSMiddleware, allow_origins=cd.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"],
                       expose_headers=["Retry-After"])
    gan_xu_ly_loi(app)
    app.include_router(auth.router)
    app.include_router(cong_khai.router)
    app.include_router(quan_tri.router)

    @app.get("/health", tags=["Hệ thống"])
    def health():
        return {"trang_thai": "ok", "phien_ban": PHIEN_BAN}

    return app


app = tao_app()
