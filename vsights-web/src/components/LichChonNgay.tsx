import { useMemo, useState } from 'react';
import { HopNoi } from './HopNoi';
import { cungNgay, homNay, khoangNgay, ngayNgan, soNgayGiua, TEN_THU_LICH } from '../utils/ngay';

// CLich — chọn ngày nhận, trả trên lịch (NFR-06): không có ô gõ ngày. Tối đa 30 đêm (QUA_SO_DEM), không chọn ngày đã qua.
const TOI_DA_DEM = 30;

function NgayCuaThang(nam: number, thang: number): (Date | null)[] {
  const dau = new Date(nam, thang, 1);
  const lech = (dau.getDay() + 6) % 7; // tuần bắt đầu T2
  const soNgay = new Date(nam, thang + 1, 0).getDate();
  const o: (Date | null)[] = Array.from({ length: lech }, () => null);
  for (let i = 1; i <= soNgay; i++) o.push(new Date(nam, thang, i));
  return o;
}

export function LichChonNgay({
  nhan: nhanDau,
  tra: traDau,
  xong,
  dong,
}: {
  nhan: Date | null;
  tra: Date | null;
  xong: (nhan: Date, tra: Date) => void;
  dong: () => void;
}) {
  const h = homNay();
  const [nhan, setNhan] = useState<Date | null>(nhanDau);
  const [tra, setTra] = useState<Date | null>(traDau);
  const goc = nhanDau ?? h;
  const [thangDau, setThangDau] = useState(new Date(goc.getFullYear(), goc.getMonth(), 1));
  const thang2 = new Date(thangDau.getFullYear(), thangDau.getMonth() + 1, 1);

  const chon = (d: Date) => {
    if (!nhan || tra || d <= nhan) {
      setNhan(d);
      setTra(null);
    } else {
      setTra(d);
    }
  };

  const camNgay = (d: Date) => {
    if (d < h) return true;
    if (nhan && !tra && d > nhan && soNgayGiua(nhan, d) > TOI_DA_DEM) return true;
    return false;
  };

  const thangs = useMemo(() => [thangDau, thang2], [thangDau, thang2]);
  const coTheLui = thangDau > new Date(h.getFullYear(), h.getMonth(), 1);

  return (
    <HopNoi
      tieuDe="Chọn ngày nhận, trả phòng"
      dong={dong}
      chan={
        <>
          <span className="phu" style={{ marginRight: 'auto', alignSelf: 'center' }} aria-live="polite">
            {nhan && tra ? khoangNgay(nhan, tra) : nhan ? `Nhận ${ngayNgan(nhan)} · chọn ngày trả` : 'Chọn ngày nhận phòng'}
          </span>
          <button type="button" className="nut nut-chinh nut-nho" disabled={!nhan || !tra} onClick={() => nhan && tra && xong(nhan, tra)}>
            Xong
          </button>
        </>
      }
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <button type="button" className="nut-chu" disabled={!coTheLui} onClick={() => setThangDau(new Date(thangDau.getFullYear(), thangDau.getMonth() - 1, 1))}>
          ‹ Tháng trước
        </button>
        <button type="button" className="nut-chu" onClick={() => setThangDau(new Date(thangDau.getFullYear(), thangDau.getMonth() + 1, 1))}>
          Tháng sau ›
        </button>
      </div>
      <div className="lich">
        {thangs.map((t) => (
          <div className="lich-thang" key={t.toISOString()}>
            <h3>
              Tháng {t.getMonth() + 1}/{t.getFullYear()}
            </h3>
            <div className="lich-luoi">
              {TEN_THU_LICH.map((x) => (
                <div className="lich-thu" key={x}>
                  {x}
                </div>
              ))}
              {NgayCuaThang(t.getFullYear(), t.getMonth()).map((d, i) =>
                d ? (
                  <button
                    key={i}
                    type="button"
                    className={[
                      'lich-ngay',
                      cungNgay(d, nhan) ? 'dau' : '',
                      cungNgay(d, tra) ? 'cuoi' : '',
                      nhan && tra && d > nhan && d < tra ? 'trong-khoang' : '',
                    ].join(' ')}
                    disabled={camNgay(d)}
                    aria-pressed={cungNgay(d, nhan) || cungNgay(d, tra)}
                    aria-label={ngayNgan(d)}
                    onClick={() => chon(d)}
                  >
                    {d.getDate()}
                  </button>
                ) : (
                  <span key={i} />
                ),
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="phu" style={{ marginTop: 12 }}>
        Mỗi lần ở tối đa {TOI_DA_DEM} đêm.
      </p>
    </HopNoi>
  );
}
