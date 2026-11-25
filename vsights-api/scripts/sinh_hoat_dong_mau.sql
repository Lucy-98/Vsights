-- sinh_hoat_dong_mau.sql — DE, T-026 bản 1.1 (Q-026 = A, D-042, BR-11)
-- Sinh 30 ngày HOẠT ĐỘNG MẪU để màn A01 (thống kê) và A05 (đồng bộ) có số liệu trình diễn:
-- lượt tìm, lượt chuyển OTA, hội thoại + tin nhắn chatbot, lịch sử đồng bộ. Mọi dòng là dữ liệu mẫu, không phải
-- hành vi người dùng thật; bảng hoạt động không có cột nhãn mẫu nên nhãn nằm ở khoá cấu hình 'hoat_dong_mau' = 'true'
-- (A01 hiện dòng "Số liệu hoạt động là dữ liệu mẫu" khi khoá này bật).
--
-- Cách dùng (sau khi nạp db/01…05):   psql -v ON_ERROR_STOP=1 -d vsights -f scripts/sinh_hoat_dong_mau.sql
-- Gỡ trước khi chạy thật:             psql -v ON_ERROR_STOP=1 -d vsights -f scripts/xoa_hoat_dong_mau.sql
-- Chạy lại khi khoá đang 'true': xoá bộ mẫu cũ rồi sinh lại (cùng hạt giống, ngày tính theo hôm nay giờ Việt Nam).
-- Từ chối chạy nếu khoá đang 'false' mà các bảng hoạt động đã có dòng (đó là dữ liệu thật, không được ghi đè).
-- Không chọn kết quả theo OTA: lượt chuyển rải theo cặp (loại phòng × liên kết) đang hoạt động, không xếp hạng OTA (D-042).
BEGIN;
SELECT setseed(0.42);

DO $$
DECLARE co text; n bigint;
BEGIN
  SELECT gia_tri INTO co FROM cau_hinh_he_thong WHERE khoa = 'hoat_dong_mau';
  IF co IS NULL THEN RAISE EXCEPTION 'Chưa có khoá hoat_dong_mau: nạp db/04_bo_sung_de.sql trước'; END IF;
  IF co <> 'true' THEN
    SELECT (SELECT count(*) FROM luot_tim_kiem) + (SELECT count(*) FROM luot_chuyen_ota)
         + (SELECT count(*) FROM hoi_thoai) + (SELECT count(*) FROM lan_dong_bo) INTO n;
    IF n > 0 THEN
      RAISE EXCEPTION 'Đã có % dòng hoạt động thật; không ghi đè. Gỡ thủ công nếu chắc chắn đó là dữ liệu thử.', n;
    END IF;
  END IF;
END $$;

-- Khoá đang 'true' → mọi dòng hoạt động hiện có là bộ mẫu cũ: gỡ trước khi sinh lại.
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

CREATE TEMP TABLE de_ngay ON COMMIT DROP AS
SELECT d, ((now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date - d) AS ngay
FROM generate_series(0, 29) d;

CREATE TEMP TABLE de_nguoi ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY ma_nguoi_dung) AS n, ma_nguoi_dung
FROM nguoi_dung WHERE email = 'dukhach@vidu.vn' OR email LIKE 'nguoidanhgia%';

-- Tỉnh được tìm nhiều hơn (trọng số): 75% lượt tìm theo danh sách này, 25% đều trên 34 tỉnh.
CREATE TEMP TABLE de_tinh_hay ON COMMIT DROP AS
SELECT array_agg(t.ma_tinh) AS ds
FROM (VALUES ('Hà Nội',5),('Đà Nẵng',6),('Khánh Hòa',5),('Lâm Đồng',5),('TP. Hồ Chí Minh',5),('Quảng Ninh',3),
             ('Huế',3),('An Giang',3),('Hải Phòng',2),('Lào Cai',2),('Ninh Bình',2),('Cần Thơ',2)) w(ten, so)
JOIN tinh_thanh t ON t.ten_tinh = w.ten, LATERAL generate_series(1, w.so);

-- ===================================================================================================
-- 1. Lượt tìm kiếm (T1): ~700 lượt/ngày, cuối tuần nhiều hơn, tăng nhẹ về hôm nay; ~7% không có kết quả (T3)
-- ===================================================================================================
INSERT INTO luot_tim_kiem (ma_nguoi_dung, ma_tinh, ngay_nhan, ngay_tra, so_nguoi, so_phong, ngan_sach, loai_ngan_sach,
                           so_ket_qua, thoi_diem)
SELECT CASE WHEN r1 < 0.35 THEN (SELECT ma_nguoi_dung FROM de_nguoi WHERE n = 1 + floor(r2 * (SELECT count(*) FROM de_nguoi))::int) END,
       CASE WHEN r3 < 0.75 THEN (SELECT ds[1 + floor(r4 * array_length(ds, 1))::int] FROM de_tinh_hay)
            ELSE 1 + floor(r4 * 34)::int END,
       nhan, nhan + dem, so_nguoi, so_phong,
       CASE WHEN r5 < 0.5 THEN NULL ELSE (ARRAY[500000, 800000, 1200000, 2000000, 3500000])[1 + floor(r6 * 5)::int] END,
       CASE WHEN r5 < 0.5 THEN NULL WHEN r7 < 0.6 THEN 'moi_dem' ELSE 'ca_chuyen' END,
       CASE WHEN r8 < 0.07 THEN 0 ELSE 1 + floor(r9 * 12)::int END,
       tg
FROM (
  SELECT x.*,
         (x.ngay_goc + 1 + floor(random() * 60)::int) AS nhan,
         (1 + floor(random() * 4)::int) AS dem,
         (1 + floor(random() * 5)::int) AS so_nguoi,
         (1 + floor(random() * 2)::int) AS so_phong,
         random() r1, random() r2, random() r3, random() r4, random() r5, random() r6, random() r7, random() r8, random() r9,
         (((x.ngay_goc + make_interval(hours => (ARRAY[7,8,9,10,11,12,12,13,14,15,16,17,18,19,19,20,20,20,21,21,21,22,22,23])
                                                   [1 + floor(random() * 24)::int],
                                       mins => floor(random() * 60)::int, secs => floor(random() * 60)::int))
           AT TIME ZONE 'Asia/Ho_Chi_Minh')) AS tg
  FROM (SELECT n.ngay AS ngay_goc, s
        FROM de_ngay n,
        LATERAL generate_series(1, round(700 * (CASE WHEN extract(isodow FROM n.ngay) IN (6, 7) THEN 1.25 ELSE 1 END)
                                              * (0.85 + 0.30 * (29 - n.d) / 29.0) * (0.9 + 0.2 * random()))::int) s) x
) y
WHERE tg <= now();

-- ===================================================================================================
-- 2. Lượt chuyển sang OTA (C1): ~4,5–7,5% số lượt tìm cùng ngày; cặp (loại phòng × liên kết hoạt động) đều nhau
-- ===================================================================================================
CREATE TEMP TABLE de_cap ON COMMIT DROP AS
SELECT row_number() OVER (ORDER BY lp.ma_loai_phong, lk.ma_lien_ket) AS n, lp.ma_loai_phong, lk.ma_lien_ket
FROM loai_phong lp JOIN lien_ket_ota lk ON lk.ma_co_so = lp.ma_co_so AND lk.trang_thai = 'hoat_dong'
WHERE lp.trang_thai = 'hien';

INSERT INTO luot_chuyen_ota (ma_nguoi_dung, ma_loai_phong, ma_lien_ket, ngay_nhan, ngay_tra, so_nguoi, so_phong,
                             gia_tham_khao, thoi_diem)
SELECT CASE WHEN r1 < 0.45 THEN (SELECT ma_nguoi_dung FROM de_nguoi WHERE n = 1 + floor(r2 * (SELECT count(*) FROM de_nguoi))::int) END,
       c.ma_loai_phong, c.ma_lien_ket, nhan, nhan + dem, so_nguoi, 1,
       (SELECT g.gia_dem FROM gia_tham_khao g WHERE g.ma_loai_phong = c.ma_loai_phong AND g.ma_lien_ket = c.ma_lien_ket
          AND g.ngay = greatest(nhan, current_date)),
       tg
FROM (
  SELECT x.*,
         (x.ngay_goc + 1 + floor(random() * 45)::int) AS nhan,
         (1 + floor(random() * 3)::int) AS dem,
         (1 + floor(random() * 4)::int) AS so_nguoi,
         random() r1, random() r2,
         (1 + floor(random() * (SELECT count(*) FROM de_cap))::int) AS ma_cap,
         (((x.ngay_goc + make_interval(hours => (ARRAY[8,9,10,11,12,13,14,15,16,17,18,19,19,20,20,20,21,21,21,22,22,23])
                                                   [1 + floor(random() * 22)::int],
                                       mins => floor(random() * 60)::int, secs => floor(random() * 60)::int))
           AT TIME ZONE 'Asia/Ho_Chi_Minh')) AS tg
  FROM (SELECT n.ngay AS ngay_goc, s
        FROM de_ngay n,
        LATERAL generate_series(1, round(700 * (CASE WHEN extract(isodow FROM n.ngay) IN (6, 7) THEN 1.25 ELSE 1 END)
                                              * (0.85 + 0.30 * (29 - n.d) / 29.0) * (0.045 + 0.03 * random()))::int) s) x
) y JOIN de_cap c ON c.n = y.ma_cap
WHERE tg <= now();

-- ===================================================================================================
-- 3. Chatbot (B1, B3, đề xuất, xem xét): ~20 hội thoại/ngày, 1–4 lượt hỏi-đáp; cột theo SA-017
-- ===================================================================================================
CREATE TEMP TABLE de_ht ON COMMIT DROP AS
SELECT row_number() OVER () AS n, gen_random_uuid() AS phien, tg AS bat_dau, so_cap,
       CASE WHEN r1 < 0.4 THEN (SELECT ma_nguoi_dung FROM de_nguoi WHERE n = 1 + floor(r2 * (SELECT count(*) FROM de_nguoi))::int) END AS nguoi
FROM (
  SELECT floor(1 + random() * 4)::int AS so_cap, random() r1, random() r2,
         ((x.ngay_goc + make_interval(hours => (ARRAY[8,9,10,11,12,13,14,15,16,17,19,19,20,20,21,21,22])[1 + floor(random() * 17)::int],
                                      mins => floor(random() * 60)::int, secs => floor(random() * 60)::int))
           AT TIME ZONE 'Asia/Ho_Chi_Minh') AS tg
  FROM (SELECT n.ngay AS ngay_goc, s FROM de_ngay n,
        LATERAL generate_series(1, 15 + floor(random() * 11)::int) s) x
) y WHERE tg <= now() - interval '5 minutes';

INSERT INTO hoi_thoai (ma_nguoi_dung, ma_phien_an_danh, bat_dau, cap_nhat_luc)
SELECT nguoi, phien, bat_dau, bat_dau + (so_cap * interval '2 minutes') FROM de_ht ORDER BY n;

CREATE TEMP TABLE de_cap_tin ON COMMIT DROP AS
SELECT h.ma_hoi_thoai, d.bat_dau, d.nguoi, j
FROM de_ht d JOIN hoi_thoai h ON h.ma_phien_an_danh = d.phien, LATERAL generate_series(1, d.so_cap) j;

-- tin của người dùng (nội dung mẫu; đã là bản "che thông tin cá nhân" theo quy ước của cột)
INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, y_dinh, bi_tu_choi, khoa_gui, thoi_diem)
SELECT ma_hoi_thoai, 'nguoi_dung', cau[i][1], cau[i][2], cau[i][2] = 'ngoai_pham_vi', gen_random_uuid(),
       bat_dau + ((j - 1) * interval '2 minutes')
FROM (
  SELECT c.*,
         1 + floor(random() * (CASE WHEN random() < 0.05 THEN 10 ELSE 9 END))::int AS i,
         ARRAY[
      ARRAY['[Mẫu] Gợi ý chỗ ở cho 2 người ở Đà Nẵng cuối tuần sau', 'tim_cho_o'],
      ARRAY['[Mẫu] Có lịch trình 3 ngày ở Huế không?', 'lich_trinh'],
      ARRAY['[Mẫu] Quán ăn nào gần Hồ Gươm?', 'hoi_dia_diem'],
      ARRAY['[Mẫu] Chỗ ở nào có hồ bơi, dưới 1 triệu một đêm ở Khánh Hòa?', 'tim_cho_o'],
      ARRAY['[Mẫu] Nên đi Đà Lạt mấy ngày cho gia đình có trẻ nhỏ?', 'lich_trinh'],
      ARRAY['[Mẫu] Bãi biển mẫu nào gần chỗ ở của tôi ở Quảng Ninh?', 'hoi_dia_diem'],
      ARRAY['[Mẫu] Giá chỗ ở có thể thay đổi không?', 'hoi_dia_diem'],
      ARRAY['[Mẫu] Giải giúp tôi bài toán lớp 9', 'ngoai_pham_vi'],
      ARRAY['[Mẫu] Viết giúp tôi bài thơ về mùa thu', 'ngoai_pham_vi'],
      ARRAY['[Mẫu] Tôi bị đau bụng dữ dội, phải làm sao?', 'khan_cap']
    ] AS cau
  FROM de_cap_tin c) q;

-- tin của trợ lý: một lượt trả lời sau mỗi lượt hỏi
INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, y_dinh, huu_ich, thoi_diem,
    pham_vi, nguon_tra_loi, phien_ban_prompt, mo_hinh, do_tre_ms, token_vao, token_vao_cache, token_ra,
    ma_xac_nhan, de_xuat, trang_thai_de_xuat, de_xuat_het_han,
    can_xem_xet, ly_do_xem_xet, muc_xem_xet, trang_thai_xem_xet, nguyen_nhan, ma_qt_xem_xet, xem_xet_luc, bao_sai_ly_do)
SELECT ma_hoi_thoai, 'tro_ly',
       '[Mẫu] ' || CASE pv WHEN 'trong_pham_vi' THEN 'Trả lời mẫu từ dữ liệu mẫu; giá chỉ là giá tham khảo, giá cuối cùng do OTA quyết định.'
                           WHEN 'thieu_du_lieu' THEN 'Hiện chưa có đủ dữ liệu mẫu để trả lời câu này.'
                           WHEN 'ngoai_pham_vi' THEN 'Câu này nằm ngoài phạm vi của trợ lý du lịch.'
                           ELSE 'Nếu đang gặp nguy hiểm, hãy gọi 115 (cấp cứu), 113 (công an) hoặc 114 (cứu hoả).' END,
       CASE pv WHEN 'ngoai_pham_vi' THEN 'ngoai_pham_vi' WHEN 'khan_cap' THEN 'khan_cap' ELSE 'tra_loi' END,
       hi, tg,
       pv, nguon,
       CASE WHEN nguon = 'mo_hinh' THEN 'SP-TRO-LY-1.0' END,
       CASE WHEN nguon = 'mo_hinh' THEN 'openai/gpt-oss-120b' END,
       CASE WHEN nguon = 'mo_hinh' THEN 2000 + floor(r3 * 9000)::int ELSE 40 + floor(r3 * 120)::int END,
       CASE WHEN nguon = 'mo_hinh' THEN tv END,
       CASE WHEN nguon = 'mo_hinh' THEN floor(tv * (0.3 + 0.5 * r5))::int END,
       CASE WHEN nguon = 'mo_hinh' THEN 150 + floor(r6 * 600)::int END,
       CASE WHEN co_de_xuat THEN gen_random_uuid() END,
       CASE WHEN co_de_xuat THEN jsonb_build_object('v', 1, 'loai', 'luu_lich_trinh', 'mau', TRUE) END,
       CASE WHEN co_de_xuat THEN CASE WHEN r10 < 0.55 THEN 'da_xac_nhan' WHEN r10 < 0.75 THEN 'bo_qua' ELSE 'het_han' END END,
       CASE WHEN co_de_xuat THEN tg + interval '30 minutes' END,
       xx,
       CASE WHEN NOT xx THEN NULL WHEN pv = 'khan_cap' THEN ARRAY['khan_cap']
            WHEN bao_sai THEN ARRAY['khong_huu_ich', 'bao_sai'] ELSE ARRAY['khong_huu_ich'] END,
       CASE WHEN NOT xx THEN NULL WHEN pv = 'khan_cap' THEN 3 ELSE 2 END::smallint,
       CASE WHEN NOT xx THEN NULL WHEN da_xem THEN 'da_xem' ELSE 'cho' END,
       CASE WHEN xx AND da_xem THEN (ARRAY['thieu_du_lieu','du_lieu_sai','prompt_chua_ro','nguoi_dung_hieu_nham','ngoai_pham_vi_hop_le'])
                                    [1 + floor(r11 * 5)::int] END,
       CASE WHEN xx AND da_xem THEN (SELECT ma_nguoi_dung FROM nguoi_dung WHERE email = 'quantri@vidu.vn') END,
       CASE WHEN xx AND da_xem THEN tg + interval '1 day' END,
       CASE WHEN xx AND bao_sai THEN (ARRAY['sai_thong_tin','sai_gia','khong_lien_quan','khong_phu_hop','khac'])[1 + floor(r12 * 5)::int] END
FROM (
  SELECT z.*,
         (pv = 'trong_pham_vi' AND r9 < 0.12) AS co_de_xuat,
         (pv = 'khan_cap' OR hi IS FALSE) AS xx,
         (hi IS FALSE AND r13 < 0.3) AS bao_sai,
         (tg < now() - interval '2 days' AND r14 < 0.7) AS da_xem
  FROM (
    SELECT c.ma_hoi_thoai,
           c.bat_dau + ((c.j - 1) * interval '2 minutes') + interval '20 seconds' AS tg,
           CASE WHEN r1 < 0.80 THEN 'trong_pham_vi' WHEN r1 < 0.88 THEN 'thieu_du_lieu'
                WHEN r1 < 0.985 THEN 'ngoai_pham_vi' ELSE 'khan_cap' END AS pv,
           CASE WHEN r1 >= 0.985 THEN 'mau' WHEN r1 >= 0.88 THEN 'quy_tac'
                WHEN r2 < 0.90 THEN 'mo_hinh' WHEN r2 < 0.97 THEN 'quy_tac' ELSE 'mau' END AS nguon,
           CASE WHEN r7 < 0.22 THEN (r8 < 0.85) END AS hi,
           4000 + floor(r4 * 6000)::int AS tv,
           r3, r5, r6, r9, r10, r11, r12, r13, r14
    FROM (SELECT c.*, random() r1, random() r2, random() r3, random() r4, random() r5, random() r6, random() r7, random() r8,
                 random() r9, random() r10, random() r11, random() r12, random() r13, random() r14
          FROM de_cap_tin c) c
  ) z
) w;

-- ===================================================================================================
-- 4. Lịch sử đồng bộ OTA (A05): mỗi OTA mỗi ngày 03:00 giờ Việt Nam, do lịch chạy (ma_quan_tri rỗng, D-036)
-- ===================================================================================================
INSERT INTO lan_dong_bo (ma_ota, ma_quan_tri, bat_dau, ket_thuc, so_ban_ghi, so_loi, trang_thai, thong_bao_loi, chi_tiet)
SELECT o.ma_ota, NULL, bd, bd + (6 + floor(r1 * 20)::int) * interval '1 second',
       sb, sl, tt,
       CASE tt WHEN 'loi_mot_phan' THEN 'Một số dòng giá không hợp lệ (mẫu).' WHEN 'that_bai' THEN 'Nguồn mẫu không phản hồi (mẫu).' END,
       jsonb_build_object('them', CASE WHEN tt = 'that_bai' THEN 0 ELSE floor(r2 * 40)::int END,
                          'sua',  CASE WHEN tt = 'that_bai' THEN 0 ELSE 400 + floor(r3 * 900)::int END,
                          'xoa',  CASE WHEN tt = 'that_bai' THEN 0 ELSE floor(r4 * 30)::int END,
                          'giu_nguyen', CASE WHEN tt = 'that_bai' THEN 0 ELSE sb - 400 END)
FROM (
  SELECT o.ma_ota, n.d,
         (((n.ngay + time '03:00') AT TIME ZONE 'Asia/Ho_Chi_Minh')) AS bd,
         random() r1, random() r2, random() r3, random() r4,
         CASE WHEN random() < 0.02 THEN 'that_bai' WHEN random() < 0.05 THEN 'loi_mot_phan' ELSE 'thanh_cong' END AS tt
  FROM de_ngay n CROSS JOIN nguon_ota o
) s JOIN nguon_ota o USING (ma_ota)
CROSS JOIN LATERAL (SELECT CASE WHEN tt = 'that_bai' THEN 0 ELSE 30000 + floor(s.r1 * 4000)::int END AS sb,
                           CASE tt WHEN 'loi_mot_phan' THEN 3 + floor(s.r2 * 12)::int WHEN 'that_bai' THEN 1 ELSE 0 END AS sl) v
WHERE bd < now();

-- Vài dòng lỗi mẫu cho các lần loi_mot_phan (A05 mở được danh sách lỗi)
INSERT INTO loi_dong_bo (ma_lan, ma_lien_ket, du_lieu_goc, mo_ta_loi, da_xu_ly)
SELECT l.ma_lan, lk.ma_lien_ket,
       jsonb_build_object('ngay', (current_date + 5)::text, 'gia_dem', -1, 'mau', TRUE),
       'Giá không hợp lệ: gia_dem phải lớn hơn 0 (mẫu)', l.bat_dau < now() - interval '10 days'
FROM lan_dong_bo l
CROSS JOIN LATERAL (SELECT ma_lien_ket FROM lien_ket_ota WHERE ma_ota = l.ma_ota ORDER BY ma_lien_ket
                    OFFSET (l.ma_lan % 200)::int LIMIT 2) lk
WHERE l.trang_thai = 'loi_mot_phan';

-- ===================================================================================================
-- 5. Lịch trình mẫu (L1: tỉ lệ đã lưu; L2: tỉ lệ nhóm): ~10 lịch trình/ngày, tên bắt đầu "[Mẫu] "
--    Bảng lich_trinh chưa có cột ngày tạo nên cap_nhat_luc đóng vai thời điểm tạo (xem Q-030).
-- ===================================================================================================
INSERT INTO lich_trinh (ma_chu, ma_tinh, ten, ngay_bat_dau, ngay_ket_thuc, so_nguoi, kieu_nhom, la_nhom, trang_thai, cap_nhat_luc)
SELECT (SELECT ma_nguoi_dung FROM de_nguoi WHERE n = 1 + floor(r1 * (SELECT count(*) FROM de_nguoi))::int),
       tinh, '[Mẫu] Chuyến đi ' || (SELECT ten_tinh FROM tinh_thanh WHERE ma_tinh = tinh) || ' số ' || s,
       bd, bd + dem, so_nguoi,
       (ARRAY['mot_minh','cap_doi','gia_dinh','ban_be'])[1 + floor(r3 * 4)::int],
       r4 < 0.12, CASE WHEN r5 < 0.45 THEN 'da_luu' ELSE 'nhap' END, tg
FROM (
  SELECT x.*, random() r1, random() r3, random() r4, random() r5,
         (CASE WHEN random() < 0.7 THEN (SELECT ds[1 + (abs(hashtext(x.s::text || x.ngay_goc::text)) % array_length(ds, 1))] FROM de_tinh_hay)
               ELSE 1 + floor(random() * 34)::int END)::smallint AS tinh,
         (x.ngay_goc + 3 + floor(random() * 60)::int) AS bd,
         (1 + floor(random() * 4)::int) AS dem,
         (1 + floor(random() * 6)::int) AS so_nguoi,
         (((x.ngay_goc + make_interval(hours => 9 + floor(random() * 13)::int, mins => floor(random() * 60)::int))
           AT TIME ZONE 'Asia/Ho_Chi_Minh')) AS tg
  FROM (SELECT n.ngay AS ngay_goc, s FROM de_ngay n,
        LATERAL generate_series(1, 7 + floor(random() * 7)::int) s) x
) y WHERE tg <= now();

UPDATE cau_hinh_he_thong SET gia_tri = 'true' WHERE khoa = 'hoat_dong_mau';
COMMIT;
ANALYZE luot_tim_kiem; ANALYZE luot_chuyen_ota; ANALYZE hoi_thoai; ANALYZE tin_nhan_chatbot; ANALYZE lan_dong_bo; ANALYZE lich_trinh;
