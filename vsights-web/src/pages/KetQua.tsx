import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  layTienNghi,
  laySoThich,
  TEN_LOAI_HINH,
  timChoO,
  type DieuKienTim,
  type GoiYNoi,
  type KetQuaChoO,
  type LoaiHinh,
  type LoaiNganSach,
  type SapXep,
  type SoThich,
  type TienNghi,
  type TrangKetQua,
} from '../api/stays';
import { BieuTuong } from '../components/BieuTuong';
import { HopNoi } from '../components/HopNoi';
import { OTim, useTinhThanh, type DieuKienCoBan } from '../components/OTim';
import { TheChoO } from '../components/TheChoO';
import { DaiLoi } from '../components/ThongBao';
import { dinhDangTien } from '../utils/dinhDang';
import { khoangNgay, tuIso } from '../utils/ngay';
import { thamSoTim } from './TrangChu';

// W03/M03 — Kết quả tìm chỗ ở (UC02): bộ lọc, sắp xếp BR-04, gợi ý nới điều kiện có số kết quả thật (B-028).
const KICH_THUOC = 10;
const SAP_XEP: { gt: SapXep; ten: string }[] = [
  { gt: 'phu_hop', ten: 'Phù hợp nhất' },
  { gt: 'gia_tang', ten: 'Giá cả chuyến thấp trước' },
  { gt: 'danh_gia', ten: 'Điểm đánh giá cao trước' },
];

function docThamSo(p: URLSearchParams): DieuKienTim | null {
  const ma_tinh = Number(p.get('ma_tinh'));
  const ngay_nhan = p.get('ngay_nhan') ?? '';
  const ngay_tra = p.get('ngay_tra') ?? '';
  if (!ma_tinh || !tuIso(ngay_nhan) || !tuIso(ngay_tra)) return null;
  const so = (k: string) => (p.get(k) ? Number(p.get(k)) : undefined);
  return {
    ma_tinh,
    ngay_nhan,
    ngay_tra,
    so_nguoi: so('so_nguoi') ?? 2,
    so_phong: so('so_phong') ?? 1,
    ngan_sach: so('ngan_sach'),
    loai_ngan_sach: (p.get('loai_ngan_sach') as LoaiNganSach) || undefined,
    loai_hinh: (p.get('loai_hinh') as LoaiHinh) || undefined,
    ma_tien_nghi: p.getAll('ma_tien_nghi').map(Number).filter(Boolean),
    ma_so_thich: p.getAll('ma_so_thich').map(Number).filter(Boolean),
    sap_xep: (p.get('sap_xep') as SapXep) || 'phu_hop',
  };
}

function BoLoc({
  dk,
  doi,
  tienNghi,
  soThich,
}: {
  dk: DieuKienTim;
  doi: (thay: Partial<DieuKienTim>) => void;
  tienNghi: TienNghi[];
  soThich: SoThich[];
}) {
  const bat = (ds: number[] = [], m: number) => (ds.includes(m) ? ds.filter((x) => x !== m) : [...ds, m]);
  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <div className="truong" style={{ margin: 0 }}>
        <label htmlFor="sap-xep">Sắp xếp</label>
        <select id="sap-xep" className="o-nhap" value={dk.sap_xep} onChange={(e) => doi({ sap_xep: e.target.value as SapXep })}>
          {SAP_XEP.map((s) => (
            <option key={s.gt} value={s.gt}>
              {s.ten}
            </option>
          ))}
        </select>
        <span className="phu">"Phù hợp nhất": khớp sở thích nhiều hơn → giá cả chuyến thấp hơn → điểm đánh giá cao hơn (BR-04).</span>
      </div>
      <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="nhan-in-hoa" style={{ marginBottom: 8 }}>Loại hình</legend>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(Object.keys(TEN_LOAI_HINH) as LoaiHinh[]).map((l) => (
            <button key={l} type="button" className="chip" aria-pressed={dk.loai_hinh === l} onClick={() => doi({ loai_hinh: dk.loai_hinh === l ? undefined : l })}>
              {TEN_LOAI_HINH[l]}
            </button>
          ))}
        </div>
      </fieldset>
      {soThich.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="nhan-in-hoa" style={{ marginBottom: 8 }}>Sở thích (để sắp xếp)</legend>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {soThich.map((s) => (
              <button key={s.ma_so_thich} type="button" className="chip" aria-pressed={dk.ma_so_thich?.includes(s.ma_so_thich)} onClick={() => doi({ ma_so_thich: bat(dk.ma_so_thich, s.ma_so_thich) })}>
                {s.ten}
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {tienNghi.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="nhan-in-hoa" style={{ marginBottom: 8 }}>Tiện nghi phải có</legend>
          <div style={{ display: 'grid', gap: 2 }}>
            {tienNghi.map((t) => (
              <label key={t.ma_tien_nghi} style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 40, cursor: 'pointer', fontSize: 14 }}>
                <input type="checkbox" style={{ width: 18, height: 18 }} checked={!!dk.ma_tien_nghi?.includes(t.ma_tien_nghi)} onChange={() => doi({ ma_tien_nghi: bat(dk.ma_tien_nghi, t.ma_tien_nghi) })} />
                {t.ten_tien_nghi}
                {t.pham_vi === 'phong' && <span className="phu">(trong phòng)</span>}
              </label>
            ))}
          </div>
        </fieldset>
      )}
    </div>
  );
}

export function KetQua() {
  const [p] = useSearchParams();
  const dieuHuong = useNavigate();
  const dk = useMemo(() => docThamSo(p), [p]);
  const tinh = useTinhThanh();
  const [tienNghi, setTienNghi] = useState<TienNghi[]>([]);
  const [soThich, setSoThich] = useState<SoThich[]>([]);
  const [kq, setKq] = useState<TrangKetQua | null>(null);
  const [items, setItems] = useState<KetQuaChoO[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [loi, setLoi] = useState<unknown>(null);
  const [moSua, setMoSua] = useState(false);
  const [moLoc, setMoLoc] = useState(false);
  const lan = useRef(0);

  useEffect(() => {
    layTienNghi().then(setTienNghi).catch(() => setTienNghi([]));
    laySoThich().then(setSoThich).catch(() => setSoThich([]));
  }, []);

  const tai = async (trang: number, noiThem: boolean) => {
    if (!dk) return;
    const l = ++lan.current;
    setDangTai(true);
    setLoi(null);
    try {
      const r = await timChoO({ ...dk, trang, kich_thuoc: KICH_THUOC });
      if (l !== lan.current) return;
      setKq(r);
      setItems((cu) => (noiThem ? [...cu, ...r.items] : r.items));
    } catch (e) {
      if (l === lan.current) setLoi(e);
    } finally {
      if (l === lan.current) setDangTai(false);
    }
  };

  useEffect(() => {
    setItems([]);
    tai(1, false);
    window.scrollTo({ top: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dk]);

  if (!dk) {
    return (
      <main className="khung trang">
        <h1 className="tieu-de-trang">Tìm chỗ ở</h1>
        <OTim gui={(d) => dieuHuong(`/cho-o?${thamSoTim(d)}`)} />
      </main>
    );
  }

  const doi = (thay: Partial<DieuKienTim>) => dieuHuong(`/cho-o?${thamSoTim({ ...dk, ...thay })}`, { replace: true });
  const apDungGoiY = (g: GoiYNoi) => {
    if (g.dieu_kien === 'ma_tien_nghi') doi({ ma_tien_nghi: typeof g.gia_tri === 'number' ? dk.ma_tien_nghi?.filter((x) => x !== g.gia_tri) : [] });
    else if (g.dieu_kien === 'ngan_sach') doi({ ngan_sach: undefined, loai_ngan_sach: undefined });
    else if (g.dieu_kien === 'loai_hinh') doi({ loai_hinh: undefined });
    else if (g.dieu_kien === 'ngay_nhan' && g.gia_tri && typeof g.gia_tri === 'object') doi({ ...g.gia_tri });
    else setMoSua(true);
  };

  const tenTinh = tinh.find((t) => t.ma_tinh === dk.ma_tinh)?.ten_tinh ?? 'Tỉnh đã chọn';
  const nhan = tuIso(dk.ngay_nhan)!;
  const tra = tuIso(dk.ngay_tra)!;
  const soLoc = (dk.loai_hinh ? 1 : 0) + (dk.ma_tien_nghi?.length ?? 0) + (dk.ma_so_thich?.length ?? 0);
  const thamSoChiTiet = thamSoTim({ ngay_nhan: dk.ngay_nhan, ngay_tra: dk.ngay_tra, so_nguoi: dk.so_nguoi, so_phong: dk.so_phong });

  return (
    <main className="khung trang">
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <h1 style={{ fontSize: 'clamp(26px, 3.4vw, 36px)', marginRight: 8 }}>Chỗ ở tại {tenTinh}</h1>
        <button type="button" className="chip" onClick={() => setMoSua(true)} aria-label="Sửa điều kiện tìm">
          {khoangNgay(nhan, tra)} · {dk.so_nguoi} người, {dk.so_phong} phòng
          {dk.ngan_sach ? ` · dưới ${dinhDangTien(dk.ngan_sach)} ${dk.loai_ngan_sach === 'moi_dem' ? 'mỗi đêm' : 'cả chuyến'}` : ''}
          <b style={{ color: 'var(--mau-chinh)', marginLeft: 6 }}>Sửa</b>
        </button>
        <button type="button" className="chip nut-mo-loc" onClick={() => setMoLoc(true)}>
          <BieuTuong ten="loc" co={18} />
          Bộ lọc{soLoc ? ` (${soLoc})` : ''}
        </button>
      </div>

      <div className="bo-cuc-ket-qua">
        <aside className="cot-loc the" aria-label="Bộ lọc">
          <BoLoc dk={dk} doi={doi} tienNghi={tienNghi} soThich={soThich} />
        </aside>

        <section aria-label="Kết quả">
          {loi != null && (
            <div style={{ marginBottom: 16 }}>
              <DaiLoi loi={loi} thuLai={() => tai(1, false)} />
            </div>
          )}
          <p className="phu" aria-live="polite" style={{ margin: '0 0 12px' }}>
            {kq && !dangTai ? (kq.tong ? `${kq.tong.toLocaleString('vi-VN')} chỗ ở có giá cho đủ ${kq.so_dem} đêm` : '') : 'Đang tìm…'}
          </p>

          {!dangTai && !loi && kq && kq.tong === 0 && (
            <div className="the" style={{ background: 'var(--nen-nhat)', marginBottom: 16 }}>
              <h2 style={{ fontSize: 22, marginBottom: 6 }}>Chưa có chỗ ở hợp mọi điều kiện</h2>
              <p className="phu" style={{ marginTop: 0 }}>Bạn thử nới một điều kiện:</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {kq.goi_y_noi_dieu_kien.map((g, i) => (
                  <button key={i} type="button" className="chip" onClick={() => apDungGoiY(g)}>
                    {g.nhan}
                    {g.so_ket_qua != null && <b style={{ color: 'var(--mau-chinh)' }}>· {g.so_ket_qua} kết quả</b>}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gap: 16 }}>
            {items.map((c) => (
              <TheChoO key={c.ma_co_so} c={c} soDem={kq?.so_dem ?? 1} soPhong={dk.so_phong} thamSo={thamSoChiTiet} />
            ))}
            {dangTai &&
              Array.from({ length: items.length ? 2 : 4 }, (_, i) => (
                <div key={i} className="the-cho-o" aria-hidden="true">
                  <div className="xuong" style={{ minHeight: 150, borderRadius: 16 }} />
                  <div>
                    <div className="xuong" style={{ height: 14, width: '40%', marginBottom: 12 }} />
                    <div className="xuong" style={{ height: 22, width: '70%', marginBottom: 12 }} />
                    <div className="xuong" style={{ height: 14, width: '55%' }} />
                  </div>
                </div>
              ))}
          </div>

          {kq && items.length < kq.tong && !dangTai && (
            <div style={{ textAlign: 'center', marginTop: 28 }}>
              <button type="button" className="nut nut-vien" onClick={() => tai(Math.floor(items.length / KICH_THUOC) + 1, true)}>
                Xem thêm
              </button>
            </div>
          )}
          {kq && <p className="phu" style={{ marginTop: 28 }}>{kq.ghi_chu} Dữ liệu là dữ liệu mẫu.</p>}
        </section>
      </div>

      {moSua && (
        <HopNoi tieuDe="Sửa điều kiện tìm" dong={() => setMoSua(false)}>
          <OTim
            dau={dk}
            nhanNut="Tìm lại"
            gui={(d: DieuKienCoBan) => {
              setMoSua(false);
              dieuHuong(`/cho-o?${thamSoTim({ ...dk, ...d, ngan_sach: d.ngan_sach, loai_ngan_sach: d.loai_ngan_sach })}`);
            }}
          />
        </HopNoi>
      )}
      {moLoc && (
        <HopNoi
          tieuDe="Bộ lọc"
          dong={() => setMoLoc(false)}
          chan={
            <button type="button" className="nut nut-chinh nut-nho" onClick={() => setMoLoc(false)}>
              Xem {kq?.tong ?? 0} kết quả
            </button>
          }
        >
          <BoLoc dk={dk} doi={doi} tienNghi={tienNghi} soThich={soThich} />
        </HopNoi>
      )}
    </main>
  );
}
