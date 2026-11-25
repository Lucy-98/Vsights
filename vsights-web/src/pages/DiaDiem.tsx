import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { layTinhThanh, timDiaDiem, type DiaDiem as DiaDiemT, type NhomDiaDiem, type TinhThanh } from '../api/places';
import { DaiLoi } from '../components/ThongBao';
import { dinhDangDiem, dinhDangKhoangGia } from '../utils/dinhDang';

// W10/M10 — Địa điểm, quán ăn (UC05, UC06). Gọi GET /places thật; công khai, không cần đăng nhập.

const KICH_THUOC = 12;

export function DiaDiem() {
  const [tinh, setTinh] = useState<TinhThanh[]>([]);
  const [maTinh, setMaTinh] = useState<number | ''>('');
  const [nhom, setNhom] = useState<NhomDiaDiem>('tham_quan');
  const [tuKhoa, setTuKhoa] = useState('');
  const [tuKhoaDaGui, setTuKhoaDaGui] = useState('');

  const [items, setItems] = useState<DiaDiemT[]>([]);
  const [tong, setTong] = useState(0);
  const [trang, setTrang] = useState(1);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState<unknown>(null);
  const lanGoi = useRef(0); // bỏ phản hồi cũ khi người dùng đổi bộ lọc nhanh

  useEffect(() => {
    layTinhThanh().then(setTinh).catch(() => setTinh([]));
  }, []);

  const tai = useCallback(
    async (trangMuon: number, noiThem: boolean) => {
      const lan = ++lanGoi.current;
      setDangTai(true);
      setLoi(null);
      try {
        const kq = await timDiaDiem({
          ma_tinh: maTinh === '' ? undefined : maTinh,
          nhom,
          q: tuKhoaDaGui || undefined,
          trang: trangMuon,
          kich_thuoc: KICH_THUOC,
        });
        if (lan !== lanGoi.current) return;
        setItems((cu) => (noiThem ? [...cu, ...kq.items] : kq.items));
        setTong(kq.tong);
        setTrang(kq.trang ?? trangMuon);
      } catch (err) {
        if (lan === lanGoi.current) setLoi(err);
      } finally {
        if (lan === lanGoi.current) setDangTai(false);
      }
    },
    [maTinh, nhom, tuKhoaDaGui],
  );

  // Đổi bộ lọc → tải lại từ trang 1.
  useEffect(() => {
    tai(1, false);
  }, [tai]);

  const guiTim = (e: FormEvent) => {
    e.preventDefault();
    setTuKhoaDaGui(tuKhoa.trim());
  };

  const conNua = items.length < tong;

  return (
    <main className="khung" style={{ padding: '48px var(--le-trang) 96px' }}>
      <p className="nhan-in-hoa">Khám phá</p>
      <h1 style={{ fontSize: 'clamp(34px, 5vw, 60px)', lineHeight: 1.05, margin: '8px 0 32px' }}>
        Điểm tham quan và quán ăn
      </h1>

      <form onSubmit={guiTim} style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'end', marginBottom: 20 }}>
        <div className="truong" style={{ marginBottom: 0, minWidth: 220 }}>
          <label htmlFor="tinh">Tỉnh, thành</label>
          <select id="tinh" className="o-nhap" value={maTinh} onChange={(e) => setMaTinh(e.target.value ? Number(e.target.value) : '')}>
            <option value="">Tất cả 34 tỉnh, thành</option>
            {tinh.map((t) => (
              <option key={t.ma_tinh} value={t.ma_tinh}>
                {t.ten_tinh}
              </option>
            ))}
          </select>
        </div>
        <div className="truong" style={{ marginBottom: 0, flex: 1, minWidth: 220 }}>
          <label htmlFor="q">Tìm theo tên</label>
          <input id="q" className="o-nhap" value={tuKhoa} onChange={(e) => setTuKhoa(e.target.value)} placeholder="Ví dụ: chợ, bảo tàng, bún chả" />
        </div>
        <button className="nut nut-chinh" type="submit">Tìm</button>
      </form>

      <div role="group" aria-label="Nhóm địa điểm" style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
        <button className="chip" aria-pressed={nhom === 'tham_quan'} onClick={() => setNhom('tham_quan')}>
          Điểm tham quan
        </button>
        <button className="chip" aria-pressed={nhom === 'an_uong'} onClick={() => setNhom('an_uong')}>
          Quán ăn
        </button>
      </div>

      {loi != null && (
        <div style={{ marginBottom: 20 }}>
          <DaiLoi loi={loi} thuLai={() => tai(1, false)} />
        </div>
      )}

      {!dangTai && !loi && items.length === 0 && (
        <div className="the" style={{ background: 'var(--nen-nhat)' }}>
          <h2 style={{ fontSize: 22, marginBottom: 6 }}>Chưa có kết quả</h2>
          <p className="phu" style={{ margin: 0 }}>Thử bỏ từ khoá hoặc chọn "Tất cả 34 tỉnh, thành".</p>
        </div>
      )}

      <p className="phu" aria-live="polite" style={{ marginBottom: 12 }}>
        {tong > 0 && `${tong.toLocaleString('vi-VN')} kết quả`}
      </p>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
        {items.map((d) => (
          <li key={d.ma_dia_diem} className="the">
            <p className="nhan-in-hoa" style={{ margin: 0 }}>
              {d.loai?.ten_loai ?? (nhom === 'an_uong' ? 'Quán ăn' : 'Điểm tham quan')}
            </p>
            <h3 style={{ fontSize: 18, margin: '6px 0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={d.ten}>
              {d.ten}
            </h3>
            <p className="phu" style={{ margin: '0 0 10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {d.dia_chi || 'Chưa có thông tin địa chỉ'}
            </p>
            <p style={{ margin: 0, fontSize: 14 }}>
              <span style={{ color: d.diem_tb != null && (d.so_luot_danh_gia ?? 3) >= 3 ? 'var(--chu)' : 'var(--chu-phu)' }}>
                {dinhDangDiem(d.diem_tb, d.so_luot_danh_gia)}
              </span>
              <span className="phu"> · {dinhDangKhoangGia(d.muc_gia_nguoi_tu, d.muc_gia_nguoi_den) ?? 'Chưa có thông tin giá'}</span>
            </p>
          </li>
        ))}
        {dangTai &&
          Array.from({ length: items.length ? 3 : 6 }, (_, i) => (
            <li key={`xuong-${i}`} className="the" aria-hidden="true">
              <div className="xuong" style={{ height: 12, width: '40%', marginBottom: 12 }} />
              <div className="xuong" style={{ height: 20, width: '80%', marginBottom: 10 }} />
              <div className="xuong" style={{ height: 14, width: '60%' }} />
            </li>
          ))}
      </ul>

      {conNua && !dangTai && (
        <div style={{ textAlign: 'center', marginTop: 32 }}>
          <button className="nut nut-vien" onClick={() => tai(trang + 1, true)}>
            Xem thêm
          </button>
        </div>
      )}

      <p className="phu" style={{ marginTop: 40 }}>
        Dữ liệu là dữ liệu mẫu. Giá vé, mức giá là giá tham khảo.
      </p>
    </main>
  );
}
