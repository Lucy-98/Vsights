-- VSIGHTS — DỮ LIỆU MẪU CHO TRÌNH DIỄN (chạy sau 02_danh_muc.sql)
-- Mọi chỗ ở, địa điểm đều có la_du_lieu_mau = TRUE. Tên là tên giả, không phải cơ sở thật.
-- Giá tham khảo sinh cho 120 đêm kể từ NGÀY NẠP (current_date) → nạp lại khi demo ở ngày khác.
-- Sinh bằng hàm băm (hashtext) nên chạy lại cho cùng kết quả với cùng ngày nạp.

-- Tài khoản trình diễn (mật khẩu chung: matkhau123 — chỉ dùng trên máy cá nhân)
INSERT INTO nguoi_dung (email, mat_khau_bam, ho_ten, vai_tro, email_da_xac_thuc) VALUES
 ('quantri@vidu.vn',  '$argon2id$v=19$m=65536,t=3,p=4$+wP27P8iqgtwjgx7UzBDQA$R8vZ+fiQUcQ7dWguECMm9Otp2Hclx6tAqz49i4BXFoc', 'Quản trị viên mẫu', 'quan_tri', TRUE),
 ('dukhach@vidu.vn',  '$argon2id$v=19$m=65536,t=3,p=4$+wP27P8iqgtwjgx7UzBDQA$R8vZ+fiQUcQ7dWguECMm9Otp2Hclx6tAqz49i4BXFoc', 'Du khách mẫu', 'du_khach', TRUE),
 ('chuaxacthuc@vidu.vn','$argon2id$v=19$m=65536,t=3,p=4$+wP27P8iqgtwjgx7UzBDQA$R8vZ+fiQUcQ7dWguECMm9Otp2Hclx6tAqz49i4BXFoc', 'Chưa xác thực', 'du_khach', FALSE);
INSERT INTO nguoi_dung (email, ho_ten, email_da_xac_thuc)
SELECT 'nguoidanhgia' || g || '@vidu.vn', 'Người đánh giá ' || g, TRUE FROM generate_series(1, 6) g;
-- Một tài khoản đăng nhập Zalo: không có email (D-030, D-031)
INSERT INTO nguoi_dung (email, ho_ten) VALUES (NULL, 'Du khách Zalo mẫu');
INSERT INTO tai_khoan_lien_ket (ma_nguoi_dung, nha_cung_cap, ma_ben_ngoai)
SELECT ma_nguoi_dung, 'zalo', 'zalo-mau-0001' FROM nguoi_dung WHERE ho_ten = 'Du khách Zalo mẫu';

-- ---------------- Chỗ ở: 12 cơ sở mỗi tỉnh × 34 tỉnh = 408 ----------------
INSERT INTO co_so_luu_tru (ma_tinh, ten, loai_hinh, dia_chi, khu_vuc, vi_do, kinh_do, hang_sao, mo_ta,
                           gio_nhan_phong, gio_tra_phong, chinh_sach_huy, la_du_lieu_mau)
SELECT t.ma_tinh,
       (ARRAY['Khách sạn','Homestay','Resort','Căn hộ','Nhà nghỉ'])[1 + (i - 1) % 5] || ' ' ||
       (ARRAY['Hoa Sen','Bình Minh','Sông Xanh','Mây Ngàn','Phố Cổ','Gió Biển','Đồi Thông','An Nhiên','Hải Âu','Lá Phong','Trăng Non','Ánh Dương'])[i]
         || ' ' || t.ten_tinh,
       (ARRAY['khach_san','homestay','resort','can_ho','nha_nghi'])[1 + (i - 1) % 5],
       (10 + i * 7) || ' đường mẫu số ' || i || ', ' || t.ten_tinh,
       (ARRAY['Trung tâm','Ven biển','Ngoại ô','Gần chợ'])[1 + i % 4],
       round(t.vi_do  + ((abs(hashtext(t.ma_tinh || 'la' || i)) % 1000) - 500) / 10000.0, 6),
       round(t.kinh_do + ((abs(hashtext(t.ma_tinh || 'lo' || i)) % 1000) - 500) / 10000.0, 6),
       CASE WHEN i % 5 = 2 OR i % 7 = 0 THEN NULL ELSE 2 + (i % 4) END,       -- một phần rỗng
       'Dữ liệu mẫu cho trình diễn.',
       '14:00', '12:00',
       CASE WHEN i % 3 = 0 THEN NULL ELSE 'Huỷ miễn phí theo điều kiện của từng loại phòng; xem chi tiết trên OTA.' END,
       TRUE
FROM tinh_thanh t CROSS JOIN generate_series(1, 12) i
ORDER BY t.ma_tinh, i;

-- Tiện nghi cơ sở (Wi-Fi cho tất cả, còn lại theo hàm băm)
INSERT INTO co_so_tien_nghi (ma_co_so, ma_tien_nghi)
SELECT c.ma_co_so, tn.ma_tien_nghi
FROM co_so_luu_tru c JOIN tien_nghi tn ON tn.pham_vi = 'co_so'
WHERE tn.ten_tien_nghi = 'Wi-Fi miễn phí' OR abs(hashtext(c.ma_co_so || 'tn' || tn.ma_tien_nghi)) % 100 < 40;

-- Sở thích phù hợp của cơ sở (bảng nối thay cho cột mảng phu_hop TEXT[])
INSERT INTO co_so_so_thich (ma_co_so, ma_so_thich)
SELECT c.ma_co_so, s.ma_so_thich
FROM co_so_luu_tru c JOIN so_thich s ON s.pham_vi IN ('chung','cho_o')
WHERE abs(hashtext(c.ma_co_so || 'st' || s.ma_so_thich)) % 100 < 30;

-- ---------------- Loại phòng: 2 mỗi cơ sở = 816 ----------------
INSERT INTO loai_phong (ma_co_so, ten_loai_phong, loai_giuong, suc_chua_nl, suc_chua_te, dien_tich,
                        co_bua_sang, dieu_kien_huy, thanh_toan_tai_cho, so_ngay_huy_mien_phi)
SELECT c.ma_co_so,
       CASE k WHEN 1 THEN 'Phòng Tiêu chuẩn' ELSE 'Phòng Gia đình' END,
       CASE k WHEN 1 THEN '1 giường đôi' ELSE '2 giường đôi' END,
       CASE k WHEN 1 THEN 2 ELSE 4 END,
       CASE k WHEN 1 THEN 1 ELSE 2 END,
       CASE WHEN c.ma_co_so % 4 = 0 THEN NULL ELSE (CASE k WHEN 1 THEN 22 ELSE 36 END) + c.ma_co_so % 9 END,
       (c.ma_co_so + k) % 2 = 0,
       CASE WHEN c.ma_co_so % 3 = 0 THEN NULL ELSE 'Huỷ trước hạn được hoàn tiền theo chính sách OTA.' END,
       CASE WHEN c.ma_co_so % 5 = 0 THEN NULL ELSE (c.ma_co_so + k) % 3 <> 0 END,
       CASE WHEN c.ma_co_so % 6 = 0 THEN NULL ELSE ((c.ma_co_so + k) % 4) END
FROM co_so_luu_tru c CROSS JOIN generate_series(1, 2) k
ORDER BY c.ma_co_so, k;

INSERT INTO loai_phong_tien_nghi (ma_loai_phong, ma_tien_nghi)
SELECT lp.ma_loai_phong, tn.ma_tien_nghi
FROM loai_phong lp JOIN tien_nghi tn ON tn.pham_vi = 'phong'
WHERE tn.ten_tien_nghi = 'Điều hoà' OR abs(hashtext(lp.ma_loai_phong || 'tp' || tn.ma_tien_nghi)) % 100 < 35;

-- ---------------- Liên kết OTA ----------------
-- Mọi cơ sở có Booking.com và Agoda; cơ sở chia hết cho 3 có thêm Traveloka.
-- Cơ sở chia hết cho 25: liên kết Traveloka ở trạng thái 'hong' (UC04-A1, chỉ báo cáo, không tự ẩn).
INSERT INTO lien_ket_ota (ma_co_so, ma_ota, url, ho_tro_tham_so, trang_thai)
SELECT c.ma_co_so, o.ma_ota,
       o.url_goc || '/vsights-mau/' || c.ma_co_so,
       o.ten_ota <> 'Traveloka',
       CASE WHEN o.ten_ota = 'Traveloka' AND c.ma_co_so % 25 = 0 THEN 'hong' ELSE 'hoat_dong' END
FROM co_so_luu_tru c JOIN nguon_ota o
  ON o.ten_ota IN ('Booking.com','Agoda') OR (o.ten_ota = 'Traveloka' AND c.ma_co_so % 3 = 0);

-- ---------------- Giá tham khảo: 120 đêm từ ngày nạp ----------------
-- Giá gốc theo loại hình và hạng; mỗi OTA lệch vài %; cuối tuần +15%.
-- Khoảng 3% đêm không có giá (để thấy "khả dụng" = có giá đủ mọi đêm, D-028b).
INSERT INTO gia_tham_khao (ma_loai_phong, ma_lien_ket, ngay, gia_dem, gom_thue_phi, ngay_cap_nhat)
SELECT lp.ma_loai_phong, lk.ma_lien_ket, d::date,
       (round(
          (CASE c.loai_hinh WHEN 'resort' THEN 2200000 WHEN 'khach_san' THEN 900000 WHEN 'can_ho' THEN 800000
                            WHEN 'homestay' THEN 450000 ELSE 300000 END)
          * (CASE lp.suc_chua_nl WHEN 2 THEN 1.0 ELSE 1.7 END)
          * (0.8 + (abs(hashtext('g' || lp.ma_loai_phong)) % 50) / 100.0)
          * (CASE o.ten_ota WHEN 'Booking.com' THEN 0.92 WHEN 'Agoda' THEN 1.04 ELSE 0.95 END)
          * (CASE WHEN extract(isodow FROM d) IN (5, 6) THEN 1.15 ELSE 1 END)
        / 1000) * 1000)::bigint,
       o.ten_ota = 'Agoda',                       -- Agoda: đã gồm thuế phí; hai OTA còn lại: chưa
       now() - ((abs(hashtext('u' || lk.ma_lien_ket)) % 72) || ' hours')::interval
FROM loai_phong lp
JOIN co_so_luu_tru c ON c.ma_co_so = lp.ma_co_so
JOIN lien_ket_ota lk ON lk.ma_co_so = c.ma_co_so
JOIN nguon_ota o ON o.ma_ota = lk.ma_ota
CROSS JOIN generate_series(current_date, current_date + 119, interval '1 day') d
WHERE abs(hashtext(lp.ma_loai_phong || '-' || lk.ma_lien_ket || '-' || d::date)) % 100 >= 3;

-- ---------------- Địa điểm, quán ăn: 16 mỗi tỉnh = 544 ----------------
INSERT INTO dia_diem (ma_tinh, ma_loai, ten, dia_chi, vi_do, kinh_do, mo_ta, thoi_luong_goi_y,
                      muc_gia_nguoi_tu, muc_gia_nguoi_den, la_du_lieu_mau)
SELECT t.ma_tinh, ld.ma_loai,
       CASE WHEN ld.nhom = 'tham_quan'
            THEN (ARRAY['Hồ','Đồi','Bảo tàng','Chùa','Rừng','Chợ đêm','Công viên','Thác','Làng nghề','Phố đi bộ'])[i]
                 || ' ' || (ARRAY['Ngọc','Vân','Phúc','Lâm','Kim','An','Hoà','Thanh','Đông','Bắc'])[i] || ' ' || t.ten_tinh
            ELSE (ARRAY['Quán','Nhà hàng','Cà phê','Quán','Bếp','Tiệm'])[i - 10] || ' ' ||
                 (ARRAY['Bà Tư','Phố Núi','Gió','Ốc Cô Ba','Nhà Mộc','Chè Xưa'])[i - 10] || ' ' || t.ten_tinh
       END,
       (5 + i * 3) || ' phố mẫu, ' || t.ten_tinh,
       round(t.vi_do  + ((abs(hashtext(t.ma_tinh || 'dla' || i)) % 1200) - 600) / 10000.0, 6),
       round(t.kinh_do + ((abs(hashtext(t.ma_tinh || 'dlo' || i)) % 1200) - 600) / 10000.0, 6),
       'Dữ liệu mẫu cho trình diễn.',
       CASE WHEN ld.nhom = 'tham_quan' THEN 60 + (i % 3) * 30 ELSE 60 END,
       CASE WHEN ld.nhom = 'an_uong' THEN 40000 + (i % 4) * 30000
            WHEN i % 3 = 0 THEN 0 ELSE 20000 + (i % 5) * 20000 END,
       CASE WHEN ld.nhom = 'an_uong' THEN 120000 + (i % 4) * 60000
            WHEN i % 3 = 0 THEN 0 ELSE 50000 + (i % 5) * 30000 END,
       TRUE
FROM tinh_thanh t CROSS JOIN generate_series(1, 16) i
JOIN loai_dia_diem ld ON ld.ten_loai = (ARRAY['Thắng cảnh','Thắng cảnh','Di tích, bảo tàng','Đền, chùa','Thắng cảnh',
                                              'Chợ, phố đi bộ','Công viên, khu vui chơi','Thắng cảnh','Di tích, bảo tàng','Chợ, phố đi bộ',
                                              'Quán ăn','Nhà hàng','Quán cà phê','Ăn vặt, đường phố','Quán ăn','Ăn vặt, đường phố'])[i]
ORDER BY t.ma_tinh, i;

INSERT INTO dia_diem_so_thich (ma_dia_diem, ma_so_thich)
SELECT d.ma_dia_diem, s.ma_so_thich
FROM dia_diem d JOIN so_thich s ON s.pham_vi IN ('chung','dia_diem')
WHERE abs(hashtext(d.ma_dia_diem || 'ds' || s.ma_so_thich)) % 100 < 25;

-- Giờ mở cửa: cả tuần, một ca; quán ăn mở muộn hơn
INSERT INTO gio_mo_cua (ma_dia_diem, thu_trong_tuan, ca, gio_mo, gio_dong)
SELECT d.ma_dia_diem, th, 1,
       CASE WHEN ld.nhom = 'an_uong' THEN time '09:00' ELSE time '07:30' END,
       CASE WHEN ld.nhom = 'an_uong' THEN time '22:00' ELSE time '17:30' END
FROM dia_diem d JOIN loai_dia_diem ld USING (ma_loai) CROSS JOIN generate_series(1, 7) th;

-- Giá vé cho điểm tham quan có thu phí
INSERT INTO gia_ve (ma_dia_diem, loai_khach, dieu_kien, gia)
SELECT d.ma_dia_diem, lk.loai, lk.dk, CASE lk.loai WHEN 'Người lớn' THEN d.muc_gia_nguoi_den ELSE d.muc_gia_nguoi_tu END
FROM dia_diem d JOIN loai_dia_diem ld USING (ma_loai)
CROSS JOIN (VALUES ('Người lớn', NULL), ('Trẻ em', 'Cao dưới 1,4 m')) AS lk(loai, dk)
WHERE ld.nhom = 'tham_quan' AND d.muc_gia_nguoi_den > 0;

-- ---------------- Đánh giá mẫu → điểm trung bình (cột dẫn xuất) ----------------
INSERT INTO danh_gia (ma_nguoi_dung, ma_co_so, so_sao, nhan_xet)
SELECT u.ma_nguoi_dung, c.ma_co_so, 3 + abs(hashtext(c.ma_co_so || 'sao' || u.ma_nguoi_dung)) % 3, 'Đánh giá mẫu.'
FROM co_so_luu_tru c JOIN nguoi_dung u ON u.email LIKE 'nguoidanhgia%'
WHERE abs(hashtext(c.ma_co_so || 'dg' || u.ma_nguoi_dung)) % 100 < 45;

INSERT INTO danh_gia (ma_nguoi_dung, ma_dia_diem, so_sao, nhan_xet)
SELECT u.ma_nguoi_dung, d.ma_dia_diem, 3 + abs(hashtext(d.ma_dia_diem || 'sao' || u.ma_nguoi_dung)) % 3, 'Đánh giá mẫu.'
FROM dia_diem d JOIN nguoi_dung u ON u.email LIKE 'nguoidanhgia%'
WHERE abs(hashtext(d.ma_dia_diem || 'dg' || u.ma_nguoi_dung)) % 100 < 45;

UPDATE co_so_luu_tru c SET diem_tb = x.tb, so_luot_danh_gia = x.n
FROM (SELECT ma_co_so, round(avg(so_sao), 1) tb, count(*) n FROM danh_gia
      WHERE ma_co_so IS NOT NULL AND trang_thai = 'hien' GROUP BY ma_co_so) x
WHERE x.ma_co_so = c.ma_co_so;

UPDATE dia_diem d SET diem_tb = x.tb, so_luot_danh_gia = x.n
FROM (SELECT ma_dia_diem, round(avg(so_sao), 1) tb, count(*) n FROM danh_gia
      WHERE ma_dia_diem IS NOT NULL AND trang_thai = 'hien' GROUP BY ma_dia_diem) x
WHERE x.ma_dia_diem = d.ma_dia_diem;

ANALYZE;
