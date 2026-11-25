import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';

// W22/M22 — Đăng nhập (UC01). Gọi POST /auth/login; refresh token về cookie HttpOnly.

function thongBaoDangNhap(loi: unknown): string {
  if (!(loi instanceof ApiError)) return 'Đã có lỗi không mong muốn. Vui lòng thử lại.';
  switch (loi.maLoi) {
    case 'SAI_THONG_TIN':
      return 'Email hoặc mật khẩu chưa đúng.';
    case 'EMAIL_CHUA_XAC_THUC':
      return 'Email chưa được xác thực. Mở thư Vsights đã gửi để xác thực rồi đăng nhập lại.';
    case 'TAI_KHOAN_BI_KHOA':
      return 'Tài khoản đang bị khoá. Liên hệ quản trị viên.';
    case 'NGUON_KHONG_HOP_LE':
      return 'Trang này chưa được máy chủ cho phép (Origin). Kiểm tra VS_CORS_ORIGINS của backend.';
    case 'THU_QUA_NHIEU_LAN': {
      const phut = loi.retryAfter ? Math.ceil(loi.retryAfter / 60) : 15;
      return `Bạn đã thử quá nhiều lần. Thử lại sau ${phut} phút.`;
    }
    default:
      return loi.thongBao;
  }
}

/** Lỗi 422 theo trường: chi_tiet có thể là [{truong, thong_bao}] hoặc dạng loc/msg của FastAPI. */
function loiTheoTruong(loi: unknown): Record<string, string> {
  if (!(loi instanceof ApiError) || loi.status !== 422 || !Array.isArray(loi.chiTiet)) return {};
  const kq: Record<string, string> = {};
  for (const muc of loi.chiTiet as Array<Record<string, unknown>>) {
    const truong = (muc.truong as string) ?? (Array.isArray(muc.loc) ? String(muc.loc[muc.loc.length - 1]) : '');
    const tb = (muc.thong_bao as string) ?? (muc.msg as string) ?? 'Giá trị chưa hợp lệ';
    if (truong) kq[truong] = tb;
  }
  return kq;
}

export function DangNhap() {
  const { nguoiDung, dangNhap } = useAuth();
  const dieuHuong = useNavigate();
  const viTri = useLocation();
  const veLai = (viTri.state as { tu?: string } | null)?.tu ?? '/dia-diem';

  const [email, setEmail] = useState('');
  const [matKhau, setMatKhau] = useState('');
  const [dangGui, setDangGui] = useState(false);
  const [loi, setLoi] = useState<unknown>(null);

  if (nguoiDung) return <Navigate to={veLai} replace />;

  const guiForm = async (e: FormEvent) => {
    e.preventDefault();
    setDangGui(true);
    setLoi(null);
    try {
      await dangNhap(email.trim(), matKhau);
      dieuHuong(veLai, { replace: true });
    } catch (err) {
      setLoi(err);
    } finally {
      setDangGui(false);
    }
  };

  const loiTruong = loiTheoTruong(loi);
  const loiChung = loi && Object.keys(loiTruong).length === 0 ? thongBaoDangNhap(loi) : null;

  return (
    <main className="khung" style={{ display: 'grid', placeItems: 'center', minHeight: 'calc(100vh - 73px)' }}>
      <div style={{ width: '100%', maxWidth: 420, padding: '48px 0' }}>
        <p className="nhan-in-hoa">Tài khoản Vsights</p>
        <h1 style={{ fontSize: 34, lineHeight: 1.1, margin: '8px 0 28px' }}>Đăng nhập</h1>

        {loiChung && (
          <div className="dai-thong-bao" role="alert" style={{ marginBottom: 16 }}>
            {loiChung}
          </div>
        )}

        <form onSubmit={guiForm} noValidate>
          <div className="truong">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="o-nhap"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!loiTruong.email}
            />
            {loiTruong.email && <span className="loi-truong">{loiTruong.email}</span>}
          </div>
          <div className="truong">
            <label htmlFor="mat_khau">Mật khẩu</label>
            <input
              id="mat_khau"
              className="o-nhap"
              type="password"
              autoComplete="current-password"
              required
              value={matKhau}
              onChange={(e) => setMatKhau(e.target.value)}
              aria-invalid={!!loiTruong.mat_khau}
            />
            {loiTruong.mat_khau && <span className="loi-truong">{loiTruong.mat_khau}</span>}
          </div>
          <button className="nut nut-chinh" type="submit" disabled={dangGui || !email || !matKhau} style={{ width: '100%', marginTop: 8 }}>
            {dangGui ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
        </form>

        <p className="phu" style={{ marginTop: 20 }}>
          Đăng nhập bằng Google, Zalo và "Tiếp tục với tư cách khách": đã thiết kế, chưa cài đặt trong khung này (D-030).
        </p>
      </div>
    </main>
  );
}
