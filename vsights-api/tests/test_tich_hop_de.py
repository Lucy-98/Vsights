"""Q-025 (DE, SA-020): phần lược đồ SA nhận cho pipeline đồng bộ và thống kê — vẫn 66 bảng."""
import psycopg
import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError


def test_moi_ota_chi_mot_lan_dong_bo_dang_chay(sql):
    ota = sql("SELECT ma_ota FROM nguon_ota WHERE ten_ota = 'Agoda'")[0]["ma_ota"]
    lan = sql("INSERT INTO lan_dong_bo (ma_ota) VALUES (:o) RETURNING ma_lan", o=ota)[0]["ma_lan"]
    try:
        with pytest.raises(IntegrityError) as e:
            sql("INSERT INTO lan_dong_bo (ma_ota) VALUES (:o)", o=ota)
        assert isinstance(e.value.orig, psycopg.errors.UniqueViolation)
        # Lần trước kết thúc thì chạy lần mới được; lần đã xong không giới hạn
        sql("UPDATE lan_dong_bo SET trang_thai = 'thanh_cong', ket_thuc = now(), "
            "chi_tiet = CAST(:c AS jsonb) WHERE ma_lan = :l", l=lan, c='{"them": 0, "sua": 12, "xoa": 1, "giu_nguyen": 90}')
        moi = sql("INSERT INTO lan_dong_bo (ma_ota) VALUES (:o) RETURNING ma_lan", o=ota)[0]["ma_lan"]
        sql("UPDATE lan_dong_bo SET trang_thai = 'that_bai' WHERE ma_lan = :l", l=moi)
    finally:
        sql("DELETE FROM lan_dong_bo WHERE ma_ota = :o", o=ota)


def test_chi_tiet_lan_dong_bo_phai_la_doi_tuong_json(sql):
    ota = sql("SELECT ma_ota FROM nguon_ota WHERE ten_ota = 'Traveloka'")[0]["ma_ota"]
    with pytest.raises(DBAPIError):
        sql("INSERT INTO lan_dong_bo (ma_ota, trang_thai, chi_tiet) VALUES (:o, 'that_bai', CAST('[1,2]' AS jsonb))", o=ota)


def test_chi_muc_thong_ke_va_thong_so_don_bang_gia(sql):
    ten = {r["indexname"] for r in sql("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")}
    assert {"uq_dong_bo_dang_chay", "ix_luot_tim_thoi_diem", "ix_luot_chuyen_thoi_diem", "ix_tin_nhan_thoi_diem"} <= ten
    opt = sql("SELECT reloptions FROM pg_class WHERE relname = 'gia_tham_khao'")[0]["reloptions"]
    assert "autovacuum_vacuum_scale_factor=0.05" in opt
