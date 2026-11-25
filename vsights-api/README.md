# vsights-api — Backend Vsights 0.6.4 (T-006, T-020, T-024, T-013, T-014)

FastAPI 0.162 + SQLAlchemy 2.1 (Core) + psycopg 3 + PostgreSQL 16 — đúng mốc SA-007 / `base/02`. Viết lại từ đầu theo `base/02` (kiến trúc, hợp đồng API), Cheat Sheet mục 6–8 và ERD bản 3.1 (D-031, D-034), vì mã 0.5 không còn.

## Chạy nhanh
Hướng dẫn từng bước cho Windows/macOS: `claude/SA_T006_HUONG_DAN_CHAY_BE_FE.md`.
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # điền VS_JWT_SECRET; mật khẩu PostgreSQL vào DSN hoặc PGPASSWORD
PGHOST=localhost PGUSER=postgres ./scripts/nap_csdl.sh # tạo CSDL vsights: 66 bảng + danh mục + dữ liệu mẫu
uvicorn app.main:app --reload                          # http://localhost:8000/docs
```
Tài khoản mẫu (mật khẩu `matkhau123`, chỉ dùng trên máy cá nhân): `quantri@vidu.vn` (quản trị), `dukhach@vidu.vn` (du khách), `chuaxacthuc@vidu.vn` (chưa xác thực email → 403).
Giá tham khảo mẫu sinh cho 120 đêm **kể từ ngày nạp**; demo ở ngày khác thì nạp lại.

## Cấu trúc (Controller – Service – Repository – Adapter)
```
app/
  main.py            tạo app, CORS (localhost:5173, allow_credentials), gắn router, xử lý lỗi
  core/              config (biến VS_*), db (engine), errors (AppError, SQLSTATE→409/422), security (Argon2id, JWT)
  api/               Controller: auth, cong_khai (/catalog, /places, /stays/search, /stays/compare, /stays/{ma}), quan_tri (/admin/*), schemas, deps
  services/          Nghiệp vụ + giao dịch: xac_thuc, quan_tri, tim_kiem, gia (chi tiết + giá từng đêm, T-013), so_sanh (T-014); hop_dong (kiểu + chữ ký service cho công cụ chatbot, SA-017)
  repositories/      SQL có tham số, FOR UPDATE, khoá tư vấn, UPSERT: xac_thuc, cho_o, dia_diem, danh_muc, tim_kiem, gia
  adapters/          (trống ở giữa kỳ — OTA, bản đồ, Google/Zalo, mô hình ngôn ngữ làm ở T-013…T-016)
db/  01_schema.sql (66 bảng) · 02_danh_muc.sql (34 tỉnh, tiện nghi, OTA, cấu hình) · 03_du_lieu_mau.sql · (04_bo_sung_de.sql, 05_kiem_chat_luong.sql của DE — nạp nếu có, SA-020)
scripts/  nap_csdl.sh · do_hieu_nang.py
tests/    94 ca kiểm thử tích hợp trên PostgreSQL thật
```

## API (26 đường dẫn, 32 thao tác — xem `/docs`)
| Nhóm | Endpoint |
|---|---|
| Xác thực | `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me` |
| Danh mục | `GET /catalog/provinces` · `/catalog/amenities` · `/catalog/interests` · `/catalog/place-types` |
| Công khai | `GET /places` (lọc `ma_tinh, nhom, ma_loai, ma_so_thich, q`, phân trang) · `GET /places/{ma}` · `GET /stays/search` · `GET /stays/compare` · `GET /stays/{ma}` |
| Quản trị chỗ ở | `GET/POST /admin/stays` · `GET/PATCH /admin/stays/{ma}` · `POST /admin/stays/{ma}/an` `{ly_do}` · `POST .../hien` |
| Quản trị loại phòng | `GET/POST /admin/stays/{ma}/room-types` · `GET/PATCH /admin/room-types/{ma}` · `POST .../an` · `.../hien` |
| Quản trị địa điểm | `GET/POST /admin/places` · `GET/PATCH /admin/places/{ma}` · `POST .../an` · `.../hien` |

Không có `DELETE`: "Xoá" = ẩn kèm lý do. Lỗi luôn `{ma_loi, thong_bao, chi_tiet}`; danh sách `{items, tong, trang, kich_thuoc}`.

`GET /stays/search?ma_tinh&ngay_nhan&ngay_tra&so_nguoi&so_phong&ngan_sach&loai_ngan_sach=moi_dem|ca_chuyen&loai_hinh&ma_tien_nghi&ma_so_thich&sap_xep=phu_hop|gia_tang|danh_gia` — "khả dụng" = có giá cho đủ mọi đêm trên cùng một OTA (D-028b); mọi phép chọn rẻ nhất, lọc ngân sách, sắp xếp giá dùng giá **đã gồm thuế, phí** (D-021).
- Mỗi kết quả có `gia_ngoai_phep_so`: giá của OTA **chưa gồm thuế, phí và chưa có tỷ lệ quy đổi** (Traveloka trong dữ liệu mẫu), nhãn "chưa gồm thuế, phí · không so", **không** dùng để chọn rẻ nhất, lọc, sắp xếp (B-023). Cơ sở chỉ có giá loại này thì không vào kết quả tìm (không lọc ngân sách được), vẫn xem được ở `GET /stays/{ma}` (SA-019).
- Không có kết quả → `goi_y_noi_dieu_kien: [{dieu_kien, gia_tri, nhan, so_ket_qua}]` (B-028): thử bỏ từng tiện nghi (tối đa 5), bỏ mọi tiện nghi, bỏ ngân sách, bỏ loại hình, dời ngày ±1…3 (cùng số đêm, không về quá khứ); `so_ket_qua` là số đếm thật; chỉ trả gợi ý có kết quả, không có thì một gợi ý chung (`so_ket_qua = null`). `dieu_kien` là tên tham số giao diện phải bỏ/đổi.
- Xin trang vượt số trang: `items` rỗng nhưng `tong` vẫn đúng.

`GET /stays/{ma}?ngay_nhan&ngay_tra&so_nguoi&so_phong` (UC03, mở cho khách vãng lai; ẩn hoặc không có → 404) — kiểu trả về `hop_dong.ChiTietChoO`, cũng là hàm công cụ chatbot gọi (`services/gia.chi_tiet_cho_o`). Có dải ngày thì mỗi loại phòng có `gia_theo_ota`: giá **từng đêm** (đã quy đổi nếu so được), `nhan_thue_phi` ("đã gồm thuế, phí" / "đã quy đổi +15% thuế, phí" / "chưa gồm thuế, phí · không so"), `du_dem`, `tong_ca_chuyen` (cùng công thức với tìm kiếm nên rẻ nhất ở trang chi tiết trùng thẻ kết quả), `cap_nhat_gia` (lần cũ nhất), `gia_cu` (quá 3 ngày, BR-03), `xep_hang_gia` (chỉ loại phòng đủ sức chứa, so được, đủ đêm). `re_nhat = [ma_loai_phong, ma_lien_ket]`; `ngay_re_hon`: tối đa 3 khoảng cùng số đêm, dời ±3 ngày, rẻ hơn (UC03-A4).

`GET /stays/compare?ma_co_so=…&ma_co_so=…[&ma_co_so=…]&ngay_nhan&ngay_tra&so_nguoi&so_phong&ma_tien_nghi&diem=dia_diem:<mã>|cho_o:<mã>` (UC09, W07/M07, mở cho khách vãng lai; SA-021) — kiểu trả `hop_dong.SoSanh` (`services/so_sanh.so_sanh`, chatbot gọi chung hàm). 2–3 chỗ ở cùng tỉnh (`SO_LUONG_SO_SANH`, `KHAC_TINH`), ẩn → 404, tối đa 5 điểm. Hàng (`ma_hang`): `gia_ca_chuyen`, `gia_tb_dem`, `ota_re_nhat` (cùng gốc với thẻ tìm kiếm, D-021), `gia_khong_so` (chỉ khi có, không tô), `diem_danh_gia` ("Chưa đủ đánh giá" khi < 3 lượt), `hang_sao`, `khoang_cach:<loai>:<ma>` (đường chim bay, "(ước tính)"), `tien_nghi:<ma>` (tiện nghi đã lọc, có/không), rồi theo **loại phòng đang so** (rẻ nhất trong phép so): `loai_phong`, `bua_sang`, `chinh_sach_huy`, `huy_mien_phi`, `thanh_toan_tai_cho`, `suc_chua`, `dien_tich`. Ô rỗng ghi "Chưa có thông tin". `o_tot_nhat` tô theo từng hàng (mọi ô bằng nhau hoặc hàng không có thứ tự thì rỗng); không có "tốt nhất" tổng thể (D-022c).

## Kiểm thử
```bash
PGHOST=localhost PGUSER=postgres python -m pytest -q     # tự tạo lại CSDL vsights_test
```
Kết quả SA chạy 2026-11-20, bản 0.6.4 (FastAPI 0.162.7, SQLAlchemy 2.1.9): **94 passed** (9 giây). Bộ độc lập của QC `vsights-api-tests/` (0.6.3, QC chạy 19/11): 52 đạt, 1 xfail (`TC-API-L01` = B-036) — B-036 đã sửa ở 0.6.4 nên ca này sẽ báo XPASS(strict). Gồm:
- **Xác thực (16), mã BM-01…BM-08 (đối chiếu `base/02` mục 5.2 ở `SA_T004` D.2):** cookie HttpOnly/Secure/SameSite=Strict/Path=/auth; sai mật khẩu và email không tồn tại trả cùng lỗi; `EMAIL_CHUA_XAC_THUC`, `TAI_KHOAN_BI_KHOA` chỉ báo khi đúng mật khẩu; kiểm Origin ở 3 endpoint; 429 + Retry-After sau 5 lần sai theo cặp (email, IP); 12 yêu cầu sai **song song** không lọt quá 5 lần so mật khẩu; token hết hạn / ký sai khoá; refresh xoay vòng, gửi lại token đã xoay thì thu hồi cả họ phiên và access token đang dùng bị từ chối ngay; hai refresh cùng lúc cùng token chỉ 1 thành công; đăng xuất; CORS có credentials; lệnh xoá cookie theo `VS_COOKIE_SECURE` (B-022).
- **Quản trị (25):** 15 endpoint × (401 thiếu token, 403 `KHONG_DU_QUYEN`); sửa claim vai trò không có tác dụng; không có DELETE (405); tạo/đọc/sửa có nhật ký; dữ liệu sai 422; **4 yêu cầu tạo cùng cơ sở song song → đúng 1 thành công** (khoá tư vấn); ẩn cần lý do, `TRANG_THAI_KHONG_DOI`; loại phòng có cột D-031; địa điểm ẩn thì biến khỏi trang công khai.
- **Tìm kiếm (12):** mã tỉnh sai bị chặn trước truy vấn, không lộ tên ràng buộc (B-024); 34 tỉnh; `/places` lọc, phân trang, tìm không dấu; hợp đồng `/stays/search` (không có `so_phong_con`, không có chữ "còn phòng"); 422 ngày quá khứ, quá 30 đêm, số người < số phòng; thiếu giá 1 đêm thì không khả dụng; **D-021: Booking.com niêm yết rẻ hơn Agoda nhưng sau khi quy đổi thuế phí thì đắt hơn → chọn Agoda**; ngân sách theo đêm / cả chuyến; lọc tiện nghi, loại hình, sức chứa; sắp xếp BR-04; ẩn chỗ ở thì biến khỏi kết quả, hiện lại thì có lại; ràng buộc `EXCLUDE` chặn trùng đêm (23P01).
- **Giá và chi tiết chỗ ở (13, T-013):** hợp đồng `/stays/{ma}` có/không có ngày, 404 khi ẩn, 422 dữ liệu vào; rẻ nhất và tổng ở chi tiết **trùng** thẻ tìm kiếm (1 và 2 phòng); giá từng đêm đối chiếu CSDL (Agoda nguyên giá, Booking.com × 1,15, Traveloka giá gốc · không so, không xếp hạng, đứng sau); thiếu một đêm → `du_dem = false`, không xếp hạng; giá cũ > 3 ngày (BR-03); chỉ xếp hạng loại phòng đủ sức chứa; khoảng ngày rẻ hơn ±3 ngày, không về quá khứ; service chạy trong giao dịch READ ONLY; `/stays/search` hiện riêng giá chưa gồm thuế, phí (B-023); gợi ý nới điều kiện có số kết quả thật, đúng bằng khi áp dụng (B-028), gợi ý dời ngày, gợi ý chung; trang vượt số trang giữ `tong`.
- **So sánh (10, T-014):** hợp đồng hàng, giá trùng thẻ tìm kiếm (1 và 2 phòng), 13 lỗi đầu vào (số lượng, trùng mã, khác tỉnh, ẩn, ngày, điểm sai dạng/không có/khác tỉnh, tiện nghi lạ), "Chưa có thông tin"/"Chưa đủ đánh giá" không được tô, hạn huỷ miễn phí (0 không tô), có/không tô khi khác nhau, tiện nghi đối chiếu CSDL, khoảng cách đối chiếu công thức và tối đa 5 điểm, giá "không so" hiện riêng không tô, cơ sở chưa đủ giá, service trong giao dịch READ ONLY.
- **Tích hợp dữ liệu DE (3, Q-025, SA-020):** mỗi OTA chỉ một lần đồng bộ `dang_chay` (chỉ mục duy nhất từng phần), `lan_dong_bo.chi_tiet` phải là đối tượng JSON; có chỉ mục `thoi_diem` cho thống kê và thông số dọn bảng giá; vẫn 66 bảng.
- **Tích hợp chatbot (15, T-024; +1 ca B-036):** `tim_kiem.tim(ghi_luot=False, loai_tru=…)` chạy trong giao dịch READ ONLY, không ghi lượt tìm, `tong` trừ đúng chỗ ở đã loại; vẫn 66 bảng; cột chatbot (Q-022 = A): đề xuất đủ 4 cột và chỉ ở tin trợ lý, xem xét có trạng thái + mức + lý do hợp lệ, `khoa_gui` chống gửi hai lần; **D-039(a):** nơi nghỉ dự kiến không cần chỗ ở, khác tỉnh bị chặn, chỗ ở "Đã đặt" (khác hoặc cùng cơ sở) thay nơi nghỉ dự kiến đúng các đêm, đổi ngày / huỷ cập nhật đêm, gắn sai cơ sở (FK ghép) hoặc ngoài đêm bị chặn; hợp đồng `hop_dong.ThaoTac` nhận đúng 6 thao tác, từ chối thao tác lạ.

## Đo hiệu năng truy vấn theo dải ngày
```bash
PGHOST=localhost PGUSER=postgres python scripts/do_hieu_nang.py     # ~2 phút, tạo CSDL riêng vsights_do
```
Dữ liệu giả lập: 5.000 cơ sở (tỉnh lớn 1.000), 12.500 loại phòng, 4.242.923 dòng giá. Trung vị 7 lần `EXPLAIN ANALYZE`, PostgreSQL 16.15, máy ảo Linux của SA (2026-11-18):

| Trường hợp | A. Đầy đủ tối ưu | B. Bỏ tối ưu | Quét bảng giá (A) |
|---|---|---|---|
| Tỉnh lớn, 2 đêm | **41,6 ms** | 46,3 ms | Index Only Scan, Heap Fetches = 0 |
| Tỉnh lớn, 7 đêm | **67,9 ms** | 85,1 ms | Index Only Scan, Heap Fetches = 0 |
| Tỉnh lớn, 2 đêm, ngân sách + 2 tiện nghi | **17,6 ms** | 20,6 ms | Index Only Scan, Heap Fetches = 0 |
| Tỉnh nhỏ (~121 cơ sở), 2 đêm | **4,6 ms** | 8,0 ms | Index Only Scan, Heap Fetches = 0 |
| Cơ sở ở tỉnh lớn có tiện nghi "Hồ bơi" | **0,51 ms** | 1,30 ms | — |

B = bỏ 3 chỉ mục từng phần, 2 chỉ mục ngược tiện nghi, khoá chính giá không có `INCLUDE`. Đo lại 2026-11-19 trên bản 0.6.2 (thêm điều kiện `loai_tru` vào CTE ứng viên): A lần lượt 36,5 / 54,9 / 14,3 / 4,1 / 0,40 ms, vẫn `Index Only Scan`, `Heap Fetches = 0` — không chậm hơn; báo cáo giữ số đo 18/11. Trên dữ liệu mẫu demo (408 cơ sở), gọi HTTP `GET /stays/search` tỉnh lớn mất khoảng 9 ms.

Hai thay đổi rút ra khi đo: (1) ép CTE ứng viên `MATERIALIZED` để lọc tiện nghi chạy trên từng loại phòng thay vì trên từng dòng giá; (2) khoá chính giá kèm `gom_thue_phi` (SA-013) vì phép quy đổi thuế phí đọc cột này — nếu thiếu thì không quét chỉ mục thuần được.

## Bảo mật
- Không có bí mật trong mã. `VS_JWT_SECRET` bắt buộc (≥ 32 ký tự), app không khởi động nếu thiếu.
- Mật khẩu Argon2id; refresh token chỉ lưu SHA-256; vai trò đọc lại từ CSDL mỗi yêu cầu.
- Mọi SQL có tham số; tên cột khi INSERT/UPDATE lấy từ danh sách cho phép trong mã, không lấy từ người dùng.
