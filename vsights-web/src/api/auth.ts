import { api, refreshAccessToken, setAccessToken, type TokenResponse } from './client';

// Hợp đồng theo Cheat Sheet mục 8, khớp backend code/vsights-api (0.6). Nếu `/docs` của bản đang chạy
// khác tên trường, chỉ cần sửa trong file này.

export interface NguoiDung {
  ma_nguoi_dung: number;
  email: string | null; // rỗng với tài khoản đăng nhập Zalo (D-030, D-031)
  ho_ten: string;
  vai_tro: string; // 'du_khach' | 'quan_tri' ...
  email_da_xac_thuc: boolean;
  tao_luc: string;
}

export async function dangNhap(email: string, matKhau: string): Promise<void> {
  const data = await api<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, mat_khau: matKhau, thiet_bi: navigator.userAgent.slice(0, 120) },
    boQuaRefresh: true,
  });
  setAccessToken(data.access_token);
}

/** Khôi phục phiên sau khi tải lại trang: access token mất cùng bộ nhớ, cookie refresh vẫn còn. */
export async function khoiPhucPhien(): Promise<boolean> {
  return (await refreshAccessToken()) !== null;
}

export function layToi(): Promise<NguoiDung> {
  return api<NguoiDung>('/auth/me');
}

export async function dangXuat(): Promise<void> {
  try {
    await api<void>('/auth/logout', { method: 'POST', boQuaRefresh: true });
  } finally {
    setAccessToken(null);
  }
}
