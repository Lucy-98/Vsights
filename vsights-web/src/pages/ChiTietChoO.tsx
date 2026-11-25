import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { layChiTiet, TEN_LOAI_HINH, type ChiTietChoO as ChiTiet, type GiaOta, type LoaiPhongGia } from '../api/stays';
import { BieuTuong } from '../components/BieuTuong';
import { LichChonNgay } from '../components/LichChonNgay';
import { DaiLoi } from '../components/ThongBao';
import { dinhDangDiem, dinhDangTien } from '../utils/dinhDang';
import { congNgay, khoangNgay, ngayNgan, sangIso, tuIso } from '../utils/ngay';
import { thamSoTim } from './TrangChu';

// W04/W05, M05 — Chi tiết chỗ ở và giá từng đêm theo OTA (UC03, GET /stays/{ma}).
// Quy tắc: giá so được (đã gồm thuế, phí / đã quy đổi +15%) xếp theo xep_hang_gia; giá "không so" đứng sau, không xếp hạng;
// nút "Xem trên [OTA]" mở thẳng trang OTA, không hộp xác nhận (D-034); gia_cu → "Giá có thể đã thay đổi" (BR-03).

function thongTinHuy(lp: LoaiPhongGia): string {
  if (lp.so_ngay_huy_mien_phi == null) return 'Huỷ miễn phí: chưa có thông tin';
  if (lp.so_ngay_huy_mien_phi === 0) return 'Không huỷ miễn phí';
  return `Huỷ miễn phí trước ${lp.so_ngay_huy_mien_phi} ngày`;
}
function thanhToan(lp: LoaiPhongGia): string {
  if (lp.thanh_toan_tai_cho == null) return 'Thanh toán tại chỗ: chưa có thông tin';
  return lp.thanh_toan_tai_cho ? 'Có thể thanh toán tại chỗ' : 'Thanh toán trước trên OTA';
}

function sapOta(ds: GiaOta[]): GiaOta[] {
  return [...ds].sort((a, b) => {
    if (a.so_sanh_duoc !== b.so_sanh_duoc) return a.so_sanh_duoc ? -1 : 1;
    return (a.xep_hang_gia ?? 99) - (b.xep_hang_gia ?? 99);
  });
}

function DongOta({ g, laReNhat }: { g: GiaOta; laReNhat: boolean }) {
  return (
    <div className="dong-ota">
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <b>{g.ten_ota}</b>
          {laReNhat && <span className="nhan nhan-tot">Rẻ nhất trong các trang so được</span>}
          {g.gia_cu && <span className="nhan nhan-vang">Giá có thể đã thay đổi</span>}
        </div>
        <div className="phu">
          {g.nhan_thue_phi}
          {g.cap_nhat_gia && ` · cập nhật ${new Date(g.cap_nhat_gia).toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })}`}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        {g.du_dem && g.tong_ca_chuyen != null ? (
          <span style={{ font: g.so_sanh_duoc ? '600 18px var(--font-tieu-de)' : '500 15px var(--font-noi-dung)', color: g.so_sanh_duoc ? 'var(--chu)' : 'var(--chu-vua)' }}>
            {dinhDangTien(g.tong_ca_chuyen)}
          </span>
        ) : (
          <span className="phu">Thiếu giá {g.dem.length ? 'một số đêm' : 'các đêm này'}</span>
        )}
      </div>
      <a className={`nut nut-nho ${laReNhat ? 'nut-chinh' : 'nut-vien'}`} href={g.url} target="_blank" rel="noopener noreferrer">
        Xem trên {g.ten_ota}
        <BieuTuong ten="ra-ngoai" co={16} />
      </a>
    </div>
  );
}

function BangGiaDem({ lp, ngays }: { lp: LoaiPhongGia; ngays: string[] }) {
  const ds = sapOta(lp.gia_theo_ota);
  return (
    <div className="cuon-ngang" style={{ marginTop: 12 }}>
      <table className="bang-gia">
        <caption className="phu" style={{ textAlign: 'left', captionSide: 'top', paddingBottom: 6 }}>
          Giá từng đêm cho mỗi phòng (giá tham khảo)
        </caption>
        <thead>
          <tr>
            <th scope="col">Đêm</th>
            {ds.map((g) => (
              <th key={g.ma_lien_ket} scope="col">
                {g.ten_ota}
                <div style={{ fontWeight: 400 }}>{g.so_sanh_duoc ? (g.gom_thue_phi_goc ? 'đã gồm thuế, phí' : 'đã quy đổi +15%') : 'không so'}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ngays.map((n) => (
            <tr key={n}>
              <td>{ngayNgan(tuIso(n)!)}</td>
              {ds.map((g) => {
                const d = g.dem.find((x) => x.ngay === n);
                return <td key={g.ma_lien_ket}>{d ? dinhDangTien(d.gia_dem) : <span className="phu">Chưa có giá</span>}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChiTietChoO() {
  const { ma } = useParams();
  const [p] = useSearchParams();
  const dieuHuong = useNavigate();
  const [ct, setCt] = useState<ChiTiet | null>(null);
  const [loi, setLoi] = useState<unknown>(null);
  const [dangTai, setDangTai] = useState(true);
  const [moLich, setMoLich] = useState(false);
  const [moBang, setMoBang] = useState<Record<number, boolean>>({});

  const ngayNhan = p.get('ngay_nhan') ?? undefined;
  const ngayTra = p.get('ngay_tra') ?? undefined;
  const soNguoi = Number(p.get('so_nguoi') ?? 2) || 2;
  const soPhong = Number(p.get('so_phong') ?? 1) || 1;

  const tai = () => {
    const ac = new AbortController();
    setDangTai(true);
    setLoi(null);
    layChiTiet(Number(ma), { ngay_nhan: ngayNhan, ngay_tra: ngayTra, so_nguoi: soNguoi, so_phong: soPhong }, ac.signal)
      .then(setCt)
      .catch((e) => {
        if (!(e instanceof DOMException)) setLoi(e);
      })
      .finally(() => setDangTai(false));
    return ac;
  };
  useEffect(() => {
    const ac = tai();
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ma, ngayNhan, ngayTra, soNguoi, soPhong]);

  const doiNgay = (n: string, t: string) => dieuHuong(`/cho-o/${ma}?${thamSoTim({ ngay_nhan: n, ngay_tra: t, so_nguoi: soNguoi, so_phong: soPhong })}`, { replace: true });

  if (loi instanceof ApiError && loi.status === 404) {
    return (
      <main className="khung trang">
        <h1 className="tieu-de-trang">Không tìm thấy chỗ ở</h1>
        <p>Chỗ ở này không có hoặc đang tạm ẩn.</p>
        <Link to="/">Tìm chỗ ở khác</Link>
      </main>
    );
  }
  if (loi) {
    return (
      <main className="khung trang">
        <DaiLoi loi={loi} thuLai={tai} />
      </main>
    );
  }
  if (!ct || dangTai) {
    return (
      <main className="khung trang" aria-busy="true">
        <div className="xuong" style={{ height: 16, width: 180, marginBottom: 14 }} />
        <div className="xuong" style={{ height: 40, width: '60%', marginBottom: 24 }} />
        <div className="xuong" style={{ height: 320, borderRadius: 24 }} />
      </main>
    );
  }

  const coNgay = !!(ct.ngay_nhan && ct.ngay_tra);
  const ngays = coNgay ? Array.from({ length: ct.so_dem ?? 0 }, (_, i) => sangIso(congNgay(tuIso(ct.ngay_nhan)!, i))) : [];
  const phongDu = ct.loai_phong.filter((l) => l.du_suc_chua);
  const phongThieu = ct.loai_phong.filter((l) => !l.du_suc_chua);
  const veKetQua = `/cho-o?${thamSoTim({ ma_tinh: ct.ma_tinh, ngay_nhan: ct.ngay_nhan, ngay_tra: ct.ngay_tra, so_nguoi: ct.so_nguoi, so_phong: ct.so_phong })}`;

  return (
    <main className="khung trang">
      <Link to={coNgay ? veKetQua : '/'} className="nut-chu" style={{ paddingLeft: 0, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
        ‹ Kết quả tìm
      </Link>
      <p className="nhan-in-hoa" style={{ margin: '8px 0 0' }}>
        {TEN_LOAI_HINH[ct.loai_hinh] ?? ct.loai_hinh}
        {ct.hang_sao ? ` · ${ct.hang_sao} sao` : ''}
        {ct.khu_vuc ? ` · ${ct.khu_vuc}` : ''}
      </p>
      <h1 className="tieu-de-trang" style={{ marginBottom: 8 }}>{ct.ten}</h1>
      <p className="phu" style={{ fontSize: 15, margin: '0 0 6px' }}>{ct.dia_chi ?? 'Chưa có thông tin địa chỉ'}</p>
      <p style={{ margin: '0 0 24px' }}>
        {dinhDangDiem(ct.diem_danh_gia, ct.so_luot_danh_gia)} <span className="phu">· đánh giá của người dùng Vsights</span>
        {ct.la_du_lieu_mau && <span className="nhan nhan-xam" style={{ marginLeft: 8 }}>Dữ liệu mẫu</span>}
      </p>

      <div className="the" style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div className="nhan-in-hoa">Giá cho</div>
          <div style={{ fontWeight: 600 }}>
            {coNgay ? khoangNgay(tuIso(ct.ngay_nhan)!, tuIso(ct.ngay_tra)!) : 'Chưa chọn ngày'} · {ct.so_nguoi} người, {ct.so_phong} phòng
          </div>
        </div>
        <button type="button" className="nut nut-vien nut-nho" onClick={() => setMoLich(true)}>
          <BieuTuong ten="lich" co={18} />
          {coNgay ? 'Đổi ngày' : 'Chọn ngày để xem giá'}
        </button>
      </div>

      {coNgay && ct.ngay_re_hon.length > 0 && (
        <div className="the" style={{ marginBottom: 24, background: 'var(--nen-nhat)' }}>
          <p className="nhan-in-hoa" style={{ marginTop: 0 }}>Ngày gần đó có giá thấp hơn</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {ct.ngay_re_hon.map((k) => (
              <button key={k.ngay_nhan} type="button" className="chip" onClick={() => doiNgay(k.ngay_nhan, k.ngay_tra)}>
                {khoangNgay(tuIso(k.ngay_nhan)!, tuIso(k.ngay_tra)!, false)} · {dinhDangTien(k.tong_ca_chuyen)}
              </button>
            ))}
          </div>
        </div>
      )}

      <h2 style={{ fontSize: 26, margin: '8px 0 12px' }}>Loại phòng và giá trên từng trang</h2>
      {!coNgay && <p className="phu">Chọn ngày nhận, trả phòng để xem giá từng đêm.</p>}
      <div style={{ display: 'grid', gap: 16 }}>
        {[...phongDu, ...phongThieu].map((lp) => {
          const ds = sapOta(lp.gia_theo_ota);
          return (
            <section key={lp.ma_loai_phong} className="the" style={{ opacity: lp.du_suc_chua ? 1 : 0.7 }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8 }}>
                <h3 style={{ fontSize: 19 }}>{lp.ten_loai_phong}</h3>
                {!lp.du_suc_chua && <span className="nhan nhan-xam">Không đủ chỗ cho {ct.so_nguoi} người, {ct.so_phong} phòng</span>}
              </div>
              <p className="phu" style={{ margin: '4px 0 0' }}>
                {[lp.loai_giuong, lp.dien_tich ? `${String(lp.dien_tich).replace('.', ',')} m²` : null, `${lp.suc_chua_nl} người lớn${lp.suc_chua_te ? `, ${lp.suc_chua_te} trẻ em` : ''}`, lp.co_bua_sang ? 'Có bữa sáng' : 'Không gồm bữa sáng']
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              <p className="phu" style={{ margin: '2px 0 0' }}>
                {thongTinHuy(lp)} · {thanhToan(lp)}
              </p>
              {coNgay && lp.du_suc_chua && (
                <>
                  <div style={{ marginTop: 8 }}>
                    {ds.length === 0 && <p className="phu">Chưa có giá cho các đêm này.</p>}
                    {ds.map((g) => (
                      <DongOta key={g.ma_lien_ket} g={g} laReNhat={!!ct.re_nhat && ct.re_nhat[0] === lp.ma_loai_phong && ct.re_nhat[1] === g.ma_lien_ket} />
                    ))}
                  </div>
                  {ds.length > 1 && (
                    <button type="button" className="nut-chu" style={{ paddingLeft: 0 }} aria-expanded={!!moBang[lp.ma_loai_phong]} onClick={() => setMoBang((m) => ({ ...m, [lp.ma_loai_phong]: !m[lp.ma_loai_phong] }))}>
                      {moBang[lp.ma_loai_phong] ? 'Ẩn giá từng đêm' : `So ${ds.length} trang theo từng đêm`}
                    </button>
                  )}
                  {moBang[lp.ma_loai_phong] && <BangGiaDem lp={lp} ngays={ngays} />}
                </>
              )}
            </section>
          );
        })}
      </div>

      {(ct.tien_nghi.length > 0 || ct.mo_ta) && (
        <section style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 22, marginBottom: 10 }}>Giới thiệu</h2>
          {ct.mo_ta && <p style={{ whiteSpace: 'pre-line', maxWidth: 760 }}>{ct.mo_ta}</p>}
          {ct.tien_nghi.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {ct.tien_nghi.map((t) => (
                <span key={t} className="nhan nhan-xam">
                  {t}
                </span>
              ))}
            </div>
          )}
        </section>
      )}

      <p className="phu" style={{ marginTop: 32 }}>{ct.ghi_chu}</p>

      {moLich && (
        <LichChonNgay
          nhan={tuIso(ct.ngay_nhan)}
          tra={tuIso(ct.ngay_tra)}
          dong={() => setMoLich(false)}
          xong={(n, t) => {
            setMoLich(false);
            doiNgay(sangIso(n), sangIso(t));
          }}
        />
      )}
    </main>
  );
}
