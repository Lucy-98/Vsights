import { useEffect, useRef, type ReactNode } from 'react';
import { BieuTuong } from './BieuTuong';

/** Hộp nổi ở máy tính, ngăn dưới ở điện thoại (UX-011). Esc / bấm nền để đóng; giữ tiêu điểm trong hộp. */
export function HopNoi({ tieuDe, dong, children, chan }: { tieuDe: string; dong: () => void; children: ReactNode; chan?: ReactNode }) {
  const hop = useRef<HTMLDivElement>(null);
  const dongRef = useRef(dong);
  dongRef.current = dong;
  // Chỉ chạy khi mở/đóng hộp (không theo mỗi lần vẽ lại), để tiêu điểm không nhảy khi người dùng bấm trong hộp.
  useEffect(() => {
    const truoc = document.activeElement as HTMLElement | null;
    hop.current?.focus();
    const phim = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        dongRef.current();
      }
    };
    const nut = hop.current;
    nut?.addEventListener('keydown', phim);
    const tran = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      nut?.removeEventListener('keydown', phim);
      document.body.style.overflow = tran;
      truoc?.focus();
    };
  }, []);
  return (
    <div className="lop-phu" onMouseDown={(e) => e.target === e.currentTarget && dong()}>
      <div className="hop-noi" role="dialog" aria-modal="true" aria-label={tieuDe} tabIndex={-1} ref={hop}>
        <div className="dau-hop">
          <h2 style={{ fontSize: 22 }}>{tieuDe}</h2>
          <button type="button" className="nut-dong" onClick={dong} aria-label="Đóng">
            <BieuTuong ten="dong" />
          </button>
        </div>
        {children}
        {chan && <div style={{ marginTop: 20, display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>{chan}</div>}
      </div>
    </div>
  );
}
