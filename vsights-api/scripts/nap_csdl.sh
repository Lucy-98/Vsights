#!/usr/bin/env bash
# Tạo lại CSDL vsights từ đầu: lược đồ + danh mục + dữ liệu mẫu.
# Dùng biến PG* chuẩn của PostgreSQL (PGHOST, PGPORT, PGUSER, PGPASSWORD). Ví dụ:
#   PGHOST=localhost PGUSER=postgres PGPASSWORD=... ./scripts/nap_csdl.sh
set -euo pipefail
DB="${1:-vsights}"
cd "$(dirname "$0")/.."
psql -v ON_ERROR_STOP=1 -q -d postgres -c "DROP DATABASE IF EXISTS \"$DB\"" -c "CREATE DATABASE \"$DB\""
for f in db/01_schema.sql db/02_danh_muc.sql db/03_du_lieu_mau.sql; do
  echo "→ $f"; psql -v ON_ERROR_STOP=1 -q -d "$DB" -f "$f"
done
# Q-025 #4 (SA-020): tệp của DE — bổ sung dữ liệu mẫu (chỉ thêm, chạy lại không trùng) và view chất lượng.
# Có thì nạp, chưa có thì bỏ qua; SA chạy lại cả hai bộ kiểm thử trước khi nhận tệp vào Project.
for f in db/04_bo_sung_de.sql db/05_kiem_chat_luong.sql; do
  if [ -f "$f" ]; then echo "→ $f"; psql -v ON_ERROR_STOP=1 -q -d "$DB" -f "$f"; fi
done
psql -d "$DB" -tA -c "SELECT 'bảng: ' || count(*) FROM information_schema.tables WHERE table_schema='public'"
