import { ThanChat } from '../components/ChatMount';

// W12/M12 — trang Trợ lý (UX-012). Thân khung chat do AI làm ở P4; trang này chỉ giữ chỗ trong bố cục.
export function TroLy() {
  return (
    <main className="khung trang" style={{ maxWidth: 760 }}>
      <div className="the" style={{ padding: 0 }}>
        <ThanChat />
      </div>
    </main>
  );
}
