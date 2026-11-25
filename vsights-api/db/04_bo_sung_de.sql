-- 04_bo_sung_de.sql — DE, T-026 bản 1.1 (Q-024 = B, D-039b, D-041, Q-026 = A)
-- Nạp sau 01, 02, 03 (scripts/nap_csdl.sh). Chạy lại nhiều lần an toàn: INSERT có điều kiện NOT EXISTS / ON CONFLICT,
-- UPDATE cho cùng kết quả. Không tạo bảng, không đổi mã, không xoá dòng thực thể (chỉ gỡ dòng liên kết ở mục B).

BEGIN;

-- ===================================================================================================
-- A. Danh sách tỉnh ven biển (D-041, 21 tỉnh) và tâm phụ phía biển
-- ===================================================================================================
CREATE TEMP TABLE de_ven_bien (ten_tinh VARCHAR(60) PRIMARY KEY) ON COMMIT DROP;
INSERT INTO de_ven_bien VALUES
 ('Quảng Ninh'),('Hải Phòng'),('Hưng Yên'),('Ninh Bình'),('Thanh Hóa'),('Nghệ An'),('Hà Tĩnh'),('Quảng Trị'),
 ('Huế'),('Đà Nẵng'),('Quảng Ngãi'),('Gia Lai'),('Đắk Lắk'),('Khánh Hòa'),('Lâm Đồng'),('TP. Hồ Chí Minh'),
 ('Đồng Tháp'),('Vĩnh Long'),('Cần Thơ'),('Cà Mau'),('An Giang');

-- Tỉnh có tâm mẫu cách biển > 40 km (ước lượng đường chim bay tới điểm ven biển gần nhất): đặt bãi biển và cơ sở
-- "Ven biển" quanh tâm phụ. Ngoại lệ có chủ đích của D-026 (PO, D-041). Toạ độ làm tròn, chỉ là điểm mẫu.
CREATE TEMP TABLE de_tam_phu (ten_tinh VARCHAR(60) PRIMARY KEY, ten_tam VARCHAR(60) NOT NULL,
                              vi_do NUMERIC(9,6) NOT NULL, kinh_do NUMERIC(9,6) NOT NULL) ON COMMIT DROP;
INSERT INTO de_tam_phu VALUES
 ('Hưng Yên',        'Ven biển Thái Thụy',  20.450000, 106.500000),
 ('Gia Lai',         'Quy Nhơn',            13.780000, 109.220000),
 ('Đắk Lắk',         'Tuy Hòa',             13.080000, 109.300000),
 ('Lâm Đồng',        'Phan Thiết',          10.930000, 108.100000),
 ('TP. Hồ Chí Minh', 'Vũng Tàu',            10.350000, 107.080000),
 ('Cần Thơ',         'Trần Đề',              9.600000, 106.100000),
 ('Vĩnh Long',       'Duyên Hải',            9.750000, 106.450000),
 ('Đồng Tháp',       'Gò Công Đông',        10.350000, 106.750000),
 ('An Giang',        'Rạch Giá',            10.010000, 105.090000);

DO $$
BEGIN
  IF (SELECT count(*) FROM de_ven_bien v JOIN tinh_thanh t USING (ten_tinh)) <> 21 THEN
    RAISE EXCEPTION 'Danh sách ven biển (D-041) không khớp đủ 21 tỉnh trong tinh_thanh';
  END IF;
  IF (SELECT count(*) FROM de_tam_phu p JOIN de_ven_bien v USING (ten_tinh)) <> 9 THEN
    RAISE EXCEPTION 'Tâm phụ phải thuộc tỉnh ven biển';
  END IF;
END $$;

INSERT INTO cau_hinh_he_thong (khoa, gia_tri, mo_ta)
SELECT 'tinh_ven_bien', string_agg(t.ma_tinh::text, ',' ORDER BY t.ma_tinh),
       'D-041: mã 21 tỉnh, thành ven biển (nhãn "Ven biển", sở thích "Biển", bãi biển chỉ ở các tỉnh này)'
FROM tinh_thanh t JOIN de_ven_bien v USING (ten_tinh)
ON CONFLICT (khoa) DO UPDATE SET gia_tri = EXCLUDED.gia_tri, mo_ta = EXCLUDED.mo_ta;

INSERT INTO cau_hinh_he_thong (khoa, gia_tri, mo_ta)
SELECT 'tam_phu_' || t.ma_tinh, p.vi_do || ',' || p.kinh_do,
       'D-041: tâm phụ phía biển của ' || t.ten_tinh || ' (' || p.ten_tam || '), dạng vi_do,kinh_do'
FROM tinh_thanh t JOIN de_tam_phu p USING (ten_tinh)
ON CONFLICT (khoa) DO UPDATE SET gia_tri = EXCLUDED.gia_tri, mo_ta = EXCLUDED.mo_ta;

-- Q-026 = A: bật thành 'true' khi nạp dữ liệu hoạt động mẫu (scripts/sinh_hoat_dong_mau.sql), về 'false' khi xoá.
INSERT INTO cau_hinh_he_thong (khoa, gia_tri, mo_ta)
VALUES ('hoat_dong_mau', 'false',
        'Q-026: true = số liệu hoạt động (tìm kiếm, chuyển OTA, chatbot) là dữ liệu mẫu; A01 hiện dòng ghi rõ')
ON CONFLICT (khoa) DO NOTHING;

-- ===================================================================================================
-- B. Q-024 = B: sửa nhãn, tên, sở thích, tiện nghi "biển" sai ở 13 tỉnh nội địa (D-041)
--    Chỉ UPDATE cột khu_vuc, ten của cơ sở SA; gỡ dòng liên kết sở thích "Biển" (1) và tiện nghi "View biển" (13).
-- ===================================================================================================
UPDATE co_so_luu_tru c
SET khu_vuc = 'Trung tâm'
FROM tinh_thanh t
WHERE t.ma_tinh = c.ma_tinh AND t.ten_tinh NOT IN (SELECT ten_tinh FROM de_ven_bien) AND c.khu_vuc = 'Ven biển';

UPDATE co_so_luu_tru c
SET ten = replace(replace(c.ten, 'Gió Biển', 'Gió Đồng mẫu'), 'Hải Âu', 'Chim Én mẫu')
FROM tinh_thanh t
WHERE t.ma_tinh = c.ma_tinh AND t.ten_tinh NOT IN (SELECT ten_tinh FROM de_ven_bien)
  AND (c.ten LIKE '%Gió Biển%' OR c.ten LIKE '%Hải Âu%');

DELETE FROM co_so_so_thich x USING co_so_luu_tru c, tinh_thanh t
WHERE x.ma_so_thich = (SELECT ma_so_thich FROM so_thich WHERE ten = 'Biển')
  AND c.ma_co_so = x.ma_co_so AND t.ma_tinh = c.ma_tinh AND t.ten_tinh NOT IN (SELECT ten_tinh FROM de_ven_bien);

DELETE FROM dia_diem_so_thich x USING dia_diem d, tinh_thanh t
WHERE x.ma_so_thich = (SELECT ma_so_thich FROM so_thich WHERE ten = 'Biển')
  AND d.ma_dia_diem = x.ma_dia_diem AND t.ma_tinh = d.ma_tinh AND t.ten_tinh NOT IN (SELECT ten_tinh FROM de_ven_bien);

DELETE FROM loai_phong_tien_nghi x USING loai_phong lp, co_so_luu_tru c, tinh_thanh t
WHERE x.ma_tien_nghi = (SELECT ma_tien_nghi FROM tien_nghi WHERE ten_tien_nghi = 'View biển' AND pham_vi = 'phong')
  AND lp.ma_loai_phong = x.ma_loai_phong AND c.ma_co_so = lp.ma_co_so AND t.ma_tinh = c.ma_tinh
  AND t.ten_tinh NOT IN (SELECT ten_tinh FROM de_ven_bien);

-- ===================================================================================================
-- C. Bãi biển mẫu: 2 bãi cho mỗi tỉnh ven biển (D-039b); tỉnh có tâm phụ thì quanh tâm phụ (D-041)
-- ===================================================================================================
INSERT INTO dia_diem (ma_tinh, ma_loai, ten, dia_chi, vi_do, kinh_do, mo_ta, luu_y, thoi_diem_dep, thoi_luong_goi_y,
                      muc_gia_nguoi_tu, muc_gia_nguoi_den, la_du_lieu_mau)
SELECT t.ma_tinh,
       (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển'),
       'Bãi biển mẫu số ' || b.so || ' ' || t.ten_tinh,
       'Bờ biển mẫu số ' || b.so || ', ' || t.ten_tinh,
       round(coalesce(p.vi_do,  t.vi_do)  + ((abs(hashtext(t.ma_tinh || 'bla' || b.so)) % 1000) - 500) / 10000.0, 6),
       round(coalesce(p.kinh_do, t.kinh_do) + ((abs(hashtext(t.ma_tinh || 'blo' || b.so)) % 1000) - 500) / 10000.0, 6),
       'Bãi biển mẫu cho trình diễn, không phải địa điểm thật.',
       'Dữ liệu mẫu. Kiểm tra thời tiết và cờ cảnh báo trước khi tắm.',
       'Sáng sớm hoặc chiều muộn',
       120, 0, 0, TRUE
FROM tinh_thanh t
JOIN de_ven_bien v USING (ten_tinh)
LEFT JOIN de_tam_phu p USING (ten_tinh)
CROSS JOIN (VALUES (1), (2)) b(so)
WHERE NOT EXISTS (SELECT 1 FROM dia_diem d WHERE d.ma_tinh = t.ma_tinh
                  AND d.ten = 'Bãi biển mẫu số ' || b.so || ' ' || t.ten_tinh);

-- ===================================================================================================
-- D. Địa điểm tham quan thêm: 3 điểm mẫu mỗi tỉnh (đủ ≥ 12 điểm tham quan/tỉnh); điểm thứ 3 cách tâm 15–35 km
-- ===================================================================================================
INSERT INTO dia_diem (ma_tinh, ma_loai, ten, dia_chi, vi_do, kinh_do, mo_ta, thoi_luong_goi_y,
                      muc_gia_nguoi_tu, muc_gia_nguoi_den, la_du_lieu_mau)
SELECT t.ma_tinh,
       (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = (ARRAY['Công viên, khu vui chơi','Di tích, bảo tàng','Thắng cảnh'])[x.n]),
       (ARRAY['Vườn hoa mẫu','Phố cổ mẫu','Khu sinh thái mẫu'])[x.n] || ' ' || t.ten_tinh,
       (ARRAY['Khu vườn mẫu, ','Phố mẫu số 1, ','Xã mẫu ngoại thành, '])[x.n] || t.ten_tinh,
       round(t.vi_do  + CASE WHEN x.n < 3 THEN ((abs(hashtext(t.ma_tinh || 'nla' || x.n)) % 1200) - 600) / 10000.0
                             ELSE (CASE WHEN abs(hashtext(t.ma_tinh || 'nsa')) % 2 = 0 THEN 1 ELSE -1 END)
                                  * (0.15 + (abs(hashtext(t.ma_tinh || 'nta')) % 100) / 1000.0) END, 6),
       round(t.kinh_do + CASE WHEN x.n < 3 THEN ((abs(hashtext(t.ma_tinh || 'nlo' || x.n)) % 1200) - 600) / 10000.0
                              ELSE (CASE WHEN abs(hashtext(t.ma_tinh || 'nso')) % 2 = 0 THEN 1 ELSE -1 END)
                                   * (0.08 + (abs(hashtext(t.ma_tinh || 'nto')) % 80) / 1000.0) END, 6),
       'Dữ liệu mẫu cho trình diễn.',
       (ARRAY[60, 90, 180])[x.n],
       (ARRAY[0, 30000, 0])[x.n],
       (ARRAY[0, 60000, 0])[x.n],
       TRUE
FROM tinh_thanh t CROSS JOIN (VALUES (1), (2), (3)) x(n)
WHERE NOT EXISTS (SELECT 1 FROM dia_diem d WHERE d.ma_tinh = t.ma_tinh
                  AND d.ten = (ARRAY['Vườn hoa mẫu','Phố cổ mẫu','Khu sinh thái mẫu'])[x.n] || ' ' || t.ten_tinh);

-- Điểm mới: sở thích, giờ mở cửa, giá vé. Sở thích "Biển" chỉ gắn cho bãi biển.
INSERT INTO dia_diem_so_thich (ma_dia_diem, ma_so_thich)
SELECT d.ma_dia_diem, (SELECT ma_so_thich FROM so_thich WHERE ten = 'Biển')
FROM dia_diem d WHERE d.ma_loai = (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển')
ON CONFLICT DO NOTHING;

INSERT INTO dia_diem_so_thich (ma_dia_diem, ma_so_thich)
SELECT d.ma_dia_diem, (SELECT ma_so_thich FROM so_thich WHERE ten = 'Thiên nhiên')
FROM dia_diem d WHERE d.ma_loai = (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển')
ON CONFLICT DO NOTHING;

INSERT INTO dia_diem_so_thich (ma_dia_diem, ma_so_thich)
SELECT d.ma_dia_diem, s.ma_so_thich
FROM dia_diem d JOIN so_thich s ON s.pham_vi IN ('chung', 'dia_diem') AND s.ten <> 'Biển'
WHERE d.ten ~ '^(Vườn hoa mẫu|Phố cổ mẫu|Khu sinh thái mẫu) '
  AND abs(hashtext(d.ma_dia_diem || 'ns' || s.ma_so_thich)) % 100 < 25
ON CONFLICT DO NOTHING;

INSERT INTO gio_mo_cua (ma_dia_diem, thu_trong_tuan, ca, gio_mo, gio_dong)
SELECT d.ma_dia_diem, th,  1,
       CASE WHEN d.ma_loai = (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển') THEN time '05:00' ELSE time '07:30' END,
       CASE WHEN d.ma_loai = (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển') THEN time '20:00' ELSE time '17:30' END
FROM dia_diem d CROSS JOIN generate_series(1, 7) th
WHERE d.ten ~ '^(Bãi biển mẫu số|Vườn hoa mẫu|Phố cổ mẫu|Khu sinh thái mẫu) '
ON CONFLICT DO NOTHING;

INSERT INTO gia_ve (ma_dia_diem, loai_khach, dieu_kien, gia)
SELECT d.ma_dia_diem, lk.loai, lk.dk, CASE lk.loai WHEN 'Người lớn' THEN d.muc_gia_nguoi_den ELSE d.muc_gia_nguoi_tu END
FROM dia_diem d CROSS JOIN (VALUES ('Người lớn', NULL), ('Trẻ em', 'Cao dưới 1,4 m')) AS lk(loai, dk)
WHERE d.ten ~ '^Phố cổ mẫu ' AND d.muc_gia_nguoi_den > 0
  AND NOT EXISTS (SELECT 1 FROM gia_ve g WHERE g.ma_dia_diem = d.ma_dia_diem AND g.loai_khach = lk.loai);

-- ===================================================================================================
-- E. KHỐI CHỜ SA DUYỆT (Q-029): đưa cơ sở "Ven biển" của tỉnh có tâm xa biển về tâm phụ (D-041)
--    Đây là UPDATE toạ độ, rộng hơn điều kiện SA đã đồng ý ở Q-024 (chỉ nhãn, tên). Nếu SA không đồng ý:
--    xoá riêng mục E; các mục A–D không phụ thuộc. Cùng kết quả mỗi lần chạy (hàm của mã cơ sở).
-- ===================================================================================================
UPDATE co_so_luu_tru c
SET vi_do   = round(p.vi_do   + ((abs(hashtext(c.ma_co_so || 'pla')) % 1000) - 500) / 10000.0, 6),
    kinh_do = round(p.kinh_do + ((abs(hashtext(c.ma_co_so || 'plo')) % 1000) - 500) / 10000.0, 6)
FROM tinh_thanh t JOIN de_tam_phu p USING (ten_tinh)
WHERE t.ma_tinh = c.ma_tinh AND c.khu_vuc = 'Ven biển' AND c.la_du_lieu_mau;

ANALYZE dia_diem;
ANALYZE co_so_luu_tru;

COMMIT;
