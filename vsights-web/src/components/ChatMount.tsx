import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BieuTuong } from './BieuTuong';

// UX-012 — điểm gắn giao diện chat. AI (P4, Lucy 20/11) thay phần THÂN (ThanChat) mà không đổi bố cục:
//  - ≥ 768 px: nút nổi "Hỏi trợ lý" góc phải dưới → ngăn chat bên phải rộng 420 px;
//  - ≤ 767 px: không có nút nổi, dùng tab "Trợ lý" → trang /tro-ly toàn màn;
//  - ngữ cảnh: ở W14 truyền { ma_lich_trinh } để trợ lý sửa đúng lịch trình (X3).
// Danh sách sửa giao diện chat: claude/UI_T025_SUA_GIAO_DIEN_CHATBOT.md.

export interface NguCanhChat {
  ma_lich_trinh?: number;
}

/** Phần thân khung chat — AI thay bằng giao diện thật ở P4. */
export function ThanChat({ nguCanh }: { nguCanh?: NguCanhChat }) {
  return (
    <div style={{ padding: 24, display: 'grid', gap: 12, alignContent: 'start' }} aria-live="polite">
      <p className="nhan-in-hoa" style={{ margin: 0 }}>Trợ lý Vsights</p>
      <h2 style={{ fontSize: 24 }}>Trợ lý đang được hoàn thiện</h2>
      <p className="phu" style={{ fontSize: 14, margin: 0 }}>
        Khung chat sẽ có ở bản sau. Trong lúc chờ, bạn dùng ô tìm kiếm ở trang Chỗ ở để tìm và so giá tham khảo.
      </p>
      {nguCanh?.ma_lich_trinh != null && <p className="phu">Ngữ cảnh: lịch trình {nguCanh.ma_lich_trinh}</p>}
      <Link to="/" className="nut nut-vien nut-nho" style={{ justifySelf: 'start' }}>
        Tìm chỗ ở
      </Link>
    </div>
  );
}

export function ChatMount({ nguCanh }: { nguCanh?: NguCanhChat }) {
  const [mo, setMo] = useState(false);
  const { pathname } = useLocation();
  if (pathname.startsWith('/tro-ly')) return null; // đã ở trang trợ lý
  return (
    <>
      {!mo && (
        <button type="button" className="nut nut-chinh nut-tro-ly" onClick={() => setMo(true)}>
          <BieuTuong ten="tro-ly" />
          Hỏi trợ lý
        </button>
      )}
      {mo && (
        <aside className="ngan-chat" aria-label="Trợ lý">
          <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '12px 12px 0' }}>
            <button type="button" className="nut-dong" aria-label="Đóng trợ lý" onClick={() => setMo(false)}>
              <BieuTuong ten="dong" />
            </button>
          </div>
          <ThanChat nguCanh={nguCanh} />
        </aside>
      )}
    </>
  );
}
