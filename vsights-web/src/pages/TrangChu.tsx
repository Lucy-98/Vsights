import { Link, useNavigate } from 'react-router-dom';
import { OTim, type DieuKienCoBan } from '../components/OTim';

// W01/M01 — Trang chủ: tìm chỗ ở theo tỉnh, dải ngày, số người, ngân sách (UC02). Mở cho khách vãng lai.
export function thamSoTim(dk: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(dk)) {
    if (Array.isArray(v)) v.forEach((x) => p.append(k, String(x)));
    else if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  }
  return p.toString();
}

export function TrangChu() {
  const dieuHuong = useNavigate();
  const gui = (dk: DieuKienCoBan) => dieuHuong(`/cho-o?${thamSoTim(dk)}`);

  return (
    <main>
      <section style={{ background: 'linear-gradient(180deg, #E8EEF5 0%, #F8FAFC 100%)', padding: 'clamp(40px, 8vw, 96px) 0 48px' }}>
        <div className="khung">
          <p className="nhan-in-hoa">Vsights · du lịch trong nước</p>
          <h1 style={{ fontSize: 'clamp(34px, 5.4vw, 64px)', lineHeight: 1.04, margin: '10px 0 14px', maxWidth: 820 }}>
            Tìm chỗ ở và so giá tham khảo trên nhiều trang
          </h1>
          <p style={{ fontSize: 17, color: 'var(--chu-vua)', margin: '0 0 28px', maxWidth: 640 }}>
            Vsights gom giá tham khảo từ Agoda, Booking.com, Traveloka, so giá đã gồm thuế, phí rồi đưa bạn sang trang của OTA. Vsights không nhận đặt chỗ.
          </p>
          <OTim gui={gui} />
        </div>
      </section>
      <section className="khung" style={{ padding: '40px var(--le-trang) 120px' }}>
        <div className="luoi-the" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
          <div className="the">
            <p className="nhan-in-hoa" style={{ marginTop: 0 }}>Giá đã gồm thuế, phí</p>
            <p style={{ margin: 0 }}>Giá Booking.com được quy đổi +15% thuế, phí trước khi so. Giá chưa gồm thuế, phí mà không quy đổi được thì hiện riêng, không dùng để so.</p>
          </div>
          <div className="the">
            <p className="nhan-in-hoa" style={{ marginTop: 0 }}>Giá từng đêm</p>
            <p style={{ margin: 0 }}>Mở một chỗ ở để xem giá từng đêm trên mỗi trang và khoảng ngày rẻ hơn gần ngày bạn chọn.</p>
          </div>
          <div className="the">
            <p className="nhan-in-hoa" style={{ marginTop: 0 }}>Điểm tham quan, quán ăn</p>
            <p style={{ margin: 0 }}>
              Xem địa điểm theo tỉnh ở trang <Link to="/dia-diem">Khám phá</Link>.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
