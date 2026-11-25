-- 05_kiem_chat_luong.sql — DE, T-026 bản 1.1. Chỉ tạo VIEW (không bảng, không dữ liệu). Chạy lại an toàn (CREATE OR REPLACE).
-- Cần db/04_bo_sung_de.sql đã nạp (khoá cấu hình tinh_ven_bien, tam_phu_<ma_tinh>).

-- Tâm của từng tỉnh: tâm chính + tâm phụ phía biển (D-041, nếu có). QT-C2 tính theo tâm gần nhất.
CREATE OR REPLACE VIEW v_tam_tinh AS
SELECT ma_tinh, vi_do, kinh_do, 'chinh'::text AS loai FROM tinh_thanh
UNION ALL
SELECT substr(khoa, 9)::smallint, split_part(gia_tri, ',', 1)::numeric, split_part(gia_tri, ',', 2)::numeric, 'phu'
FROM cau_hinh_he_thong WHERE khoa ~ '^tam_phu_[0-9]+$';

-- Mã các tỉnh ven biển (D-041).
CREATE OR REPLACE VIEW v_tinh_ven_bien AS
SELECT unnest(string_to_array(gia_tri, ','))::smallint AS ma_tinh FROM cau_hinh_he_thong WHERE khoa = 'tinh_ven_bien';

CREATE OR REPLACE VIEW v_kiem_chat_luong AS
WITH p AS (SELECT (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS hom_nay),
-- QT-G2: giá lệch quá 3 lần trung vị của cặp (loại phòng × liên kết) trong 30 đêm tới
trung_vi AS (
  SELECT ma_loai_phong, ma_lien_ket, percentile_cont(0.5) WITHIN GROUP (ORDER BY gia_dem) tv
  FROM gia_tham_khao, p WHERE ngay >= p.hom_nay AND ngay < p.hom_nay + 30 GROUP BY 1,2),
g2 AS (SELECT count(*) FILTER (WHERE g.gia_dem < tv.tv/3 OR g.gia_dem > tv.tv*3) vp, count(*) tong
       FROM gia_tham_khao g JOIN trung_vi tv USING (ma_loai_phong, ma_lien_ket), p
       WHERE g.ngay >= p.hom_nay AND g.ngay < p.hom_nay + 30),
-- QT-G4: mỗi OTA chỉ có một giá trị gom_thue_phi (D-035)
g4 AS (SELECT coalesce(sum(CASE WHEN n_t > 0 AND n_f > 0 THEN least(n_t, n_f) END),0) vp, coalesce(sum(n_t+n_f),0) tong
       FROM (SELECT lk.ma_ota, count(*) FILTER (WHERE g.gom_thue_phi) n_t, count(*) FILTER (WHERE NOT g.gom_thue_phi) n_f
             FROM gia_tham_khao g JOIN lien_ket_ota lk USING (ma_lien_ket) GROUP BY 1) x),
-- QT-G5: liên kết hỏng/tạm dừng nhưng giá còn mới trong 3 ngày
g5 AS (SELECT count(DISTINCT lk.ma_lien_ket) FILTER (WHERE lk.trang_thai <> 'hoat_dong' AND g.moi) vp, count(DISTINCT lk.ma_lien_ket) tong
       FROM lien_ket_ota lk JOIN (SELECT ma_lien_ket, max(ngay_cap_nhat) > now() - interval '3 days' moi
                                  FROM gia_tham_khao GROUP BY 1) g USING (ma_lien_ket)),
-- QT-G6: liên kết có dòng giá cũ hơn 3 ngày (BR-03)
g6 AS (SELECT count(*) FILTER (WHERE m < now() - interval '3 days') vp, count(*) tong
       FROM (SELECT ma_lien_ket, min(ngay_cap_nhat) m FROM gia_tham_khao, p WHERE ngay >= p.hom_nay GROUP BY 1) x),
-- QT-C2a/b: thiếu toạ độ hoặc cách TÂM GẦN NHẤT của tỉnh quá 40 km (D-023, D-026, D-041)
c2 AS (SELECT count(*) FILTER (WHERE c.vi_do IS NULL OR c.kinh_do IS NULL OR k.km IS NULL OR k.km > 40) vp, count(*) tong
       FROM co_so_luu_tru c
       LEFT JOIN LATERAL (SELECT min(6371*2*asin(sqrt(sin(radians(c.vi_do-t.vi_do)/2)^2
                 + cos(radians(t.vi_do))*cos(radians(c.vi_do))*sin(radians(c.kinh_do-t.kinh_do)/2)^2))) km
                 FROM v_tam_tinh t WHERE t.ma_tinh = c.ma_tinh) k ON TRUE
       WHERE c.trang_thai='hien'),
c2d AS (SELECT count(*) FILTER (WHERE d.vi_do IS NULL OR d.kinh_do IS NULL OR k.km IS NULL OR k.km > 40) vp, count(*) tong
       FROM dia_diem d
       LEFT JOIN LATERAL (SELECT min(6371*2*asin(sqrt(sin(radians(d.vi_do-t.vi_do)/2)^2
                 + cos(radians(t.vi_do))*cos(radians(d.vi_do))*sin(radians(d.kinh_do-t.kinh_do)/2)^2))) km
                 FROM v_tam_tinh t WHERE t.ma_tinh = d.ma_tinh) k ON TRUE
       WHERE d.trang_thai='hien'),
-- QT-C3: trùng cơ sở (tỉnh + tên + địa chỉ đã chuẩn hoá: bỏ dấu, chữ thường, gộp và cắt khoảng trắng)
c3 AS (SELECT coalesce(sum(n-1),0) vp, (SELECT count(*) FROM co_so_luu_tru WHERE trang_thai='hien') tong
       FROM (SELECT count(*) n FROM co_so_luu_tru WHERE trang_thai='hien'
             GROUP BY ma_tinh,
                      btrim(regexp_replace(lower(unaccent(ten)),'\s+',' ','g')),
                      btrim(regexp_replace(lower(unaccent(dia_chi)),'\s+',' ','g'))
             HAVING count(*)>1) x),
-- QT-C4: cơ sở "hiện" nhưng không thể lên kết quả tìm (không có giá 30 đêm tới ở liên kết hoạt động)
c4 AS (SELECT count(*) FILTER (WHERE NOT EXISTS (
          SELECT 1 FROM loai_phong lp JOIN lien_ket_ota lk ON lk.ma_co_so=lp.ma_co_so AND lk.trang_thai='hoat_dong'
          JOIN gia_tham_khao g ON g.ma_loai_phong=lp.ma_loai_phong AND g.ma_lien_ket=lk.ma_lien_ket, p
          WHERE lp.ma_co_so=c.ma_co_so AND lp.trang_thai='hien' AND g.ngay >= p.hom_nay AND g.ngay < p.hom_nay+30)) vp, count(*) tong
       FROM co_so_luu_tru c WHERE c.trang_thai='hien'),
-- QT-C7: diem_tb, so_luot_danh_gia khớp tính lại từ DANH_GIA (ngoại lệ 3NF có chủ đích của SA)
c7 AS (SELECT count(*) FILTER (WHERE c.diem_tb IS DISTINCT FROM x.a OR c.so_luot_danh_gia <> coalesce(x.n,0)) vp, count(*) tong
       FROM co_so_luu_tru c LEFT JOIN (SELECT ma_co_so, round(avg(so_sao),1) a, count(*) n
                                       FROM danh_gia WHERE ma_co_so IS NOT NULL AND trang_thai='hien' GROUP BY 1) x USING (ma_co_so)),
-- QT-C8 (mới, D-041): nhãn "Ven biển", sở thích "Biển", tiện nghi "View biển", chữ "biển"/"Hải Âu" trong tên chỉ ở tỉnh ven biển
c8 AS (SELECT (SELECT count(*) FROM co_so_luu_tru c
                WHERE c.ma_tinh NOT IN (SELECT ma_tinh FROM v_tinh_ven_bien)
                  AND (c.khu_vuc = 'Ven biển' OR lower(c.ten) ~ '(biển|hải âu)'
                       OR EXISTS (SELECT 1 FROM co_so_so_thich x JOIN so_thich s USING (ma_so_thich)
                                  WHERE x.ma_co_so = c.ma_co_so AND s.ten = 'Biển')
                       OR EXISTS (SELECT 1 FROM loai_phong lp JOIN loai_phong_tien_nghi x USING (ma_loai_phong)
                                  JOIN tien_nghi tn USING (ma_tien_nghi)
                                  WHERE lp.ma_co_so = c.ma_co_so AND tn.ten_tien_nghi = 'View biển'))) +
               (SELECT count(*) FROM dia_diem d
                WHERE d.ma_tinh NOT IN (SELECT ma_tinh FROM v_tinh_ven_bien)
                  AND (lower(d.ten) ~ '(biển|hải âu)'
                       OR d.ma_loai = (SELECT ma_loai FROM loai_dia_diem WHERE ten_loai = 'Bãi biển')
                       OR EXISTS (SELECT 1 FROM dia_diem_so_thich x JOIN so_thich s USING (ma_so_thich)
                                  WHERE x.ma_dia_diem = d.ma_dia_diem AND s.ten = 'Biển'))) vp,
              (SELECT count(*) FROM co_so_luu_tru) + (SELECT count(*) FROM dia_diem) tong),
-- QT-D2: địa điểm hiện không có giờ mở cửa
d2 AS (SELECT count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM gio_mo_cua g WHERE g.ma_dia_diem=d.ma_dia_diem)) vp, count(*) tong
       FROM dia_diem d WHERE d.trang_thai='hien'),
-- QT-D5: tỉnh có dưới 12 điểm tham quan (không đủ cho lịch trình nhiều ngày)
d5 AS (SELECT count(*) FILTER (WHERE n < 12) vp, count(*) tong
       FROM (SELECT t.ma_tinh, count(d.*) FILTER (WHERE l.nhom='tham_quan') n
             FROM tinh_thanh t LEFT JOIN dia_diem d ON d.ma_tinh=t.ma_tinh AND d.trang_thai='hien'
             LEFT JOIN loai_dia_diem l USING (ma_loai) GROUP BY 1) x),
-- QT-D6 (mới, D-039b, D-041): tỉnh ven biển phải có ít nhất 1 bãi biển hiện
d6 AS (SELECT count(*) FILTER (WHERE NOT EXISTS (
          SELECT 1 FROM dia_diem d JOIN loai_dia_diem l USING (ma_loai)
          WHERE d.ma_tinh = v.ma_tinh AND l.ten_loai = 'Bãi biển' AND d.trang_thai = 'hien')) vp, count(*) tong
       FROM v_tinh_ven_bien v)
SELECT 'QT-G2'  ma, 'canh_bao'  muc, 'Giá lệch quá 3 lần trung vị cặp phòng × OTA' mo_ta, vp, tong FROM g2
UNION ALL SELECT 'QT-G4',  'chan',      'Một OTA có cả dòng gồm và không gồm thuế phí (D-035)', vp, tong FROM g4
UNION ALL SELECT 'QT-G5',  'canh_bao',  'Liên kết hỏng/tạm dừng nhưng giá còn mới trong 3 ngày', vp, tong FROM g5
UNION ALL SELECT 'QT-G6',  'canh_bao',  'Liên kết có dòng giá cũ hơn 3 ngày (BR-03)', vp, tong FROM g6
UNION ALL SELECT 'QT-C2a', 'canh_bao',  'Cơ sở thiếu toạ độ hoặc cách tâm gần nhất của tỉnh > 40 km', vp, tong FROM c2
UNION ALL SELECT 'QT-C2b', 'canh_bao',  'Địa điểm thiếu toạ độ hoặc cách tâm gần nhất của tỉnh > 40 km', vp, tong FROM c2d
UNION ALL SELECT 'QT-C3',  'canh_bao',  'Trùng cơ sở (tỉnh + tên + địa chỉ chuẩn hoá)', vp, tong FROM c3
UNION ALL SELECT 'QT-C4',  'canh_bao',  'Cơ sở hiện nhưng không thể lên kết quả tìm (không có giá 30 đêm tới)', vp, tong FROM c4
UNION ALL SELECT 'QT-C7',  'chan',      'diem_tb, so_luot_danh_gia không khớp danh_gia', vp, tong FROM c7
UNION ALL SELECT 'QT-C8',  'canh_bao',  'Nhãn, tên, sở thích, tiện nghi "biển" ở tỉnh ngoài danh sách ven biển (D-041)', vp, tong FROM c8
UNION ALL SELECT 'QT-D2',  'canh_bao',  'Địa điểm hiện không có giờ mở cửa', vp, tong FROM d2
UNION ALL SELECT 'QT-D5',  'thong_tin', 'Tỉnh có dưới 12 điểm tham quan', vp, tong FROM d5
UNION ALL SELECT 'QT-D6',  'canh_bao',  'Tỉnh ven biển không có bãi biển (D-039b)', vp, tong FROM d6;
