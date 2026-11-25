import { useEffect, useState, type FormEvent } from 'react';
import { layTinhThanh, type TinhThanh } from '../api/places';
import type { DieuKienTim, LoaiNganSach } from '../api/stays';
import { cuoiTuanToi, khoangNgay, sangIso, tuIso } from '../utils/ngay';
import { BieuTuong } from './BieuTuong';
import { HopNoi } from './HopNoi';
import { LichChonNgay } from './LichChonNgay';

// Ô tìm chỗ ở (W01/M01, W03 "Sửa điều kiện"). Ngày chỉ chọn trên lịch (NFR-06).
export type DieuKienCoBan = Pick<DieuKienTim, 'ma_tinh' | 'ngay_nhan' | 'ngay_tra' | 'so_nguoi' | 'so_phong' | 'ngan_sach' | 'loai_ngan_sach'>;

let boNhoTinh: TinhThanh[] | null = null;
export function useTinhThanh(): TinhThanh[] {
  const [ds, setDs] = useState<TinhThanh[]>(boNhoTinh ?? []);
  useEffect(() => {
    if (boNhoTinh) return;
    layTinhThanh()
      .then((x) => {
        boNhoTinh = x;
        setDs(x);
      })
      .catch(() => setDs([]));
  }, []);
  return ds;
}

function Dem({ nhan, gt, dat, min, max }: { nhan: string; gt: number; dat: (v: number) => void; min: number; max: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--vien)' }}>
      <span style={{ fontWeight: 500 }}>{nhan}</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
        <button type="button" className="nut-dong" aria-label={`Bớt ${nhan.toLowerCase()}`} disabled={gt <= min} onClick={() => dat(gt - 1)}>
          −
        </button>
        <b style={{ minWidth: 24, textAlign: 'center' }} aria-live="polite">
          {gt}
        </b>
        <button type="button" className="nut-dong" aria-label={`Thêm ${nhan.toLowerCase()}`} disabled={gt >= max} onClick={() => dat(gt + 1)}>
          +
        </button>
      </span>
    </div>
  );
}

export function OTim({ dau, gui, nhanNut = 'Tìm chỗ ở' }: { dau?: Partial<DieuKienCoBan>; gui: (dk: DieuKienCoBan) => void; nhanNut?: string }) {
  const tinh = useTinhThanh();
  const [cuoiNhan, cuoiTra] = cuoiTuanToi();
  const [maTinh, setMaTinh] = useState<number | ''>(dau?.ma_tinh ?? '');
  const [nhan, setNhan] = useState<Date>(tuIso(dau?.ngay_nhan) ?? cuoiNhan);
  const [tra, setTra] = useState<Date>(tuIso(dau?.ngay_tra) ?? cuoiTra);
  const [soNguoi, setSoNguoi] = useState(dau?.so_nguoi ?? 2);
  const [soPhong, setSoPhong] = useState(dau?.so_phong ?? 1);
  const [nganSach, setNganSach] = useState(dau?.ngan_sach ? String(dau.ngan_sach) : '');
  const [loaiNs, setLoaiNs] = useState<LoaiNganSach>(dau?.loai_ngan_sach ?? 'ca_chuyen');
  const [moLich, setMoLich] = useState(false);
  const [moKhach, setMoKhach] = useState(false);
  const [loi, setLoi] = useState('');

  const soNs = Number(nganSach.replace(/\D/g, '')) || undefined;

  const guiForm = (e: FormEvent) => {
    e.preventDefault();
    if (maTinh === '') {
      setLoi('Chọn tỉnh, thành bạn muốn đến.');
      return;
    }
    setLoi('');
    gui({
      ma_tinh: maTinh,
      ngay_nhan: sangIso(nhan),
      ngay_tra: sangIso(tra),
      so_nguoi: soNguoi,
      so_phong: soPhong,
      ngan_sach: soNs,
      loai_ngan_sach: soNs ? loaiNs : undefined,
    });
  };

  return (
    <>
      <form className="o-tim" onSubmit={guiForm} noValidate>
        <div className="truong">
          <label htmlFor="ot-tinh">Đi đâu</label>
          <select id="ot-tinh" className="o-nhap" value={maTinh} onChange={(e) => setMaTinh(e.target.value ? Number(e.target.value) : '')} aria-invalid={!!loi}>
            <option value="">Chọn tỉnh, thành</option>
            {tinh.map((t) => (
              <option key={t.ma_tinh} value={t.ma_tinh}>
                {t.ten_tinh}
              </option>
            ))}
          </select>
        </div>
        <div className="truong">
          <span className="nhan-truong" id="ot-ngay">Ngày nhận, trả phòng</span>
          <button type="button" className="nut-truong" aria-labelledby="ot-ngay" aria-describedby="ot-ngay-gt" onClick={() => setMoLich(true)}>
            <span id="ot-ngay-gt">{khoangNgay(nhan, tra)}</span>
            <BieuTuong ten="lich" co={18} />
          </button>
        </div>
        <div className="truong">
          <span className="nhan-truong" id="ot-khach">Khách</span>
          <button type="button" className="nut-truong" aria-labelledby="ot-khach" onClick={() => setMoKhach(true)}>
            {soNguoi} người · {soPhong} phòng
          </button>
        </div>
        <div className="truong">
          <label htmlFor="ot-ns">Ngân sách (không bắt buộc)</label>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              id="ot-ns"
              className="o-nhap"
              inputMode="numeric"
              placeholder="Ví dụ 1.500.000"
              value={soNs ? soNs.toLocaleString('vi-VN') : ''}
              onChange={(e) => setNganSach(e.target.value)}
              style={{ minWidth: 0 }}
            />
            <select className="o-nhap" aria-label="Ngân sách tính cho" value={loaiNs} onChange={(e) => setLoaiNs(e.target.value as LoaiNganSach)} style={{ width: 'auto' }}>
              <option value="ca_chuyen">cả chuyến</option>
              <option value="moi_dem">mỗi đêm</option>
            </select>
          </div>
        </div>
        <button className="nut nut-chinh" type="submit">
          <BieuTuong ten="tim" co={18} />
          {nhanNut}
        </button>
      </form>
      {loi && (
        <p className="loi-truong" role="alert" style={{ marginTop: 8 }}>
          {loi}
        </p>
      )}

      {moLich && (
        <LichChonNgay
          nhan={nhan}
          tra={tra}
          dong={() => setMoLich(false)}
          xong={(n, t) => {
            setNhan(n);
            setTra(t);
            setMoLich(false);
          }}
        />
      )}
      {moKhach && (
        <HopNoi
          tieuDe="Số người, số phòng"
          dong={() => setMoKhach(false)}
          chan={
            <button type="button" className="nut nut-chinh nut-nho" onClick={() => setMoKhach(false)}>
              Xong
            </button>
          }
        >
          <Dem nhan="Người" gt={soNguoi} min={Math.max(1, soPhong)} max={60} dat={setSoNguoi} />
          <Dem nhan="Phòng" gt={soPhong} min={1} max={Math.min(20, soNguoi)} dat={setSoPhong} />
          <p className="phu" style={{ marginTop: 12 }}>Số người tính cả trẻ em. Mỗi phòng có ít nhất một người.</p>
        </HopNoi>
      )}
    </>
  );
}
