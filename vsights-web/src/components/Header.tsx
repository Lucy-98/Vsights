import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { BieuTuong } from './BieuTuong';

// Header web (W-xx, ≥ 768 px). Ở điện thoại (≤ 767 px) điều hướng chuyển xuống ThanhTab (UX-011).
const MUC = [
  { den: '/', ten: 'Chỗ ở', sapCo: false, dau: true },
  { den: '/dia-diem', ten: 'Khám phá', sapCo: false },
  { den: '/lich-trinh', ten: 'Lịch trình', sapCo: true },
  { den: '/tro-ly', ten: 'Trợ lý', sapCo: false },
];

export function Header() {
  const { nguoiDung, dangXuat } = useAuth();
  const dieuHuong = useNavigate();
  const { pathname } = useLocation();

  return (
    <header className="dau-trang">
      <div className="khung">
        <NavLink to="/" style={{ textDecoration: 'none', color: 'var(--mau-chinh)' }} aria-label="Vsights — trang chủ">
          <span style={{ font: '600 22px var(--font-tieu-de)', letterSpacing: '-0.02em' }}>Vsights</span>
        </NavLink>
        <nav aria-label="Điều hướng chính">
          {MUC.map((m) =>
            m.sapCo ? (
              <span key={m.ten} className="muc-nav" aria-disabled="true" title="Đang làm (T-027 đợt 2)">
                {m.ten}
              </span>
            ) : (
              <NavLink
                key={m.ten}
                to={m.den}
                end={m.dau}
                className={({ isActive }) => {
                  const choO = m.dau && pathname.startsWith('/cho-o');
                  return `muc-nav${isActive || choO ? ' active' : ''}`;
                }}
              >
                {m.ten}
              </NavLink>
            ),
          )}
        </nav>
        <div className="tai-khoan-dau">
          {nguoiDung ? (
            <>
              <NavLink to="/tai-khoan" className="nut-chu" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                {nguoiDung.ho_ten || nguoiDung.email}
              </NavLink>
              <button
                className="nut-chu"
                onClick={async () => {
                  await dangXuat();
                  dieuHuong('/dang-nhap');
                }}
              >
                Đăng xuất
              </button>
            </>
          ) : (
            <NavLink to="/dang-nhap" className="nut nut-vien nut-nho">
              Đăng nhập
            </NavLink>
          )}
        </div>
      </div>
    </header>
  );
}

/** Thanh tab dưới ở điện thoại — theo CTab của canvas: Khám phá · Lịch trình · Trợ lý · Của tôi · Tài khoản. */
export function ThanhTab() {
  const { nguoiDung } = useAuth();
  const { pathname } = useLocation();
  const lop = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '');
  return (
    <nav className="thanh-tab" aria-label="Điều hướng chính (điện thoại)">
      <NavLink to="/" end className={({ isActive }) => (isActive || /^\/(cho-o|dia-diem)/.test(pathname) ? 'active' : '')}>
        <BieuTuong ten="tim" />
        Khám phá
      </NavLink>
      <span aria-disabled="true" title="Đang làm (T-027 đợt 2)">
        <BieuTuong ten="lich" />
        Lịch trình
      </span>
      <NavLink to="/tro-ly" className={lop}>
        <BieuTuong ten="tro-ly" />
        Trợ lý
      </NavLink>
      <span aria-disabled="true" title="Đang làm (T-027 đợt 2)">
        <BieuTuong ten="cua-toi" />
        Của tôi
      </span>
      <NavLink to={nguoiDung ? '/tai-khoan' : '/dang-nhap'} className={lop}>
        <BieuTuong ten="tai-khoan" />
        Tài khoản
      </NavLink>
    </nav>
  );
}
