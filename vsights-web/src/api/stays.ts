import { api } from './client';

// Hợp đồng theo vsights-api 0.6.3: services/tim_kiem.py (GET /stays/search) và services/hop_dong.py
// (ChiTietChoO cho GET /stays/{ma}). Đổi tên trường ở backend thì chỉ sửa tệp này.

export type LoaiHinh = 'khach_san' | 'homestay' | 'resort' | 'can_ho' | 'nha_nghi';
export type LoaiNganSach = 'moi_dem' | 'ca_chuyen';
export type SapXep = 'phu_hop' | 'gia_tang' | 'danh_gia';

export const TEN_LOAI_HINH: Record<LoaiHinh, string> = {
  khach_san: 'Khách sạn',
  homestay: 'Homestay',
  resort: 'Resort',
  can_ho: 'Căn hộ',
  nha_nghi: 'Nhà nghỉ',
};

export interface DieuKienTim {
  ma_tinh: number;
  ngay_nhan: string; // YYYY-MM-DD
  ngay_tra: string;
  so_nguoi: number;
  so_phong: number;
  ngan_sach?: number;
  loai_ngan_sach?: LoaiNganSach;
  loai_hinh?: LoaiHinh;
  ma_tien_nghi?: number[];
  ma_so_thich?: number[];
  sap_xep?: SapXep;
  trang?: number;
  kich_thuoc?: number;
}

export interface GiaNgoaiPhepSo {
  ten_ota: string;
  ma_lien_ket: number;
  ma_loai_phong: number;
  ten_loai_phong: string;
  tong_chua_gom_thue_phi: number;
  gom_thue_phi: false;
  so_sanh_duoc: false;
  nhan: string; // "chưa gồm thuế, phí · không so"
  cap_nhat_gia: string | null;
}

export interface KetQuaChoO {
  ma_co_so: number;
  ten: string;
  loai_hinh: LoaiHinh;
  dia_chi: string | null;
  khu_vuc: string | null;
  hang_sao: number | null;
  diem_danh_gia: number | null;
  so_luot_danh_gia: number;
  so_thich_khop: number;
  so_lua_chon: number;
  la_du_lieu_mau: boolean;
  re_nhat: {
    ma_loai_phong: number;
    ten_loai_phong: string;
    ten_ota: string;
    ma_lien_ket: number;
    tong_ca_chuyen: number;
    gia_tb_moi_dem_moi_phong: number;
    gom_thue_phi: true;
    gia_goc_gom_thue_phi: boolean; // false = Booking.com đã quy đổi +15%
    cap_nhat_gia: string | null;
  };
  gia_ngoai_phep_so: GiaNgoaiPhepSo[];
}

export interface GoiYNoi {
  dieu_kien: 'ma_tien_nghi' | 'ngan_sach' | 'loai_hinh' | 'ngay_nhan' | 'ma_tinh';
  gia_tri: number | null | { ngay_nhan: string; ngay_tra: string };
  nhan: string;
  so_ket_qua: number | null;
}

export interface TrangKetQua {
  items: KetQuaChoO[];
  tong: number;
  trang: number;
  kich_thuoc: number;
  so_dem: number;
  ghi_chu: string;
  goi_y_noi_dieu_kien: GoiYNoi[];
}

export function timChoO(dk: DieuKienTim, signal?: AbortSignal): Promise<TrangKetQua> {
  return api<TrangKetQua>('/stays/search', { query: { ...dk }, signal });
}

// ---- Chi tiết (hop_dong.ChiTietChoO) ----
export interface GiaDem {
  ngay: string;
  gia_dem: number;
}
export interface GiaOta {
  ma_lien_ket: number;
  ten_ota: string;
  url: string;
  gom_thue_phi_goc: boolean;
  so_sanh_duoc: boolean;
  nhan_thue_phi: string;
  du_dem: boolean;
  dem: GiaDem[];
  tong_ca_chuyen: number | null;
  cap_nhat_gia: string | null;
  gia_cu: boolean;
  xep_hang_gia: number | null;
}
export interface LoaiPhongGia {
  ma_loai_phong: number;
  ten_loai_phong: string;
  loai_giuong: string | null;
  suc_chua_nl: number;
  suc_chua_te: number;
  du_suc_chua: boolean;
  dien_tich: number | null;
  co_bua_sang: boolean;
  thanh_toan_tai_cho: boolean | null;
  so_ngay_huy_mien_phi: number | null;
  dieu_kien_huy: string | null;
  tien_nghi: string[];
  gia_theo_ota: GiaOta[];
}
export interface KhoangNgay {
  ngay_nhan: string;
  ngay_tra: string;
  tong_ca_chuyen: number;
}
export interface ChiTietChoO {
  ma_co_so: number;
  ma_tinh: number;
  ten: string;
  loai_hinh: LoaiHinh;
  dia_chi: string | null;
  khu_vuc: string | null;
  hang_sao: number | null;
  vi_do: number | null;
  kinh_do: number | null;
  diem_danh_gia: number | null;
  so_luot_danh_gia: number;
  la_du_lieu_mau: boolean;
  mo_ta: string | null;
  tien_nghi: string[];
  so_thich: string[];
  ngay_nhan: string | null;
  ngay_tra: string | null;
  so_dem: number | null;
  so_nguoi: number;
  so_phong: number;
  loai_phong: LoaiPhongGia[];
  re_nhat: [number, number] | null;
  ngay_re_hon: KhoangNgay[];
  ghi_chu: string;
}

export function layChiTiet(
  ma: number,
  q: { ngay_nhan?: string; ngay_tra?: string; so_nguoi?: number; so_phong?: number },
  signal?: AbortSignal,
): Promise<ChiTietChoO> {
  return api<ChiTietChoO>(`/stays/${ma}`, { query: q, signal });
}

// ---- Danh mục ----
export interface TienNghi {
  ma_tien_nghi: number;
  ten_tien_nghi: string;
  pham_vi?: 'co_so' | 'phong' | string;
}
export interface SoThich {
  ma_so_thich: number;
  ten: string;
  pham_vi?: string;
}
export const layTienNghi = () => api<TienNghi[]>('/catalog/amenities');
export const laySoThich = () => api<SoThich[]>('/catalog/interests');

/** Giá quá 3 ngày chưa cập nhật (BR-03) — dùng cho thẻ kết quả (trang chi tiết có cờ gia_cu từ API). */
export function giaCu(capNhat: string | null | undefined, bayGio = Date.now()): boolean {
  if (!capNhat) return false;
  return bayGio - new Date(capNhat).getTime() > 3 * 86400000;
}

/** Nhãn thuế phí cho giá đã so (D-021, D-035). */
export function nhanThuePhi(giaGocGomThuePhi: boolean): string {
  return giaGocGomThuePhi ? 'đã gồm thuế, phí' : 'đã quy đổi +15% thuế, phí';
}
