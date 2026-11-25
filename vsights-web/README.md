# vsights-web — Frontend web responsive Vsights (T-005 → T-027)

SPA **React 18 + Vite 5 + TypeScript**, gọi backend `code/vsights-api` **0.6.3**. **Một bộ mã cho mọi cỡ màn** (D-040): máy tính theo màn W-xx, điện thoại theo bố cục M-xx của canvas; không có app di động riêng. Bảng màn, trạng thái API thật/giả lập: `claude/UI_T027_FRONTEND.md`.

## Chạy

Hướng dẫn đầy đủ (PostgreSQL, nạp dữ liệu, chạy cả hai phía): `claude/SA_T006_HUONG_DAN_CHAY_BE_FE.md`. Tóm tắt:

```bash
# 1. Backend (thư mục vsights-api, đã nạp CSDL theo README của nó)
uvicorn app.main:app --reload            # http://localhost:8000

# 2. Frontend (thư mục này) — cần Node.js 18+
cp .env.example .env                      # VITE_API_URL=http://localhost:8000
npm install
npm run dev                               # mở http://localhost:5173 (đúng chữ "localhost", khớp VS_CORS_ORIGINS)
```

Tài khoản mẫu: `dukhach@vidu.vn` / `matkhau123` (chỉ dùng trên máy cá nhân). Giá mẫu của backend sinh cho 120 đêm kể từ ngày nạp CSDL; demo ngày khác thì nạp lại.

### Chạy thử khi chưa bật backend
```bash
npm run mock-api     # API giả lập tại :8000
npm run dev
```
API giả lập có `/catalog/*`, `/places`, `/stays/search`, `/stays/{ma}` **đúng hình dạng** của 0.6.3 (tỉnh 48 = Đà Nẵng có 14 chỗ ở; Agoda đã gồm thuế, phí; Booking.com ×1,15; Traveloka không so; có đêm thiếu giá, giá cũ > 3 ngày, liên kết hỏng). **Chỉ để thử**: tên, giá, mã tỉnh khác dữ liệu mẫu thật; ảnh chụp nộp báo cáo lấy với backend thật.

## Màn đã có (đợt 1)

| Đường dẫn | Màn | API |
|---|---|---|
| `/` | W01/M01 Trang chủ, ô tìm (tỉnh, ngày trên lịch, người/phòng, ngân sách mỗi đêm/cả chuyến) | `/catalog/provinces` |
| `/cho-o?…` | W03/M03 Kết quả: sắp xếp BR-04, lọc loại hình/sở thích/tiện nghi (điện thoại: ngăn "Bộ lọc"), giá rẻ nhất + nhãn thuế phí, giá "không so" hiện riêng, "Giá có thể đã thay đổi", gợi ý nới điều kiện có số kết quả | `/stays/search`, `/catalog/amenities`, `/catalog/interests` |
| `/cho-o/:ma?…` | W04/W05, M05 Chi tiết: loại phòng, giá mỗi OTA (xếp hạng, rẻ nhất), bảng giá từng đêm "So N trang", ngày rẻ hơn ±3 ngày, huỷ miễn phí, thanh toán tại chỗ, "Xem trên [OTA]" | `/stays/{ma}` |
| `/dia-diem` | W10/M10 Điểm tham quan, quán ăn | `/places` |
| `/dang-nhap`, `/tai-khoan` | W22, W20 rút gọn | `/auth/*` |
| `/tro-ly` | W12/M12 — chỗ gắn khung chat (UX-012), thân chat do AI làm (P4) | — |

## Cấu trúc

```
src/
  api/         client.ts (fetch + làm mới token + Web Locks; query mảng) · auth.ts · places.ts · stays.ts (hợp đồng 0.6.3)
  auth/        AuthContext.tsx
  components/  Header (header web + ThanhTab điện thoại) · OTim · LichChonNgay · HopNoi · TheChoO · ChatMount · BieuTuong · ThongBao · YeuCauDangNhap
  pages/       TrangChu · KetQua · ChiTietChoO · DiaDiem · DangNhap · TaiKhoan · TroLy
  styles/      tokens.css (màu, điểm ngắt UX-011) · base.css
  utils/       dinhDang.ts · ngay.ts (giờ Việt Nam, "T6 20/11 → CN 22/11")
scripts/       mock-api.mjs
```

## Quy tắc đã cài (QC kiểm theo bảng này)
- Ngày nhận, trả **chỉ chọn trên lịch** (NFR-06), không chọn ngày đã qua, tối đa 30 đêm; mặc định "cuối tuần này" = nhận T6, trả CN (D-037(5)).
- Giá to = rẻ nhất trong phép so, nhãn "đã gồm thuế, phí" (Agoda) / "đã quy đổi +15% thuế, phí" (Booking.com); giá Traveloka "chưa gồm thuế, phí · không so" hiện riêng, chữ nhỏ, không xếp hạng (D-021, D-035, B-023).
- "Giá có thể đã thay đổi" khi giá quá 3 ngày (BR-03). Không có chữ "còn phòng", không đếm ngược, không khan hiếm (D-029(5), BR-05).
- "Xem trên [OTA]" mở thẳng trang OTA ở thẻ mới, `rel="noopener noreferrer"`, không hộp xác nhận (D-034).
- Dưới 3 lượt đánh giá: "Chưa đủ đánh giá"; nhãn "Dữ liệu mẫu" (BR-11).
- Không emoji; nút, chip ≥ 44 px; có "Bỏ qua tới nội dung", hộp nổi đóng bằng Esc.

## Đã kiểm (UI, 2026-11-20, với API giả lập)
`npm run build` đạt (tsc + vite). Chrome headless ở 1440 × 900 và 390 × 844: trang chủ, lịch, kết quả, không kết quả + gợi ý, chi tiết + bảng giá từng đêm, địa điểm, trợ lý — không lỗi JavaScript (lỗi console chỉ là phông chữ bị chặn mạng trong máy ảo và 401 của `/auth/refresh` khi chưa đăng nhập). **Chưa chạy với backend thật** — nhờ SA/QC chạy theo `SA_T006`.

## Lưu ý
- Khi lên môi trường thật: thêm Content-Security-Policy; không chèn HTML thô từ dữ liệu (React đã escape; `mo_ta` hiện bằng chữ thuần).
