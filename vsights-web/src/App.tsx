import { Link, Route, Routes } from 'react-router-dom';
import { ChatMount } from './components/ChatMount';
import { Header, ThanhTab } from './components/Header';
import { YeuCauDangNhap } from './components/YeuCauDangNhap';
import { ChiTietChoO } from './pages/ChiTietChoO';
import { DangNhap } from './pages/DangNhap';
import { DiaDiem } from './pages/DiaDiem';
import { KetQua } from './pages/KetQua';
import { TaiKhoan } from './pages/TaiKhoan';
import { TrangChu } from './pages/TrangChu';
import { TroLy } from './pages/TroLy';

function KhongTimThay() {
  return (
    <main className="khung trang">
      <h1 style={{ fontSize: 34, marginBottom: 12 }}>Không tìm thấy trang</h1>
      <Link to="/">Về trang chủ</Link>
    </main>
  );
}

export function App() {
  return (
    <>
      <a href="#noi-dung" className="nut-chu" style={{ position: 'absolute', left: -9999 }} onFocus={(e) => (e.currentTarget.style.left = '8px')} onBlur={(e) => (e.currentTarget.style.left = '-9999px')}>
        Bỏ qua tới nội dung
      </a>
      <Header />
      <div id="noi-dung">
        <Routes>
          <Route path="/" element={<TrangChu />} />
          <Route path="/cho-o" element={<KetQua />} />
          <Route path="/cho-o/:ma" element={<ChiTietChoO />} />
          <Route path="/dia-diem" element={<DiaDiem />} />
          <Route path="/tro-ly" element={<TroLy />} />
          <Route path="/dang-nhap" element={<DangNhap />} />
          <Route
            path="/tai-khoan"
            element={
              <YeuCauDangNhap>
                <TaiKhoan />
              </YeuCauDangNhap>
            }
          />
          <Route path="*" element={<KhongTimThay />} />
        </Routes>
      </div>
      <ChatMount />
      <ThanhTab />
    </>
  );
}
