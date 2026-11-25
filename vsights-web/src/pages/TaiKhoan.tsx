import { useAuth } from '../auth/AuthContext';
import { getAccessToken } from '../api/client';

// W20 (rút gọn) — chứng minh gọi được API cần JWT: GET /auth/me.

export function TaiKhoan() {
  const { nguoiDung } = useAuth();
  if (!nguoiDung) return null;
  const token = getAccessToken();

  return (
    <main className="khung" style={{ padding: '48px var(--le-trang) 96px', maxWidth: 760 }}>
      <p className="nhan-in-hoa">Tài khoản</p>
      <h1 style={{ fontSize: 34, margin: '8px 0 28px' }}>{nguoiDung.ho_ten || 'Tài khoản của bạn'}</h1>
      <dl className="the" style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: '12px 16px', margin: 0 }}>
        <dt className="phu">Email</dt>
        <dd style={{ margin: 0 }}>{nguoiDung.email ?? 'Chưa có (đăng nhập bằng Zalo)'}</dd>
        <dt className="phu">Vai trò</dt>
        <dd style={{ margin: 0 }}>{nguoiDung.vai_tro === 'quan_tri' ? 'Quản trị viên' : 'Du khách'}</dd>
        <dt className="phu">Email đã xác thực</dt>
        <dd style={{ margin: 0 }}>{nguoiDung.email_da_xac_thuc ? 'Có' : 'Chưa'}</dd>
        <dt className="phu">Tạo lúc</dt>
        <dd style={{ margin: 0 }}>{nguoiDung.tao_luc ? new Date(nguoiDung.tao_luc).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }) : '—'}</dd>
      </dl>
      <div className="the" style={{ marginTop: 20, background: 'var(--nen-nhat)' }}>
        <p className="nhan-in-hoa" style={{ marginTop: 0 }}>Phiên đăng nhập (minh chứng kỹ thuật)</p>
        <p style={{ margin: '0 0 6px', fontSize: 14 }}>
          Access token giữ trong bộ nhớ: <code>{token ? `${token.slice(0, 16)}…` : 'không có'}</code>
        </p>
        <p className="phu" style={{ margin: 0 }}>
          Refresh token nằm trong cookie HttpOnly <code>vs_refresh</code>: JavaScript không đọc được. Tải lại trang để thấy phiên được khôi phục qua
          <code> POST /auth/refresh</code>.
        </p>
      </div>
    </main>
  );
}
