import { ApiError } from '../api/client';

/** Dải thông báo lỗi trên cùng, kèm "Thử lại" (base/03 mục 8: lỗi mạng hoặc 5xx). */
export function DaiLoi({ loi, thuLai }: { loi: unknown; thuLai?: () => void }) {
  const thongBao =
    loi instanceof ApiError ? loi.thongBao : 'Đã có lỗi không mong muốn. Vui lòng thử lại.';
  return (
    <div className="dai-thong-bao" role="alert">
      <span>{thongBao}</span>
      {thuLai && (
        <button className="nut-chu" style={{ color: 'var(--canh-bao)' }} onClick={thuLai}>
          Thử lại
        </button>
      )}
    </div>
  );
}
