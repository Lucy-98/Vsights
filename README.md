# Vsights — mã nguồn khung ứng dụng

Ứng dụng web lập kế hoạch du lịch trong nước: tìm chỗ ở, so giá tham khảo đã gồm thuế, phí trên nhiều OTA, địa điểm và quán ăn, lịch trình, trợ lý. Vsights **không nhận đặt chỗ**, chỉ chuyển người dùng sang trang OTA.

| Thư mục | Nội dung | Công nghệ |
|---|---|---|
| `vsights-api/` | Backend **0.6.4**: xác thực JWT + refresh cookie, danh mục, CRUD quản trị chỗ ở, loại phòng, địa điểm; tìm chỗ ở, chi tiết + giá từng đêm, so sánh | Python 3.11+, FastAPI 0.162, SQLAlchemy 2.1 Core, psycopg 3, PostgreSQL 16 |
| `vsights-api/db/` | Lược đồ **66 bảng**, danh mục, dữ liệu mẫu 34 tỉnh, bổ sung của DE, view kiểm chất lượng | SQL |
| `vsights-web/` | Frontend web responsive **0.2.0** (một bộ mã cho máy tính và điện thoại) | React 18, Vite 5, TypeScript, Node.js 18+ |

Tài liệu thiết kế và quyết định nằm trong Project Vsights (`claude/SA_QUYET_DINH.md`, `base/02_BACKEND_VA_KIEN_TRUC_AI.md`, `base/03_FRONTEND_THIET_KE_UI.md`). Repo này chỉ có mã.

---

## 1. Cài một lần

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Git | bất kỳ | Windows: cài **Git for Windows**, kèm **Git Bash** để chạy script `.sh` |
| Python | 3.11 trở lên | Windows: tích "Add python.exe to PATH" khi cài |
| PostgreSQL | **16** | Cài bản đầy đủ (có `psql`). Nhớ mật khẩu user `postgres` đặt lúc cài. Hoặc dùng Docker ở mục 1b |
| Node.js | 18 trở lên (khuyên 20 LTS) | kèm `npm` |
| VS Code | mới nhất | Mở repo xong, VS Code sẽ gợi ý cài các extension trong `.vscode/extensions.json` |

Kiểm tra nhanh trong terminal:
```bash
git --version && python --version && psql --version && node --version
```

### 1b. (Không bắt buộc) PostgreSQL bằng Docker
Nếu không muốn cài PostgreSQL vào máy: cài Docker Desktop, rồi ở thư mục gốc repo chạy
```bash
docker compose up -d          # PostgreSQL 16 ở localhost:5432, user postgres, mật khẩu: xem docker-compose.yml
```
Vẫn cần lệnh `psql` trên máy để nạp dữ liệu (cài gói "command line tools" của PostgreSQL, hoặc trên macOS `brew install libpq`).

---

## 2. Chạy backend (`vsights-api`)

Mở terminal ở thư mục `vsights-api` (Windows: dùng **Git Bash** cho các lệnh dưới).

```bash
cd vsights-api
python -m venv .venv
source .venv/bin/activate              # Windows Git Bash: source .venv/Scripts/activate
                                       # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
```

Sửa `.env`:
- `VS_JWT_SECRET` — tạo chuỗi ngẫu nhiên: `python -c "import secrets;print(secrets.token_urlsafe(40))"`, dán vào.
- `VS_DATABASE_URL` — nếu PostgreSQL có mật khẩu: `postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/vsights`.
- `VS_COOKIE_SECURE=true` để nguyên (Chrome, Edge, Firefox coi `localhost` là an toàn). Chỉ đặt `false` nếu dùng Safari mà tải lại trang bị đăng xuất.

Nạp CSDL (tạo lại từ đầu: 66 bảng + danh mục + dữ liệu mẫu + bổ sung của DE):
```bash
PGHOST=localhost PGUSER=postgres PGPASSWORD=MAT_KHAU ./scripts/nap_csdl.sh
```
Thấy dòng cuối `bảng: 69` (66 bảng + 3 view) là xong.

> Giá mẫu sinh cho **120 đêm kể từ ngày nạp**. Demo vào ngày khác mà thấy hết giá thì chạy lại lệnh nạp.

(Tuỳ chọn) dữ liệu hoạt động mẫu 30 ngày cho màn thống kê quản trị:
```bash
PGHOST=localhost PGUSER=postgres PGPASSWORD=MAT_KHAU psql -v ON_ERROR_STOP=1 -d vsights -f scripts/sinh_hoat_dong_mau.sql
```

Chạy:
```bash
uvicorn app.main:app --reload          # http://localhost:8000/docs  (Swagger, thử API ngay)
```
Kiểm tra: mở http://localhost:8000/health → `{"trang_thai":"ok","phien_ban":"0.6.4"}`.

Tài khoản mẫu (mật khẩu chung `matkhau123`, **chỉ dùng trên máy cá nhân**):

| Email | Vai trò |
|---|---|
| `quantri@vidu.vn` | Quản trị viên (dùng được `/admin/*`) |
| `dukhach@vidu.vn` | Du khách |
| `chuaxacthuc@vidu.vn` | Chưa xác thực email (đăng nhập bị 403 — để thử luồng lỗi) |

### Kiểm thử backend
```bash
PGHOST=localhost PGUSER=postgres PGPASSWORD=MAT_KHAU python -m pytest -q
```
Bộ kiểm thử tự tạo CSDL riêng `vsights_test` (không đụng `vsights`). Kết quả mong đợi: **94 passed**.

---

## 3. Chạy frontend (`vsights-web`)

Mở **terminal thứ hai** (backend vẫn chạy ở terminal đầu):
```bash
cd vsights-web
cp .env.example .env                   # VITE_API_URL=http://localhost:8000
npm install
npm run dev                            # http://localhost:5173
```
Mở đúng địa chỉ `http://localhost:5173` (chữ `localhost`, không dùng `127.0.0.1`) vì backend chỉ cho phép nguồn này (CORS + cookie).

Chưa bật được backend mà vẫn muốn xem giao diện: `npm run mock-api` (API giả lập ở cổng 8000) rồi `npm run dev`. Số liệu giả lập khác dữ liệu mẫu thật.

Kiểm tra trước khi nộp: `npm run build` (gồm kiểm kiểu TypeScript).

---

## 4. Thử nhanh sau khi chạy

1. http://localhost:5173 → chọn **Đà Nẵng**, ngày trên lịch, bấm **Tìm chỗ ở** → danh sách có giá "đã gồm thuế, phí" / "đã quy đổi +15% thuế, phí"; giá Traveloka hiện riêng "chưa gồm thuế, phí · không so".
2. Bấm một chỗ ở → bảng giá từng OTA, **So N trang theo từng đêm**, "Ngày gần đó có giá thấp hơn".
3. **Đăng nhập** bằng `dukhach@vidu.vn` → vào Tài khoản; tải lại trang vẫn đăng nhập (refresh cookie).
4. Swagger http://localhost:8000/docs → `POST /auth/login` bằng `quantri@vidu.vn`, **Authorize** với access token, thử `GET /admin/stays`, `POST /admin/places`, `POST /admin/stays/{ma}/an`.
5. `GET /stays/compare?ma_co_so=…&ma_co_so=…&ngay_nhan=…&ngay_tra=…` → bảng so sánh, ô tốt nhất theo từng hàng.

---

## 5. Đưa lên Git (GitHub hoặc GitLab)

Tạo repo **rỗng, Private** trên GitHub/GitLab (không tích "Add README"), rồi ở thư mục gốc.
Bản tải về (zip) **đã có sẵn thư mục `.git` với commit đầu tiên**, nên bỏ qua 3 dòng đầu; nếu không có `.git` thì chạy đủ:
```bash
git init
git add .
git commit -m "Vsights: khung ứng dụng backend 0.6.4 + frontend 0.2.0"
git branch -M main
git remote add origin https://github.com/<tai-khoan>/vsights.git
git push -u origin main
```
`.gitignore` đã chặn `.env`, `.venv/`, `node_modules/`, `dist/`. **Trước lần đẩy đầu, chạy `git status` và chắc chắn không có tệp `.env` nào trong danh sách.** Khoá Groq (`VS_GROQ_API_KEY`) và mật khẩu PostgreSQL chỉ nằm trong `.env` trên máy.

---

## 6. Lỗi hay gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `nap_csdl.sh: Permission denied` | `chmod +x scripts/nap_csdl.sh` hoặc chạy `bash scripts/nap_csdl.sh` |
| `nap_csdl.sh` báo `$'\r': command not found` (Windows) | Tệp bị đổi sang CRLF. Trong VS Code chọn LF ở góc phải dưới rồi lưu, hoặc `git config core.autocrlf false` rồi clone lại (repo có `.gitattributes` giữ LF) |
| `psql: command not found` | Thêm `C:\Program Files\PostgreSQL\16\bin` vào PATH (Windows) hoặc `brew install libpq && brew link --force libpq` (macOS) |
| `password authentication failed` | Sai `PGPASSWORD` hoặc mật khẩu trong `VS_DATABASE_URL` |
| Backend báo thiếu `VS_JWT_SECRET` | Chưa điền `.env`, hoặc chuỗi ngắn hơn 32 ký tự |
| Frontend báo "Không kết nối được máy chủ" | Backend chưa chạy, hoặc `VITE_API_URL` sai, hoặc mở bằng `127.0.0.1` thay vì `localhost` |
| Tìm kiếm không ra giá | CSDL nạp quá 120 ngày trước hoặc chọn ngày quá xa → chạy lại `nap_csdl.sh` |
| Cổng 8000 hoặc 5173 đang bận | `uvicorn app.main:app --reload --port 8001` và sửa `VITE_API_URL`; đổi cổng 5173 thì phải thêm vào `VS_CORS_ORIGINS` |
