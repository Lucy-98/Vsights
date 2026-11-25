-- xoa_hoat_dong_mau.sql — DE, T-026 bản 1.1. Gỡ bộ hoạt động mẫu (Q-026 = A) trước khi chạy thật.
-- Chỉ chạy khi khoá hoat_dong_mau = 'true' (khi đó mọi dòng ở các bảng hoạt động là dữ liệu mẫu); nếu 'false' thì
-- dừng, vì các dòng đó có thể là hoạt động thật. Lượt chuyển OTA đã được "Chỗ ở của tôi" tham chiếu thì giữ lại.
BEGIN;
DO $$
BEGIN
  IF coalesce((SELECT gia_tri FROM cau_hinh_he_thong WHERE khoa = 'hoat_dong_mau'), 'false') <> 'true' THEN
    RAISE EXCEPTION 'hoat_dong_mau không phải true: các bảng hoạt động không được coi là dữ liệu mẫu, không xoá';
  END IF;
END $$;
DELETE FROM tin_nhan_chatbot;
DELETE FROM hoi_thoai;
DELETE FROM luot_tim_kiem;
DELETE FROM loi_dong_bo;
DELETE FROM lan_dong_bo;
DELETE FROM luot_chuyen_ota l WHERE NOT EXISTS (SELECT 1 FROM cho_o_cua_toi c WHERE c.ma_luot = l.ma_luot);
DELETE FROM lich_trinh l WHERE l.ten LIKE '[Mẫu] %'
  AND NOT EXISTS (SELECT 1 FROM ngay_lich_trinh x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM thanh_vien_lich_trinh x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM cho_o_cua_toi x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM lien_ket_chia_se x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM lich_trinh_so_thich x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM diem_rang_buoc x WHERE x.ma_lich_trinh = l.ma_lich_trinh)
  AND NOT EXISTS (SELECT 1 FROM hoi_thoai x WHERE x.ma_lich_trinh = l.ma_lich_trinh);
UPDATE cau_hinh_he_thong SET gia_tri = 'false' WHERE khoa = 'hoat_dong_mau';
COMMIT;
