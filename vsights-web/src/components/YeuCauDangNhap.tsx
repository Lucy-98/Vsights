import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

/** Thao tác cần đăng nhập: mở màn đăng nhập, đăng nhập xong quay lại đúng chỗ (base/03 mục 5). */
export function YeuCauDangNhap({ children }: { children: ReactNode }) {
  const { nguoiDung, dangKiemTra } = useAuth();
  const viTri = useLocation();
  if (dangKiemTra) return <p className="khung phu" style={{ paddingTop: 40 }}>Đang kiểm tra phiên đăng nhập…</p>;
  if (!nguoiDung) return <Navigate to="/dang-nhap" replace state={{ tu: viTri.pathname }} />;
  return <>{children}</>;
}
