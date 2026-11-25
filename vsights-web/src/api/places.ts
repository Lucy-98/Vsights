import { api, type Trang } from './client';

export type NhomDiaDiem = 'tham_quan' | 'an_uong';

export interface TinhThanh {
  ma_tinh: number;
  ten_tinh: string;
  ma_vung?: number;
}

export interface DiaDiem {
  ma_dia_diem: number;
  ten: string;
  dia_chi?: string | null;
  loai?: { ten_loai: string; nhom: NhomDiaDiem } | null;
  muc_gia_nguoi_tu?: number | null;
  muc_gia_nguoi_den?: number | null;
  diem_tb?: number | null;
  so_luot_danh_gia?: number | null;
  la_du_lieu_mau?: boolean;
}

export interface BoLocDiaDiem {
  ma_tinh?: number;
  nhom?: NhomDiaDiem;
  q?: string;
  trang?: number;
  kich_thuoc?: number;
}

export function layTinhThanh(): Promise<TinhThanh[]> {
  return api<TinhThanh[]>('/catalog/provinces');
}

export function timDiaDiem(boLoc: BoLocDiaDiem): Promise<Trang<DiaDiem>> {
  return api<Trang<DiaDiem>>('/places', {
    query: { kich_thuoc: 12, ...boLoc } as Record<string, string | number | undefined>,
  });
}
