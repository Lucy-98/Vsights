-- =====================================================================
-- VSIGHTS — LƯỢC ĐỒ CSDL (PostgreSQL 16) — theo ERD bản 3.1 (66 bảng)
-- Áp dụng D-031 (ty_le_thue_phi, thanh_toan_tai_cho, so_ngay_huy_mien_phi,
-- bỏ so_phong_con, loai_ngan_sach, email cho phép rỗng) và D-034 (LICH_TRINH).
-- Quy ước: tiền BIGINT (đồng); thời điểm TIMESTAMPTZ; toạ độ NUMERIC(9,6);
-- miền liệt kê TEXT + CHECK; "xoá" chỗ ở/loại phòng/địa điểm = ẩn kèm lý do.
-- Nạp bằng scripts/nap_csdl.sh (tạo lại CSDL từ đầu: 01 → 02 → 03).
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS unaccent;   -- tìm không dấu ("ho" khớp "Hồ")

-- ---------------------------------------------------------------------
-- ERD1 — Danh mục, địa lý, chỗ ở (10 bảng)
-- ---------------------------------------------------------------------
CREATE TABLE vung_mien (
  ma_vung   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten_vung  VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE tinh_thanh (
  ma_tinh   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_vung   SMALLINT NOT NULL REFERENCES vung_mien,
  ten_tinh  VARCHAR(60) NOT NULL UNIQUE,
  vi_do     NUMERIC(9,6),
  kinh_do   NUMERIC(9,6)
);

CREATE TABLE so_thich (
  ma_so_thich SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten         VARCHAR(60) NOT NULL UNIQUE,
  pham_vi     TEXT NOT NULL DEFAULT 'chung' CHECK (pham_vi IN ('chung','cho_o','dia_diem'))
);

CREATE TABLE tien_nghi (
  ma_tien_nghi  SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten_tien_nghi VARCHAR(60) NOT NULL,
  pham_vi       TEXT NOT NULL CHECK (pham_vi IN ('co_so','phong')),
  UNIQUE (ten_tien_nghi, pham_vi)
);

CREATE TABLE co_so_luu_tru (
  ma_co_so         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_tinh          SMALLINT NOT NULL REFERENCES tinh_thanh,
  ten              VARCHAR(200) NOT NULL,
  loai_hinh        TEXT NOT NULL CHECK (loai_hinh IN ('khach_san','homestay','resort','can_ho','nha_nghi')),
  dia_chi          VARCHAR(300) NOT NULL,
  khu_vuc          VARCHAR(100),
  vi_do            NUMERIC(9,6) CHECK (vi_do BETWEEN -90 AND 90),
  kinh_do          NUMERIC(9,6) CHECK (kinh_do BETWEEN -180 AND 180),
  hang_sao         SMALLINT CHECK (hang_sao BETWEEN 1 AND 5),
  mo_ta            TEXT,
  gio_nhan_phong   TIME,
  gio_tra_phong    TIME,
  chinh_sach_huy   TEXT,
  chinh_sach_khac  TEXT,
  diem_tb          NUMERIC(2,1) CHECK (diem_tb BETWEEN 1 AND 5),
  so_luot_danh_gia INT NOT NULL DEFAULT 0 CHECK (so_luot_danh_gia >= 0),
  la_du_lieu_mau   BOOLEAN NOT NULL DEFAULT FALSE,
  trang_thai       TEXT NOT NULL DEFAULT 'hien' CHECK (trang_thai IN ('hien','an')),
  ngay_cap_nhat    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Chỉ mục từng phần cho tìm kiếm: chỉ chỗ ở đang hiện
CREATE INDEX ix_co_so_tim ON co_so_luu_tru (ma_tinh) INCLUDE (ma_co_so) WHERE trang_thai = 'hien';

CREATE TABLE co_so_tien_nghi (
  ma_co_so     BIGINT   NOT NULL REFERENCES co_so_luu_tru,
  ma_tien_nghi SMALLINT NOT NULL REFERENCES tien_nghi,
  PRIMARY KEY (ma_co_so, ma_tien_nghi)
);
CREATE INDEX ix_co_so_tien_nghi_nguoc ON co_so_tien_nghi (ma_tien_nghi, ma_co_so);

CREATE TABLE co_so_so_thich (
  ma_co_so    BIGINT   NOT NULL REFERENCES co_so_luu_tru,
  ma_so_thich SMALLINT NOT NULL REFERENCES so_thich,
  PRIMARY KEY (ma_co_so, ma_so_thich)
);
CREATE INDEX ix_co_so_so_thich_nguoc ON co_so_so_thich (ma_so_thich, ma_co_so);

CREATE TABLE loai_phong (
  ma_loai_phong        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_co_so             BIGINT NOT NULL REFERENCES co_so_luu_tru,
  ten_loai_phong       VARCHAR(150) NOT NULL,
  loai_giuong          VARCHAR(100),
  suc_chua_nl          SMALLINT NOT NULL CHECK (suc_chua_nl BETWEEN 1 AND 20),
  suc_chua_te          SMALLINT NOT NULL DEFAULT 0 CHECK (suc_chua_te BETWEEN 0 AND 10),
  dien_tich            NUMERIC(5,1) CHECK (dien_tich > 0),
  co_bua_sang          BOOLEAN NOT NULL DEFAULT FALSE,
  dieu_kien_huy        TEXT,
  thanh_toan_tai_cho   BOOLEAN,                                           -- D-031(2)
  so_ngay_huy_mien_phi SMALLINT CHECK (so_ngay_huy_mien_phi BETWEEN 0 AND 60), -- D-031(2), đơn vị ngày
  trang_thai           TEXT NOT NULL DEFAULT 'hien' CHECK (trang_thai IN ('hien','an')),
  UNIQUE (ma_loai_phong, ma_co_so)   -- đích cho FK ghép (ảnh, chỗ ở của tôi)
);
CREATE INDEX ix_loai_phong_co_so ON loai_phong (ma_co_so) INCLUDE (ma_loai_phong, suc_chua_nl, suc_chua_te) WHERE trang_thai = 'hien';

CREATE TABLE loai_phong_tien_nghi (
  ma_loai_phong BIGINT   NOT NULL REFERENCES loai_phong,
  ma_tien_nghi  SMALLINT NOT NULL REFERENCES tien_nghi,
  PRIMARY KEY (ma_loai_phong, ma_tien_nghi)
);
CREATE INDEX ix_loai_phong_tien_nghi_nguoc ON loai_phong_tien_nghi (ma_tien_nghi, ma_loai_phong);

CREATE TABLE anh_co_so (
  ma_anh        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_co_so      BIGINT NOT NULL REFERENCES co_so_luu_tru,
  ma_loai_phong BIGINT,
  url           VARCHAR(500) NOT NULL,
  thu_tu        SMALLINT NOT NULL DEFAULT 0,
  FOREIGN KEY (ma_loai_phong, ma_co_so) REFERENCES loai_phong (ma_loai_phong, ma_co_so)
);

-- ---------------------------------------------------------------------
-- ERD3 — Địa điểm, quán ăn, di chuyển (10 bảng)
-- (tạo trước ERD2/ERD4 vì MUC_DA_LUU, LICH_TRINH tham chiếu DIA_DIEM)
-- ---------------------------------------------------------------------
CREATE TABLE loai_dia_diem (
  ma_loai  SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten_loai VARCHAR(60) NOT NULL UNIQUE,
  nhom     TEXT NOT NULL CHECK (nhom IN ('tham_quan','an_uong'))
);

CREATE TABLE dia_diem (
  ma_dia_diem       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_tinh           SMALLINT NOT NULL REFERENCES tinh_thanh,
  ma_loai           SMALLINT NOT NULL REFERENCES loai_dia_diem,
  ten               VARCHAR(200) NOT NULL,
  dia_chi           VARCHAR(300),
  vi_do             NUMERIC(9,6) CHECK (vi_do BETWEEN -90 AND 90),
  kinh_do           NUMERIC(9,6) CHECK (kinh_do BETWEEN -180 AND 180),
  mo_ta             TEXT,
  luu_y             TEXT,
  thoi_diem_dep     VARCHAR(100),
  thoi_luong_goi_y  SMALLINT CHECK (thoi_luong_goi_y BETWEEN 5 AND 1440),
  muc_gia_nguoi_tu  BIGINT CHECK (muc_gia_nguoi_tu >= 0),
  muc_gia_nguoi_den BIGINT,
  lien_ket_mua_ve   VARCHAR(500),
  diem_tb           NUMERIC(2,1) CHECK (diem_tb BETWEEN 1 AND 5),
  so_luot_danh_gia  INT NOT NULL DEFAULT 0 CHECK (so_luot_danh_gia >= 0),
  la_du_lieu_mau    BOOLEAN NOT NULL DEFAULT FALSE,
  trang_thai        TEXT NOT NULL DEFAULT 'hien' CHECK (trang_thai IN ('hien','an')),
  ngay_cap_nhat     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (muc_gia_nguoi_den IS NULL OR muc_gia_nguoi_tu IS NULL OR muc_gia_nguoi_den >= muc_gia_nguoi_tu)
);
CREATE INDEX ix_dia_diem_tim ON dia_diem (ma_tinh, ma_loai) WHERE trang_thai = 'hien';

CREATE TABLE dia_diem_so_thich (
  ma_dia_diem BIGINT   NOT NULL REFERENCES dia_diem,
  ma_so_thich SMALLINT NOT NULL REFERENCES so_thich,
  PRIMARY KEY (ma_dia_diem, ma_so_thich)
);
CREATE INDEX ix_dia_diem_so_thich_nguoc ON dia_diem_so_thich (ma_so_thich, ma_dia_diem);

CREATE TABLE anh_dia_diem (
  ma_anh      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_dia_diem BIGINT NOT NULL REFERENCES dia_diem,
  url         VARCHAR(500) NOT NULL,
  thu_tu      SMALLINT NOT NULL DEFAULT 0
);

CREATE TABLE gio_mo_cua (
  ma_dia_diem    BIGINT   NOT NULL REFERENCES dia_diem,
  thu_trong_tuan SMALLINT NOT NULL CHECK (thu_trong_tuan BETWEEN 1 AND 7), -- 1 = thứ Hai (ISO)
  ca             SMALLINT NOT NULL DEFAULT 1 CHECK (ca BETWEEN 1 AND 3),
  gio_mo         TIME NOT NULL,
  gio_dong       TIME NOT NULL,
  PRIMARY KEY (ma_dia_diem, thu_trong_tuan, ca)
);

CREATE TABLE gia_ve (
  ma_gia_ve     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_dia_diem   BIGINT NOT NULL REFERENCES dia_diem,
  loai_khach    VARCHAR(60) NOT NULL,
  dieu_kien     VARCHAR(200),
  gia           BIGINT NOT NULL CHECK (gia >= 0),
  ngay_cap_nhat TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE loai_mon (
  ma_loai_mon SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten         VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE mon_an (
  ma_mon         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_dia_diem    BIGINT   NOT NULL REFERENCES dia_diem,
  ma_loai_mon    SMALLINT NOT NULL REFERENCES loai_mon,
  ten_mon        VARCHAR(150) NOT NULL,
  gia            BIGINT CHECK (gia >= 0),
  la_mon_nen_thu BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE tuyen_di_chuyen (
  ma_tuyen           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_tinh_di         SMALLINT NOT NULL REFERENCES tinh_thanh,
  ma_tinh_den        SMALLINT NOT NULL REFERENCES tinh_thanh,
  phuong_tien        TEXT NOT NULL CHECK (phuong_tien IN ('may_bay','tau_hoa','xe_khach','tu_lai')),
  thoi_gian_uoc_tinh SMALLINT NOT NULL CHECK (thoi_gian_uoc_tinh > 0),
  gia_tu             BIGINT,
  gia_den            BIGINT,
  lien_ket_dat_ve    VARCHAR(500),
  ngay_cap_nhat      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ma_tinh_di <> ma_tinh_den)
);

CREATE TABLE thoi_gian_di_chuyen (
  ma          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  vi_do_di    NUMERIC(8,5) NOT NULL,
  kinh_do_di  NUMERIC(8,5) NOT NULL,
  vi_do_den   NUMERIC(8,5) NOT NULL,
  kinh_do_den NUMERIC(8,5) NOT NULL,
  phuong_tien TEXT NOT NULL CHECK (phuong_tien IN ('di_bo','xe_may','o_to')),
  km          NUMERIC(7,2) NOT NULL,
  phut        SMALLINT NOT NULL,
  ngay_tinh   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (vi_do_di, kinh_do_di, vi_do_den, kinh_do_den, phuong_tien)
);

-- ---------------------------------------------------------------------
-- ERD4 — Người dùng, hệ thống (12 bảng)
-- ---------------------------------------------------------------------
CREATE TABLE nguoi_dung (
  ma_nguoi_dung     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email             VARCHAR(254),                     -- rỗng được cho tài khoản Zalo (D-031, D-030)
  mat_khau_bam      VARCHAR(200),
  ho_ten            VARCHAR(100) NOT NULL,
  anh               VARCHAR(500),
  vai_tro           TEXT NOT NULL DEFAULT 'du_khach' CHECK (vai_tro IN ('du_khach','quan_tri')),
  email_da_xac_thuc BOOLEAN NOT NULL DEFAULT FALSE,
  kieu_di           TEXT CHECK (kieu_di IN ('mot_minh','cap_doi','gia_dinh','ban_be')),
  nhip_do           TEXT CHECK (nhip_do IN ('thong_tha','vua','day')),
  ma_tinh_xuat_phat SMALLINT REFERENCES tinh_thanh,
  khoa_danh_gia     BOOLEAN NOT NULL DEFAULT FALSE,
  trang_thai        TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong','khoa','cho_xoa','da_xoa')),
  tao_luc           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (email IS NULL OR email = lower(email))
);
-- Duy nhất khi có email (chỉ mục duy nhất từng phần)
CREATE UNIQUE INDEX ux_nguoi_dung_email ON nguoi_dung (email) WHERE email IS NOT NULL;

CREATE TABLE so_thich_nguoi_dung (
  ma_nguoi_dung BIGINT   NOT NULL REFERENCES nguoi_dung,
  ma_so_thich   SMALLINT NOT NULL REFERENCES so_thich,
  PRIMARY KEY (ma_nguoi_dung, ma_so_thich)
);

CREATE TABLE tai_khoan_lien_ket (
  ma            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  nha_cung_cap  TEXT NOT NULL CHECK (nha_cung_cap IN ('google','zalo')),
  ma_ben_ngoai  VARCHAR(255) NOT NULL,
  UNIQUE (nha_cung_cap, ma_ben_ngoai)
);

CREATE TABLE ma_xac_thuc (
  ma            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  loai          TEXT NOT NULL CHECK (loai IN ('xac_thuc_email','dat_lai_mat_khau')),
  token_bam     CHAR(64) NOT NULL UNIQUE,
  het_han       TIMESTAMPTZ NOT NULL,
  da_dung       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE phien_dang_nhap (
  ma_phien      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_ho_phien   UUID NOT NULL,              -- mọi token xoay vòng từ một lần đăng nhập
  token_bam     CHAR(64) NOT NULL UNIQUE,   -- SHA-256 của refresh token, không lưu token gốc
  thiet_bi      VARCHAR(200),
  tao_luc       TIMESTAMPTZ NOT NULL DEFAULT now(),
  het_han       TIMESTAMPTZ NOT NULL,
  xoay_luc      TIMESTAMPTZ                 -- khác rỗng: token này đã bị xoay, dùng lại = bị đánh cắp
);
CREATE INDEX ix_phien_ho ON phien_dang_nhap (ma_ho_phien);

CREATE TABLE muc_da_luu (
  ma_muc_luu    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_co_so      BIGINT REFERENCES co_so_luu_tru,
  ma_dia_diem   BIGINT REFERENCES dia_diem,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (num_nonnulls(ma_co_so, ma_dia_diem) = 1)
);
CREATE UNIQUE INDEX ux_muc_da_luu ON muc_da_luu (ma_nguoi_dung, coalesce(ma_co_so, 0), coalesce(ma_dia_diem, 0));

CREATE TABLE yeu_cau_xoa_tai_khoan (
  ma_yeu_cau    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_qt_xu_ly   BIGINT REFERENCES nguoi_dung,
  trang_thai    TEXT NOT NULL DEFAULT 'cho_xu_ly' CHECK (trang_thai IN ('cho_xu_ly','da_xoa','tu_choi','da_huy')),
  tao_luc       TIMESTAMPTZ NOT NULL DEFAULT now(),
  xu_ly_luc     TIMESTAMPTZ
);

CREATE TABLE thong_bao (
  ma_thong_bao  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  loai          VARCHAR(40) NOT NULL,
  noi_dung      TEXT NOT NULL,
  lien_ket      VARCHAR(500),
  da_doc        BOOLEAN NOT NULL DEFAULT FALSE,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE nhat_ky_quan_tri (
  ma_nhat_ky   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_quan_tri  BIGINT NOT NULL REFERENCES nguoi_dung,
  hanh_dong    VARCHAR(60) NOT NULL,
  doi_tuong    VARCHAR(60) NOT NULL,
  ma_doi_tuong BIGINT,
  ly_do        TEXT,
  thoi_diem    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE lan_nhap_du_lieu (
  ma_lan_nhap  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_quan_tri  BIGINT NOT NULL REFERENCES nguoi_dung,
  loai_du_lieu VARCHAR(40) NOT NULL,
  ten_tep      VARCHAR(200) NOT NULL,
  so_dong      INT NOT NULL DEFAULT 0,
  so_loi       INT NOT NULL DEFAULT 0,
  thoi_diem    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cau_hinh_he_thong (
  khoa    VARCHAR(60) PRIMARY KEY,
  gia_tri VARCHAR(200) NOT NULL,
  mo_ta   TEXT
);

CREATE TABLE dang_nhap_that_bai (
  email_chuan  VARCHAR(254) NOT NULL,
  dia_chi_ip   INET NOT NULL,
  so_lan       SMALLINT NOT NULL DEFAULT 0,
  khoa_den     TIMESTAMPTZ,
  cap_nhat_luc TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (email_chuan, dia_chi_ip)
);

-- ---------------------------------------------------------------------
-- ERD5 — Lịch trình, chatbot (10 bảng)
-- ---------------------------------------------------------------------
CREATE TABLE lich_trinh (
  ma_lich_trinh     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_chu            BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_tinh           SMALLINT NOT NULL REFERENCES tinh_thanh,
  khu_vuc           VARCHAR(100),                 -- D-034
  ten               VARCHAR(150) NOT NULL,
  ngay_bat_dau      DATE NOT NULL,
  ngay_ket_thuc     DATE NOT NULL,
  gio_den           TIME,
  gio_ve            TIME,
  gio_bat_dau_ngay  TIME,                         -- D-034
  gio_ket_thuc_ngay TIME,                         -- D-034
  so_nguoi          SMALLINT NOT NULL CHECK (so_nguoi BETWEEN 1 AND 30),
  kieu_nhom         TEXT NOT NULL DEFAULT 'mot_minh' CHECK (kieu_nhom IN ('mot_minh','cap_doi','gia_dinh','ban_be')),
  ngan_sach         BIGINT CHECK (ngan_sach > 0),
  loai_ngan_sach    TEXT CHECK (loai_ngan_sach IN ('moi_dem','ca_chuyen')),
  nhip_do           TEXT CHECK (nhip_do IN ('thong_tha','vua','day')),
  phuong_tien       TEXT CHECK (phuong_tien IN ('di_bo','xe_may','o_to')),
  la_nhom           BOOLEAN NOT NULL DEFAULT FALSE,
  trang_thai        TEXT NOT NULL DEFAULT 'nhap' CHECK (trang_thai IN ('nhap','da_luu')),
  chi_phi_uoc_tinh  BIGINT,
  da_xoa            BOOLEAN NOT NULL DEFAULT FALSE,
  cap_nhat_luc      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ngay_ket_thuc >= ngay_bat_dau AND ngay_ket_thuc - ngay_bat_dau < 14),   -- tối đa 14 ngày
  CHECK (gio_ket_thuc_ngay IS NULL OR gio_bat_dau_ngay IS NULL OR gio_ket_thuc_ngay > gio_bat_dau_ngay)
);

CREATE TABLE lich_trinh_so_thich (
  ma_lich_trinh BIGINT   NOT NULL REFERENCES lich_trinh,
  ma_so_thich   SMALLINT NOT NULL REFERENCES so_thich,
  PRIMARY KEY (ma_lich_trinh, ma_so_thich)
);

CREATE TABLE diem_rang_buoc (
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  ma_dia_diem   BIGINT NOT NULL REFERENCES dia_diem,
  loai          TEXT NOT NULL CHECK (loai IN ('bat_buoc','tranh')),
  PRIMARY KEY (ma_lich_trinh, ma_dia_diem)
);

-- ERD2 — các bảng OTA cần trước CHO_O_CUA_TOI (NGAY_LICH_TRINH tham chiếu)
CREATE TABLE nguon_ota (
  ma_ota         SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten_ota        VARCHAR(50) NOT NULL UNIQUE,
  url_goc        VARCHAR(200) NOT NULL,
  ma_doi_tac     VARCHAR(100),
  kieu_ket_noi   TEXT NOT NULL CHECK (kieu_ket_noi IN ('api','tep','thu_cong')),
  ty_le_thue_phi NUMERIC(5,2) CHECK (ty_le_thue_phi BETWEEN 0 AND 100),   -- D-031(1), %
  trang_thai     TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong','tam_dung'))
);

CREATE TABLE lien_ket_ota (
  ma_lien_ket    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_co_so       BIGINT   NOT NULL REFERENCES co_so_luu_tru,
  ma_ota         SMALLINT NOT NULL REFERENCES nguon_ota,
  url            VARCHAR(500) NOT NULL,
  ho_tro_tham_so BOOLEAN NOT NULL DEFAULT FALSE,
  trang_thai     TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong','hong','tam_dung')),
  lan_kiem_tra   TIMESTAMPTZ,
  UNIQUE (ma_co_so, ma_ota)
);
CREATE INDEX ix_lien_ket_hoat_dong ON lien_ket_ota (ma_co_so) INCLUDE (ma_lien_ket, ma_ota) WHERE trang_thai = 'hoat_dong';

CREATE TABLE gia_tham_khao (
  ma_loai_phong BIGINT NOT NULL REFERENCES loai_phong,
  ma_lien_ket   BIGINT NOT NULL REFERENCES lien_ket_ota,
  ngay          DATE   NOT NULL,
  gia_dem       BIGINT NOT NULL CHECK (gia_dem > 0),
  gom_thue_phi  BOOLEAN NOT NULL DEFAULT TRUE,
  ngay_cap_nhat TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Khoá chính phủ: đọc đúng một đoạn chỉ mục dài bằng số đêm, quét chỉ mục thuần.
  -- D-031(3): không còn so_phong_con. Kèm gom_thue_phi vì phép quy đổi thuế phí (D-021) đọc cột này (SA-013).
  PRIMARY KEY (ma_loai_phong, ma_lien_ket, ngay) INCLUDE (gia_dem, gom_thue_phi)
);
-- Q-025 #5 (SA-020): đồng bộ hằng ngày chạm ~220.000 dòng → dọn bản ghi chết sớm hơn mặc định (0,2 / 0,1)
ALTER TABLE gia_tham_khao SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

CREATE TABLE luot_chuyen_ota (
  ma_luot       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT REFERENCES nguoi_dung,
  ma_loai_phong BIGINT NOT NULL REFERENCES loai_phong,
  ma_lien_ket   BIGINT NOT NULL REFERENCES lien_ket_ota,
  ngay_nhan     DATE NOT NULL,
  ngay_tra      DATE NOT NULL,
  so_nguoi      SMALLINT NOT NULL CHECK (so_nguoi >= 1),
  so_phong      SMALLINT NOT NULL CHECK (so_phong >= 1),
  gia_tham_khao BIGINT,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ngay_tra > ngay_nhan AND ngay_tra - ngay_nhan <= 30)
);
CREATE INDEX ix_luot_chuyen_thoi_diem ON luot_chuyen_ota (thoi_diem);     -- Q-025 #3

CREATE TABLE cho_o_cua_toi (
  ma_cho_o      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_co_so      BIGINT NOT NULL REFERENCES co_so_luu_tru,
  ma_loai_phong BIGINT,
  ma_luot       BIGINT REFERENCES luot_chuyen_ota,
  ma_lich_trinh BIGINT REFERENCES lich_trinh,
  ngay_nhan     DATE NOT NULL,
  ngay_tra      DATE NOT NULL,
  so_phong      SMALLINT NOT NULL DEFAULT 1 CHECK (so_phong >= 1),
  trang_thai    TEXT NOT NULL DEFAULT 'da_dat' CHECK (trang_thai IN ('da_dat','da_huy')),  -- tự khai
  cap_nhat_luc  TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (ma_loai_phong, ma_co_so) REFERENCES loai_phong (ma_loai_phong, ma_co_so),
  UNIQUE (ma_cho_o, ma_co_so),   -- đích cho FK ghép từ NGAY_LICH_TRINH (nơi nghỉ đúng cơ sở của chỗ ở, D-039a)
  CHECK (ngay_tra > ngay_nhan AND ngay_tra - ngay_nhan <= 30),
  -- Chống trùng đêm trong cùng lịch trình, đúng cả khi ghi đồng thời (lỗi 23P01 → 409)
  CONSTRAINT ex_cho_o_trung_dem EXCLUDE USING gist (
    ma_lich_trinh WITH =, daterange(ngay_nhan, ngay_tra, '[)') WITH &&
  ) WHERE (ma_lich_trinh IS NOT NULL AND trang_thai = 'da_dat')
);

CREATE TABLE luot_tim_kiem (
  ma_luot_tim    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung  BIGINT REFERENCES nguoi_dung,
  ma_tinh        SMALLINT NOT NULL REFERENCES tinh_thanh,
  ngay_nhan      DATE NOT NULL,
  ngay_tra       DATE NOT NULL,
  so_nguoi       SMALLINT NOT NULL,
  so_phong       SMALLINT NOT NULL,
  ngan_sach      BIGINT,
  loai_ngan_sach TEXT CHECK (loai_ngan_sach IN ('moi_dem','ca_chuyen')),   -- D-031(4)
  so_ket_qua     INT NOT NULL DEFAULT 0,
  thoi_diem      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((ngan_sach IS NULL) = (loai_ngan_sach IS NULL))
);
CREATE INDEX ix_luot_tim_thoi_diem ON luot_tim_kiem (thoi_diem);          -- Q-025 #3: thống kê theo khoảng ngày (DE)

CREATE TABLE lan_dong_bo (
  ma_lan        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_ota        SMALLINT NOT NULL REFERENCES nguon_ota,
  ma_quan_tri   BIGINT REFERENCES nguoi_dung,
  bat_dau       TIMESTAMPTZ NOT NULL DEFAULT now(),
  ket_thuc      TIMESTAMPTZ,
  so_ban_ghi    INT NOT NULL DEFAULT 0,
  so_loi        INT NOT NULL DEFAULT 0,
  trang_thai    TEXT NOT NULL DEFAULT 'dang_chay' CHECK (trang_thai IN ('dang_chay','thanh_cong','loi_mot_phan','that_bai')),
  thong_bao_loi TEXT,
  -- Q-025 #2 (DE, SA-020): số thêm/sửa/xoá/giữ nguyên của lần chạy cho A05; thuộc đúng một lần chạy (3NF)
  chi_tiet      JSONB CHECK (chi_tiet IS NULL OR jsonb_typeof(chi_tiet) = 'object')
);
-- Q-025 #1 (SA-020): mỗi OTA chỉ một lần đồng bộ đang chạy (hàng rào thứ hai ngoài khoá tư vấn của DE; base/02 mục 0.5)
CREATE UNIQUE INDEX uq_dong_bo_dang_chay ON lan_dong_bo (ma_ota) WHERE trang_thai = 'dang_chay';

CREATE TABLE loi_dong_bo (
  ma_loi      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lan      BIGINT NOT NULL REFERENCES lan_dong_bo,
  ma_lien_ket BIGINT REFERENCES lien_ket_ota,
  du_lieu_goc JSONB,
  mo_ta_loi   TEXT NOT NULL,
  da_xu_ly    BOOLEAN NOT NULL DEFAULT FALSE
);

-- ERD5 (tiếp)
CREATE TABLE ngay_lich_trinh (
  ma_ngay          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh    BIGINT NOT NULL REFERENCES lich_trinh,
  thu_tu_ngay      SMALLINT NOT NULL CHECK (thu_tu_ngay BETWEEN 1 AND 14),
  ngay             DATE NOT NULL,
  -- D-039(a), SA-018: ma_co_so_nghi có, ma_cho_o rỗng = "Nơi nghỉ dự kiến · chưa đặt";
  -- ma_cho_o có = chỗ ở "Đã đặt (tự khai)", khi đó ma_co_so_nghi bắt buộc đúng cơ sở của chỗ ở (FK ghép).
  ma_co_so_nghi    BIGINT REFERENCES co_so_luu_tru,
  ma_cho_o         BIGINT,
  tieu_de          VARCHAR(200),
  luu_y            TEXT,
  chi_phi_uoc_tinh BIGINT,
  FOREIGN KEY (ma_cho_o, ma_co_so_nghi) REFERENCES cho_o_cua_toi (ma_cho_o, ma_co_so)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CHECK (ma_cho_o IS NULL OR ma_co_so_nghi IS NOT NULL),
  UNIQUE (ma_lich_trinh, thu_tu_ngay),
  UNIQUE (ma_lich_trinh, ngay)
);

CREATE TABLE muc_lich_trinh (
  ma_muc           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_ngay          BIGINT NOT NULL REFERENCES ngay_lich_trinh,
  ma_dia_diem      BIGINT REFERENCES dia_diem,
  thu_tu           SMALLINT NOT NULL,
  loai_muc         TEXT NOT NULL CHECK (loai_muc IN ('tham_quan','an_uong','nghi','di_chuyen','tu_do')),
  gio_bat_dau      TIME,
  gio_ket_thuc     TIME,
  phuong_tien      TEXT CHECK (phuong_tien IN ('di_bo','xe_may','o_to')),
  km               NUMERIC(7,2),
  phut             SMALLINT,
  chi_phi_uoc_tinh BIGINT,
  mo_ta            TEXT,
  da_ghim          BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (ma_ngay, thu_tu) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE diem_bi_loai (
  ma            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  ma_dia_diem   BIGINT NOT NULL REFERENCES dia_diem,
  ly_do         VARCHAR(200) NOT NULL
);

CREATE TABLE phien_ban_lich_trinh (
  ma_phien_ban  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  noi_dung      JSONB NOT NULL,
  tao_luc       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE lien_ket_chia_se (
  ma_lien_ket_cs BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh  BIGINT NOT NULL REFERENCES lich_trinh,
  token          CHAR(32) NOT NULL UNIQUE,
  trang_thai     TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong','thu_hoi')),
  tao_luc        TIMESTAMPTZ NOT NULL DEFAULT now(),
  thu_hoi_luc    TIMESTAMPTZ
);

CREATE TABLE hoi_thoai (
  ma_hoi_thoai     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung    BIGINT REFERENCES nguoi_dung ON DELETE SET NULL,   -- D8: xoá tài khoản thì gỡ liên kết, giữ hội thoại ẩn danh
  ma_lich_trinh    BIGINT REFERENCES lich_trinh,
  ma_phien_an_danh UUID NOT NULL,
  bat_dau          TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Q-022 = A (D-038, SA-017): trí nhớ hội thoại là cột của HOI_THOAI, vẫn 66 bảng (AI-015)
  trang_thai_chuyen_di JSONB NOT NULL DEFAULT '{"v": 1}' CHECK (jsonb_typeof(trang_thai_chuyen_di) = 'object'),
  phien_ban_trang_thai INT NOT NULL DEFAULT 0 CHECK (phien_ban_trang_thai >= 0),
  tom_tat              TEXT,
  ban_nhap_lich_trinh  JSONB,                      -- bản nháp của khách vãng lai, hết hạn 24 giờ
  ban_nhap_het_han     TIMESTAMPTZ,
  cap_nhat_luc         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((ban_nhap_lich_trinh IS NULL) = (ban_nhap_het_han IS NULL))
);
CREATE INDEX ix_hoi_thoai_phien ON hoi_thoai (ma_phien_an_danh);
CREATE INDEX ix_hoi_thoai_nguoi_dung ON hoi_thoai (ma_nguoi_dung) WHERE ma_nguoi_dung IS NOT NULL;

CREATE TABLE tin_nhan_chatbot (
  ma_tin_nhan  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_hoi_thoai BIGINT NOT NULL REFERENCES hoi_thoai,
  vai_tro      TEXT NOT NULL CHECK (vai_tro IN ('nguoi_dung','tro_ly')),
  noi_dung     TEXT NOT NULL,                     -- luôn là bản đã che thông tin cá nhân
  y_dinh       VARCHAR(30),
  bi_tu_choi   BOOLEAN NOT NULL DEFAULT FALSE,
  huu_ich      BOOLEAN,
  thoi_diem    TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Q-022 = A (SA-017): nhật ký, đề xuất, xem xét — mọi cột phụ thuộc trực tiếp ma_tin_nhan (3NF)
  khoa_gui           UUID,                        -- Idempotency-Key của tin người dùng
  pham_vi            TEXT CHECK (pham_vi IN ('trong_pham_vi','thieu_du_lieu','ngoai_pham_vi','khan_cap')),
  nguon_tra_loi      TEXT CHECK (nguon_tra_loi IN ('mo_hinh','quy_tac','mau')),
  phien_ban_prompt   VARCHAR(20),
  mo_hinh            VARCHAR(60),
  cong_cu            JSONB,
  kiem_tra           JSONB,
  trang_thai_luc_tra_loi JSONB,                   -- ảnh chụp trạng thái chuyến đi lúc trả lời
  do_tre_ms          INT CHECK (do_tre_ms >= 0),
  token_vao          INT CHECK (token_vao >= 0),
  token_vao_cache    INT CHECK (token_vao_cache >= 0),
  token_ra           INT CHECK (token_ra >= 0),
  ma_xac_nhan        UUID,                        -- mã đề xuất của trợ lý (128 bit ngẫu nhiên); khác DE_XUAT_SUA.ma_de_xuat
  de_xuat            JSONB,
  trang_thai_de_xuat TEXT CHECK (trang_thai_de_xuat IN ('cho','da_xac_nhan','bo_qua','het_han')),
  de_xuat_het_han    TIMESTAMPTZ,
  can_xem_xet        BOOLEAN NOT NULL DEFAULT FALSE,
  ly_do_xem_xet      TEXT[] CHECK (ly_do_xem_xet <@ ARRAY['bao_sai','kiem_tra_that_bai','khan_cap','nghi_chen_lenh',
                       'khong_huu_ich','thieu_du_lieu','ngoai_pham_vi_lap','dang_chu_y']::text[]),
  muc_xem_xet        SMALLINT CHECK (muc_xem_xet BETWEEN 1 AND 3),   -- 3 = cao
  trang_thai_xem_xet TEXT CHECK (trang_thai_xem_xet IN ('cho','da_xem','bo_qua')),
  nguyen_nhan        TEXT CHECK (nguyen_nhan IN ('thieu_du_lieu','du_lieu_sai','cong_cu_loi','mo_hinh_sai',
                       'prompt_chua_ro','ngoai_pham_vi_hop_le','nguoi_dung_hieu_nham','khac')),
  ghi_chu_qt         TEXT,
  ma_qt_xem_xet      BIGINT REFERENCES nguoi_dung ON DELETE SET NULL,
  xem_xet_luc        TIMESTAMPTZ,
  bao_sai_ly_do      TEXT CHECK (bao_sai_ly_do IN ('sai_thong_tin','sai_gia','khong_lien_quan','khong_phu_hop','khac')),
  CONSTRAINT ck_de_xuat_du CHECK (num_nonnulls(ma_xac_nhan, de_xuat, trang_thai_de_xuat, de_xuat_het_han) IN (0, 4)),
  CONSTRAINT ck_de_xuat_cua_tro_ly CHECK (vai_tro = 'tro_ly' OR (de_xuat IS NULL AND NOT can_xem_xet)),
  CONSTRAINT ck_khoa_gui_nguoi_dung CHECK (khoa_gui IS NULL OR vai_tro = 'nguoi_dung'),
  CONSTRAINT ck_xem_xet CHECK (can_xem_xet = (trang_thai_xem_xet IS NOT NULL)
                               AND (NOT can_xem_xet OR (muc_xem_xet IS NOT NULL AND cardinality(ly_do_xem_xet) > 0)))
);
CREATE UNIQUE INDEX ux_tin_nhan_xac_nhan ON tin_nhan_chatbot (ma_xac_nhan) WHERE ma_xac_nhan IS NOT NULL;
CREATE UNIQUE INDEX ux_tin_nhan_khoa_gui ON tin_nhan_chatbot (ma_hoi_thoai, khoa_gui) WHERE khoa_gui IS NOT NULL;
CREATE INDEX ix_tin_nhan_hoi_thoai ON tin_nhan_chatbot (ma_hoi_thoai, thoi_diem);
CREATE INDEX ix_tin_nhan_cho_xem ON tin_nhan_chatbot (muc_xem_xet DESC, thoi_diem)
  WHERE can_xem_xet AND trang_thai_xem_xet = 'cho';
CREATE INDEX ix_tin_nhan_thoi_diem ON tin_nhan_chatbot (thoi_diem);

-- ---------------------------------------------------------------------
-- ERD6 — Lịch trình nhóm (8 bảng)
-- ---------------------------------------------------------------------
CREATE TABLE loi_moi (
  ma_loi_moi    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  token         CHAR(32) NOT NULL UNIQUE,
  han_dung      TIMESTAMPTZ NOT NULL,
  trang_thai    TEXT NOT NULL DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong','thu_hoi','het_han'))
);

CREATE TABLE thanh_vien_lich_trinh (
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  vai_tro       TEXT NOT NULL DEFAULT 'thanh_vien' CHECK (vai_tro IN ('truong_nhom','thanh_vien')),
  ngay_ranh_tu  DATE,
  ngay_ranh_den DATE,
  ngan_sach     BIGINT,
  rang_buoc     TEXT,
  trang_thai    TEXT NOT NULL DEFAULT 'tham_gia' CHECK (trang_thai IN ('tham_gia','roi_nhom')),
  tham_gia_luc  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ma_lich_trinh, ma_nguoi_dung)
);

CREATE TABLE muc_muon_di (
  ma_lich_trinh BIGINT NOT NULL,
  ma_nguoi_dung BIGINT NOT NULL,
  ma_dia_diem   BIGINT NOT NULL REFERENCES dia_diem,
  muc_do        TEXT NOT NULL CHECK (muc_do IN ('rat_muon','muon','tuy')),
  PRIMARY KEY (ma_lich_trinh, ma_nguoi_dung, ma_dia_diem),
  FOREIGN KEY (ma_lich_trinh, ma_nguoi_dung) REFERENCES thanh_vien_lich_trinh
);

CREATE TABLE phien_binh_chon (
  ma_phien       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh  BIGINT NOT NULL REFERENCES lich_trinh,
  loai_doi_tuong TEXT NOT NULL CHECK (loai_doi_tuong IN ('dia_diem','cho_o')),
  han_chot       TIMESTAMPTZ NOT NULL,
  trang_thai     TEXT NOT NULL DEFAULT 'mo' CHECK (trang_thai IN ('mo','da_chot','da_huy'))
);

CREATE TABLE ung_vien_binh_chon (
  ma_ung_vien BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_phien    BIGINT NOT NULL REFERENCES phien_binh_chon,
  ma_dia_diem BIGINT REFERENCES dia_diem,
  ma_co_so    BIGINT REFERENCES co_so_luu_tru,
  CHECK (num_nonnulls(ma_dia_diem, ma_co_so) = 1)
);

CREATE TABLE phieu_bau (
  ma_ung_vien   BIGINT NOT NULL REFERENCES ung_vien_binh_chon,
  ma_lich_trinh BIGINT NOT NULL,
  ma_nguoi_dung BIGINT NOT NULL,
  lua_chon      TEXT NOT NULL CHECK (lua_chon IN ('dong_y','khong','tuy')),
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ma_ung_vien, ma_lich_trinh, ma_nguoi_dung),
  FOREIGN KEY (ma_lich_trinh, ma_nguoi_dung) REFERENCES thanh_vien_lich_trinh
);

CREATE TABLE de_xuat_sua (
  ma_de_xuat    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  noi_dung      TEXT NOT NULL,
  qua_tro_ly    BOOLEAN NOT NULL DEFAULT FALSE,   -- W16 hiện nguồn "qua trợ lý" (X5, SA-017)
  trang_thai    TEXT NOT NULL DEFAULT 'cho_duyet' CHECK (trang_thai IN ('cho_duyet','chap_nhan','tu_choi')),
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE binh_luan (
  ma_binh_luan  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_lich_trinh BIGINT NOT NULL REFERENCES lich_trinh,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_muc        BIGINT REFERENCES muc_lich_trinh,
  noi_dung      TEXT NOT NULL,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- ERD7 — Đánh giá, báo cáo (8 bảng)
-- ---------------------------------------------------------------------
CREATE TABLE danh_gia (
  ma_danh_gia   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_co_so      BIGINT REFERENCES co_so_luu_tru,
  ma_dia_diem   BIGINT REFERENCES dia_diem,
  so_sao        SMALLINT NOT NULL CHECK (so_sao BETWEEN 1 AND 5),
  nhan_xet      TEXT,
  thang_di      DATE,
  trang_thai    TEXT NOT NULL DEFAULT 'hien' CHECK (trang_thai IN ('hien','an')),
  ly_do_an      TEXT,
  tao_luc       TIMESTAMPTZ NOT NULL DEFAULT now(),
  sua_luc       TIMESTAMPTZ,
  CHECK (num_nonnulls(ma_co_so, ma_dia_diem) = 1)
);
CREATE UNIQUE INDEX ux_danh_gia_mot_lan ON danh_gia (ma_nguoi_dung, coalesce(ma_co_so, 0), coalesce(ma_dia_diem, 0));

CREATE TABLE tieu_chi_danh_gia (
  ma_tieu_chi SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ten         VARCHAR(60) NOT NULL,
  ap_dung     TEXT NOT NULL CHECK (ap_dung IN ('cho_o','dia_diem'))
);

CREATE TABLE diem_tieu_chi (
  ma_danh_gia BIGINT   NOT NULL REFERENCES danh_gia,
  ma_tieu_chi SMALLINT NOT NULL REFERENCES tieu_chi_danh_gia,
  diem        SMALLINT NOT NULL CHECK (diem BETWEEN 1 AND 5),
  PRIMARY KEY (ma_danh_gia, ma_tieu_chi)
);

CREATE TABLE anh_danh_gia (
  ma_anh      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_danh_gia BIGINT NOT NULL REFERENCES danh_gia,
  url         VARCHAR(500) NOT NULL
);

CREATE TABLE luot_huu_ich (
  ma_danh_gia   BIGINT NOT NULL REFERENCES danh_gia,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ma_danh_gia, ma_nguoi_dung)
);

CREATE TABLE bao_cao_danh_gia (
  ma_bao_cao    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_danh_gia   BIGINT NOT NULL REFERENCES danh_gia,
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ly_do         VARCHAR(200) NOT NULL,
  trang_thai    TEXT NOT NULL DEFAULT 'cho_xu_ly' CHECK (trang_thai IN ('cho_xu_ly','da_an','bo_qua'))
);

CREATE TABLE xac_nhan_da_den (
  ma_nguoi_dung BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_dia_diem   BIGINT NOT NULL REFERENCES dia_diem,
  thoi_diem     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ma_nguoi_dung, ma_dia_diem)
);

CREATE TABLE bao_cao_sai (
  ma_bao_cao_sai BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ma_nguoi_dung  BIGINT NOT NULL REFERENCES nguoi_dung,
  ma_co_so       BIGINT REFERENCES co_so_luu_tru,
  ma_dia_diem    BIGINT REFERENCES dia_diem,
  loai_loi       TEXT NOT NULL CHECK (loai_loi IN ('sai_thong_tin','sai_gia','link_ota_hong','da_dong_cua','khac')),
  ghi_chu        TEXT,
  anh            VARCHAR(500),
  trang_thai     TEXT NOT NULL DEFAULT 'cho_xu_ly' CHECK (trang_thai IN ('cho_xu_ly','da_sua','bo_qua')),
  ma_qt_xu_ly    BIGINT REFERENCES nguoi_dung,
  ket_qua        TEXT,
  tao_luc        TIMESTAMPTZ NOT NULL DEFAULT now(),
  xu_ly_luc      TIMESTAMPTZ,
  CHECK (num_nonnulls(ma_co_so, ma_dia_diem) = 1)
);

-- ---------------------------------------------------------------------
-- Trigger nơi nghỉ từng đêm (base/02 mục 6.1; D-039a; SA-018)
-- ---------------------------------------------------------------------
-- Kiểm khi ghi NGAY_LICH_TRINH: nơi nghỉ (dự kiến hoặc đã đặt) phải cùng tỉnh với lịch trình;
-- chỗ ở đã đặt phải thuộc đúng lịch trình, đang 'da_dat' và phủ đêm đó.
CREATE FUNCTION fn_kiem_tra_dem_nghi() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c cho_o_cua_toi%ROWTYPE;
BEGIN
  IF NEW.ma_co_so_nghi IS NOT NULL AND NOT EXISTS (
       SELECT 1 FROM co_so_luu_tru cs JOIN lich_trinh lt ON lt.ma_tinh = cs.ma_tinh
       WHERE cs.ma_co_so = NEW.ma_co_so_nghi AND lt.ma_lich_trinh = NEW.ma_lich_trinh) THEN
    RAISE EXCEPTION 'Nơi nghỉ phải cùng tỉnh với lịch trình' USING ERRCODE = '23514';
  END IF;
  IF NEW.ma_cho_o IS NOT NULL THEN
    SELECT * INTO c FROM cho_o_cua_toi WHERE ma_cho_o = NEW.ma_cho_o;
    IF c.trang_thai <> 'da_dat' OR c.ma_lich_trinh IS DISTINCT FROM NEW.ma_lich_trinh
       OR NEW.ngay < c.ngay_nhan OR NEW.ngay >= c.ngay_tra THEN
      RAISE EXCEPTION 'Chỗ ở đã đặt không phủ đêm này của lịch trình' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_kiem_tra_dem_nghi BEFORE INSERT OR UPDATE OF ma_co_so_nghi, ma_cho_o, ngay ON ngay_lich_trinh
  FOR EACH ROW EXECUTE FUNCTION fn_kiem_tra_dem_nghi();

-- Đồng bộ khi chỗ ở tự khai được gắn, huỷ, đổi ngày hoặc đổi lịch trình:
--  1) đêm không còn được phủ (kể cả khi chỗ ở bị gỡ khỏi lịch trình: ma_lich_trinh → NULL, B-036) → bỏ cả nơi nghỉ;
--  2) đêm được phủ → chỗ ở đã đặt THẮNG nơi nghỉ dự kiến, kể cả khác cơ sở.
CREATE FUNCTION fn_dong_bo_dem_nghi() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  UPDATE ngay_lich_trinh n SET ma_cho_o = NULL, ma_co_so_nghi = NULL
   WHERE n.ma_cho_o = NEW.ma_cho_o
     AND NOT (NEW.trang_thai = 'da_dat' AND NEW.ma_lich_trinh IS NOT NULL AND n.ma_lich_trinh = NEW.ma_lich_trinh
              AND n.ngay >= NEW.ngay_nhan AND n.ngay < NEW.ngay_tra);
  IF NEW.trang_thai = 'da_dat' AND NEW.ma_lich_trinh IS NOT NULL THEN
    UPDATE ngay_lich_trinh n SET ma_cho_o = NEW.ma_cho_o, ma_co_so_nghi = NEW.ma_co_so
     WHERE n.ma_lich_trinh = NEW.ma_lich_trinh AND n.ngay >= NEW.ngay_nhan AND n.ngay < NEW.ngay_tra
       AND (n.ma_cho_o IS DISTINCT FROM NEW.ma_cho_o OR n.ma_co_so_nghi IS DISTINCT FROM NEW.ma_co_so);
  END IF;
  RETURN NULL;
END $$;

CREATE TRIGGER trg_dong_bo_dem_nghi AFTER INSERT OR UPDATE OF trang_thai, ngay_nhan, ngay_tra, ma_lich_trinh, ma_co_so
  ON cho_o_cua_toi FOR EACH ROW EXECUTE FUNCTION fn_dong_bo_dem_nghi();
