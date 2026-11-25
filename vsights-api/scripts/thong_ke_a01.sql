-- Thống kê A01 (DE, T-026 1.1, D-042). Biến psql: tu, den (YYYY-MM-DD, giờ Việt Nam, gồm cả hai đầu), ma_tinh, ma_ota ('' = tất cả)
WITH p AS (SELECT :'tu'::date AS tu, :'den'::date AS den, NULLIF(:'ma_tinh','')::int AS tinh, NULLIF(:'ma_ota','')::int AS ota),
tk AS (SELECT l.*, (l.thoi_diem AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay FROM luot_tim_kiem l, p
       WHERE (l.thoi_diem AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN p.tu AND p.den AND (p.tinh IS NULL OR l.ma_tinh = p.tinh)),
ch AS (SELECT c.*, (c.thoi_diem AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay, lk.ma_ota, cs.ma_tinh
       FROM luot_chuyen_ota c JOIN lien_ket_ota lk USING (ma_lien_ket) JOIN co_so_luu_tru cs ON cs.ma_co_so = lk.ma_co_so, p
       WHERE (c.thoi_diem AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN p.tu AND p.den
         AND (p.tinh IS NULL OR cs.ma_tinh = p.tinh) AND (p.ota IS NULL OR lk.ma_ota = p.ota)),
ngay AS (SELECT d::date AS ngay FROM p, generate_series(p.tu, p.den, interval '1 day') d),
lt AS (SELECT l.*, (l.cap_nhat_luc AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay FROM lich_trinh l, p
       WHERE (l.cap_nhat_luc AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN p.tu AND p.den AND (p.tinh IS NULL OR l.ma_tinh = p.tinh)),
bt AS (SELECT m.* FROM tin_nhan_chatbot m, p
       WHERE (m.thoi_diem AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN p.tu AND p.den)
SELECT jsonb_pretty(jsonb_build_object(
 'tu', (SELECT tu FROM p), 'den', (SELECT den FROM p), 'mui_gio', 'Asia/Ho_Chi_Minh',
 'hoat_dong_mau', (SELECT gia_tri = 'true' FROM cau_hinh_he_thong WHERE khoa = 'hoat_dong_mau'),
 'kpi', jsonb_build_object(
   'c2_ty_le_chuyen',   (SELECT jsonb_build_object('gia_tri', round((SELECT count(*) FROM ch)::numeric / NULLIF((SELECT count(*) FROM tk),0), 4),
                                                    'tu_so', (SELECT count(*) FROM ch), 'mau_so', (SELECT count(*) FROM tk))),
   'c1_luot_chuyen',    (SELECT count(*) FROM ch),
   't1_luot_tim',       (SELECT count(*) FROM tk),
   't3_ty_le_khong_ket_qua', (SELECT jsonb_build_object('gia_tri', round(count(*) FILTER (WHERE so_ket_qua = 0)::numeric / NULLIF(count(*),0), 4),
                                                         'tu_so', count(*) FILTER (WHERE so_ket_qua = 0), 'mau_so', count(*)) FROM tk),
   'l1_lich_trinh',     (SELECT jsonb_build_object('tao_moi', count(*), 'da_luu', count(*) FILTER (WHERE trang_thai = 'da_luu'),
                                                    'ty_le_da_luu', round(count(*) FILTER (WHERE trang_thai = 'da_luu')::numeric / NULLIF(count(*),0), 4)) FROM lt),
   'd2_ty_le_gia_cu',   (SELECT jsonb_build_object('gia_tri', round(count(*) FILTER (WHERE moi < now() - interval '3 days')::numeric / NULLIF(count(*),0), 4),
                                                    'tu_so', count(*) FILTER (WHERE moi < now() - interval '3 days'), 'mau_so', count(*))
                         FROM (SELECT lk.ma_lien_ket, max(g.ngay_cap_nhat) AS moi FROM lien_ket_ota lk JOIN gia_tham_khao g USING (ma_lien_ket), p
                               WHERE lk.trang_thai = 'hoat_dong' AND (p.ota IS NULL OR lk.ma_ota = p.ota) GROUP BY 1) z)),
 'theo_doi', jsonb_build_object(   -- chỉ theo dõi, không phải KPI (D-042)
   'b1_hoi_thoai',  (SELECT count(DISTINCT ma_hoi_thoai) FROM bt),
   'b1_cau_hoi',    (SELECT count(*) FROM bt WHERE vai_tro = 'nguoi_dung'),
   'b3_huu_ich',    (SELECT jsonb_build_object('n', count(*) FILTER (WHERE huu_ich IS NOT NULL), 'huu_ich', count(*) FILTER (WHERE huu_ich),
                       'ty_le', CASE WHEN count(*) FILTER (WHERE huu_ich IS NOT NULL) >= 30
                                     THEN round(count(*) FILTER (WHERE huu_ich)::numeric / count(*) FILTER (WHERE huu_ich IS NOT NULL), 4) END,
                       'du_luot', count(*) FILTER (WHERE huu_ich IS NOT NULL) >= 30) FROM bt WHERE vai_tro = 'tro_ly'),
   'de_xuat',       (SELECT jsonb_build_object('tong', count(*) FILTER (WHERE de_xuat IS NOT NULL),
                       'da_xac_nhan', count(*) FILTER (WHERE trang_thai_de_xuat = 'da_xac_nhan'),
                       'ty_le_xac_nhan', round(count(*) FILTER (WHERE trang_thai_de_xuat = 'da_xac_nhan')::numeric / NULLIF(count(*) FILTER (WHERE de_xuat IS NOT NULL),0), 4)) FROM bt),
   'tin_cho_xem_xet', (SELECT count(*) FROM tin_nhan_chatbot WHERE trang_thai_xem_xet = 'cho')),   -- không giới hạn cửa sổ ngày
 'theo_ngay', (SELECT jsonb_agg(jsonb_build_object('ngay', n.ngay,
                 'luot_tim', (SELECT count(*) FROM tk WHERE tk.ngay = n.ngay),
                 'luot_chuyen', (SELECT count(*) FROM ch WHERE ch.ngay = n.ngay)) ORDER BY n.ngay) FROM ngay n),
 'chuyen_theo_ota', (SELECT jsonb_agg(jsonb_build_object('ma_ota', o.ma_ota, 'ten_ota', o.ten_ota, 'luot_chuyen', c.n) ORDER BY o.ma_ota)
                     FROM nguon_ota o LEFT JOIN LATERAL (SELECT count(*) n FROM ch WHERE ch.ma_ota = o.ma_ota) c ON TRUE),   -- xếp theo mã OTA, không theo số lượt (D-042)
 'tinh_tim_nhieu', (SELECT jsonb_agg(x) FROM (SELECT jsonb_build_object('ma_tinh', t.ma_tinh, 'ten_tinh', t.ten_tinh, 'luot_tim', count(*)) x
                     FROM tk JOIN tinh_thanh t USING (ma_tinh) GROUP BY t.ma_tinh, t.ten_tinh ORDER BY count(*) DESC, t.ma_tinh LIMIT 5) q)
));
