import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { dangNhap as apiDangNhap, dangXuat as apiDangXuat, khoiPhucPhien, layToi, type NguoiDung } from '../api/auth';
import { onTokenChange } from '../api/client';

interface AuthState {
  nguoiDung: NguoiDung | null;
  dangKiemTra: boolean; // đang khôi phục phiên lúc mở trang
  dangNhap: (email: string, matKhau: string) => Promise<void>;
  dangXuat: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [nguoiDung, setNguoiDung] = useState<NguoiDung | null>(null);
  const [dangKiemTra, setDangKiemTra] = useState(true);

  // Mở trang / tải lại: thử dùng cookie refresh để lấy access token mới.
  useEffect(() => {
    let huy = false;
    (async () => {
      try {
        if (await khoiPhucPhien()) {
          const toi = await layToi();
          if (!huy) setNguoiDung(toi);
        }
      } catch {
        /* chưa đăng nhập: bỏ qua */
      } finally {
        if (!huy) setDangKiemTra(false);
      }
    })();
    // Làm mới thất bại (phiên bị thu hồi) thì đưa về trạng thái chưa đăng nhập.
    const bo = onTokenChange((t) => {
      if (!t) setNguoiDung(null);
    });
    return () => {
      huy = true;
      bo();
    };
  }, []);

  const dangNhap = useCallback(async (email: string, matKhau: string) => {
    await apiDangNhap(email, matKhau);
    setNguoiDung(await layToi());
  }, []);

  const dangXuat = useCallback(async () => {
    await apiDangXuat();
    setNguoiDung(null);
  }, []);

  const value = useMemo(
    () => ({ nguoiDung, dangKiemTra, dangNhap, dangXuat }),
    [nguoiDung, dangKiemTra, dangNhap, dangXuat],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth phải nằm trong AuthProvider');
  return ctx;
}
