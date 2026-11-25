-- VSIGHTS — DANH MỤC (chạy sau 01_schema.sql)
-- 34 tỉnh, thành theo Nghị quyết 202/2025/QH15. Toạ độ là tâm hành chính ước tính.

INSERT INTO vung_mien (ten_vung) VALUES ('Miền Bắc'), ('Miền Trung'), ('Miền Nam');

INSERT INTO tinh_thanh (ma_vung, ten_tinh, vi_do, kinh_do) VALUES
 (1,'Hà Nội',21.028500,105.854200), (1,'Hải Phòng',20.844900,106.688100), (1,'Quảng Ninh',21.006400,107.292500),
 (1,'Lào Cai',22.485600,103.970700), (1,'Lai Châu',22.396400,103.458200), (1,'Điện Biên',21.386000,103.023000),
 (1,'Sơn La',21.327000,103.914000), (1,'Lạng Sơn',21.853700,106.761500), (1,'Cao Bằng',22.665700,106.257800),
 (1,'Tuyên Quang',21.823600,105.214400), (1,'Thái Nguyên',21.594200,105.848200), (1,'Phú Thọ',21.322700,105.401900),
 (1,'Bắc Ninh',21.186100,106.076300), (1,'Hưng Yên',20.646400,106.051100), (1,'Ninh Bình',20.250600,105.974400),
 (2,'Thanh Hóa',19.807700,105.776500), (2,'Nghệ An',18.679700,105.681300), (2,'Hà Tĩnh',18.342800,105.905700),
 (2,'Quảng Trị',16.816300,107.100300), (2,'Huế',16.463700,107.590900), (2,'Đà Nẵng',16.054400,108.202200),
 (2,'Quảng Ngãi',15.120500,108.799800), (2,'Gia Lai',13.983300,108.000000), (2,'Khánh Hòa',12.238800,109.196700),
 (2,'Đắk Lắk',12.666700,108.050000), (2,'Lâm Đồng',11.940400,108.458300),
 (3,'TP. Hồ Chí Minh',10.776900,106.700900), (3,'Đồng Nai',10.957400,106.842700), (3,'Tây Ninh',11.310000,106.098300),
 (3,'Cần Thơ',10.045200,105.746900), (3,'Vĩnh Long',10.253700,105.972200), (3,'Đồng Tháp',10.455600,105.633300),
 (3,'An Giang',10.386000,105.435200), (3,'Cà Mau',9.176900,105.150100);

INSERT INTO so_thich (ten, pham_vi) VALUES
 ('Biển','chung'), ('Núi, trekking','chung'), ('Ẩm thực','chung'), ('Văn hoá, lịch sử','chung'),
 ('Thiên nhiên','chung'), ('Chụp ảnh','chung'), ('Yên tĩnh, nghỉ dưỡng','cho_o'), ('Gia đình có trẻ nhỏ','chung'),
 ('Mua sắm','dia_diem'), ('Cuộc sống về đêm','dia_diem');

INSERT INTO tien_nghi (ten_tien_nghi, pham_vi) VALUES
 ('Wi-Fi miễn phí','co_so'), ('Hồ bơi','co_so'), ('Chỗ đỗ ô tô','co_so'), ('Lễ tân 24 giờ','co_so'),
 ('Đưa đón sân bay','co_so'), ('Nhà hàng','co_so'), ('Cho mang thú cưng','co_so'), ('Phòng gym','co_so'),
 ('Điều hoà','phong'), ('Ban công','phong'), ('Bồn tắm','phong'), ('Bếp riêng','phong'),
 ('View biển','phong'), ('Máy giặt','phong');

INSERT INTO loai_dia_diem (ten_loai, nhom) VALUES
 ('Thắng cảnh','tham_quan'), ('Di tích, bảo tàng','tham_quan'), ('Đền, chùa','tham_quan'), ('Bãi biển','tham_quan'),
 ('Chợ, phố đi bộ','tham_quan'), ('Công viên, khu vui chơi','tham_quan'),
 ('Quán ăn','an_uong'), ('Nhà hàng','an_uong'), ('Quán cà phê','an_uong'), ('Ăn vặt, đường phố','an_uong');

INSERT INTO loai_mon (ten) VALUES ('Món chính'), ('Món nước'), ('Ăn vặt'), ('Đồ uống'), ('Tráng miệng');

INSERT INTO tieu_chi_danh_gia (ten, ap_dung) VALUES
 ('Sạch sẽ','cho_o'), ('Vị trí','cho_o'), ('Phục vụ','cho_o'), ('Đúng mô tả','cho_o'),
 ('Đáng tiền','dia_diem'), ('Phục vụ','dia_diem');

-- D-021: Booking.com niêm yết chưa gồm thuế phí và có tỷ lệ quy đổi; Traveloka chưa gồm
-- thuế phí và CHƯA có tỷ lệ → không đưa vào phép so, hiện riêng "chưa gồm thuế, phí".
INSERT INTO nguon_ota (ten_ota, url_goc, kieu_ket_noi, ty_le_thue_phi) VALUES
 ('Booking.com','https://www.booking.com','tep',15.00),
 ('Agoda','https://www.agoda.com','tep',NULL),
 ('Traveloka','https://www.traveloka.com','tep',NULL);

-- D-023: ngưỡng gợi ý lưu ở cấu hình, không thêm cột
INSERT INTO cau_hinh_he_thong (khoa, gia_tri, mo_ta) VALUES
 ('ban_kinh_goi_y_km','40','Bán kính gợi ý địa điểm quanh chỗ ở (D-023)'),
 ('canh_bao_chang_phut','90','Cảnh báo khi một chặng di chuyển vượt số phút này (D-023)'),
 ('so_dem_toi_da','30','Số đêm tối đa của một lần ở'),
 ('so_ngay_lich_trinh_toi_da','14','Số ngày tối đa của một lịch trình');

-- Chatbot (D-037, AI_KIEN_TRUC_CHATBOT_P2 mục 6.3, SA-017). Tên mô hình KHÔNG ở đây mà ở biến môi trường
-- (đổi mô hình phải chạy lại bộ đánh giá, không phải công tắc của quản trị viên).
INSERT INTO cau_hinh_he_thong (khoa, gia_tri, mo_ta) VALUES
 ('chatbot_nguon','mo_hinh','Nguồn trả lời: mo_hinh | quy_tac (công tắc UC18)'),
 ('chatbot_tin_moi_gio_khach','10','Số tin tối đa mỗi giờ của khách vãng lai'),
 ('chatbot_tin_moi_gio_du_khach','30','Số tin tối đa mỗi giờ của du khách'),
 ('chatbot_tin_moi_hoi_thoai_khach','20','Số tin tối đa mỗi hội thoại của khách vãng lai'),
 ('chatbot_tin_moi_hoi_thoai_du_khach','60','Số tin tối đa mỗi hội thoại của du khách'),
 ('chatbot_do_dai_tin','1000','Số ký tự tối đa của một tin'),
 ('tach_cau_moi_gio','30','Số lần tìm bằng câu mô tả tối đa mỗi giờ'),
 ('chatbot_dong_thoi_toi_da','4','Số lượt gọi mô hình cùng lúc trong một tiến trình'),
 ('chatbot_tran_chi_phi_ngay_usd','2','Trần chi phí mô hình mỗi ngày; vượt thì chuyển quy_tac tới 0 giờ'),
 ('chatbot_gia_usd_moi_trieu_vao','0.15','Giá token vào (tính chi phí ở A01)'),
 ('chatbot_gia_usd_moi_trieu_ra','0.60','Giá token ra (tính chi phí ở A01)'),
 ('chatbot_luu_nhat_ky_ngay','90','Số ngày giữ nội dung tin (D-037)');
