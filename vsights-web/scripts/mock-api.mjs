// Mock API để thử frontend khi CHƯA chạy vsights-api. Chỉ dùng cục bộ; ảnh chụp nộp báo cáo lấy với backend thật.
// Mô phỏng: (1) xác thực theo base/02 mục 5 (refresh xoay vòng, thu hồi cả họ phiên, kiểm Origin);
// (2) T-027: /catalog/*, /places, /stays/search, /stays/{ma} ĐÚNG HÌNH DẠNG của vsights-api 0.6.3
//     (services/tim_kiem.py, services/hop_dong.ChiTietChoO) — Agoda đã gồm thuế, phí; Booking.com chưa gồm → ×1,15 rồi so;
//     Traveloka chưa gồm, không quy đổi → "không so" (D-021, D-035). Số tiền giả lập, không phải dữ liệu mẫu SA.
// Lưu ý: mã tỉnh, tên cơ sở, giá của API giả lập khác dữ liệu mẫu thật (db/03).
import http from 'node:http';
import crypto from 'node:crypto';

const PORT = Number(process.env.PORT ?? 8000);
const ORIGIN = process.env.ORIGIN ?? 'http://localhost:5173';
const ACCESS_TTL = Number(process.env.ACCESS_TTL ?? 900); // giây

const NGUOI_DUNG = {
  ma_nguoi_dung: 1,
  email: 'dukhach@vidu.vn',
  ho_ten: 'Du khách mẫu',
  vai_tro: 'du_khach',
  email_da_xac_thuc: true,
  tao_luc: '2026-11-01T08:00:00+07:00',
};
const MAT_KHAU = 'matkhau123';

const TINH = [
  { ma_tinh: 1, ten_tinh: 'Hà Nội', ma_vung: 1, ten_vung: 'Miền Bắc' },
  { ma_tinh: 48, ten_tinh: 'Đà Nẵng', ma_vung: 2, ten_vung: 'Miền Trung' },
  { ma_tinh: 68, ten_tinh: 'Lâm Đồng', ma_vung: 3, ten_vung: 'Miền Nam' },
];
const TIEN_NGHI = [
  { ma_tien_nghi: 1, ten_tien_nghi: 'Hồ bơi', pham_vi: 'co_so' },
  { ma_tien_nghi: 2, ten_tien_nghi: 'Bãi đỗ xe', pham_vi: 'co_so' },
  { ma_tien_nghi: 3, ten_tien_nghi: 'Đưa đón sân bay', pham_vi: 'co_so' },
  { ma_tien_nghi: 4, ten_tien_nghi: 'Phòng gym', pham_vi: 'co_so' },
  { ma_tien_nghi: 11, ten_tien_nghi: 'Điều hoà', pham_vi: 'phong' },
  { ma_tien_nghi: 12, ten_tien_nghi: 'Bếp riêng', pham_vi: 'phong' },
];
const SO_THICH = [
  { ma_so_thich: 1, ten: 'Biển', pham_vi: 'chung' },
  { ma_so_thich: 2, ten: 'Ẩm thực', pham_vi: 'chung' },
  { ma_so_thich: 3, ten: 'Gia đình có trẻ nhỏ', pham_vi: 'chung' },
  { ma_so_thich: 4, ten: 'Yên tĩnh', pham_vi: 'chung' },
];

// ---------- địa điểm ----------
const DIA_DIEM = [];
for (const t of TINH) {
  for (let i = 1; i <= 16; i++) {
    const anUong = i > 8;
    DIA_DIEM.push({
      ma_dia_diem: t.ma_tinh * 100 + i,
      ma_tinh: t.ma_tinh,
      ten: `${anUong ? 'Quán ăn' : 'Điểm tham quan'} mẫu ${t.ten_tinh} ${String(i).padStart(2, '0')}`,
      dia_chi: `${i} đường Mẫu, ${t.ten_tinh}`,
      loai: anUong ? { ten_loai: 'Ẩm thực địa phương', nhom: 'an_uong' } : { ten_loai: 'Danh thắng', nhom: 'tham_quan' },
      muc_gia_nguoi_tu: i % 4 === 0 ? 0 : 30000 * (i % 5 + 1),
      muc_gia_nguoi_den: i % 4 === 0 ? 0 : 60000 * (i % 5 + 1),
      diem_tb: i % 3 === 0 ? null : 3.5 + (i % 5) / 4,
      so_luot_danh_gia: i % 3 === 0 ? 1 : 3 + i,
      la_du_lieu_mau: true,
    });
  }
}

// ---------- chỗ ở + giá ----------
const OTA = [
  { ma_ota: 1, ten_ota: 'Agoda', gom: true, he_so: null, url: 'https://www.agoda.com/' },
  { ma_ota: 2, ten_ota: 'Booking.com', gom: false, he_so: 1.15, url: 'https://www.booking.com/' },
  { ma_ota: 3, ten_ota: 'Traveloka', gom: false, he_so: null, url: 'https://www.traveloka.com/' },
];
const LOAI = ['khach_san', 'homestay', 'resort', 'can_ho', 'nha_nghi'];
const KHU = { 48: ['Sơn Trà', 'An Hải', 'Mỹ Khê', 'Hội An'], 1: ['Hoàn Kiếm', 'Tây Hồ', 'Ba Đình'], 68: ['Đà Lạt', 'Bảo Lộc'] };
const TEN_LOAI = { khach_san: 'Khách sạn', homestay: 'Homestay', resort: 'Resort', can_ho: 'Căn hộ', nha_nghi: 'Nhà nghỉ' };

const hom = () => {
  const s = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
  return new Date(`${s}T00:00:00Z`);
};
const iso = (d) => d.toISOString().slice(0, 10);
const cong = (d, n) => new Date(d.getTime() + n * 86400000);
const HOM = hom();

const CO_SO = [];
let maLk = 1;
for (const t of TINH) {
  const so = t.ma_tinh === 48 ? 14 : 6;
  for (let i = 1; i <= so; i++) {
    const loai = LOAI[(i - 1) % LOAI.length];
    const ma = t.ma_tinh * 100 + i;
    const gocDem = loai === 'resort' ? 1800000 : loai === 'homestay' ? 320000 : loai === 'nha_nghi' ? 280000 : 450000 + i * 40000;
    const phong = [
      { ma_loai_phong: ma * 10 + 1, ten_loai_phong: 'Phòng Deluxe giường đôi', loai_giuong: '1 giường đôi', suc_chua_nl: 2, suc_chua_te: 1, dien_tich: 28, co_bua_sang: i % 2 === 0, thanh_toan_tai_cho: i % 3 === 0 ? null : i % 2 === 0, so_ngay_huy_mien_phi: i % 4 === 0 ? null : (i % 3) + 1, dieu_kien_huy: null, tien_nghi: ['Điều hoà'], gia: gocDem },
      { ma_loai_phong: ma * 10 + 2, ten_loai_phong: 'Phòng gia đình', loai_giuong: '2 giường đôi', suc_chua_nl: 4, suc_chua_te: 2, dien_tich: 40, co_bua_sang: true, thanh_toan_tai_cho: false, so_ngay_huy_mien_phi: 0, dieu_kien_huy: null, tien_nghi: ['Điều hoà', 'Bếp riêng'], gia: Math.round(gocDem * 1.7) },
    ];
    const lienKet = OTA.filter((o) => !(o.ma_ota === 3 && i % 3 !== 0)) // Traveloka chỉ ở 1/3 cơ sở
      .map((o) => ({ ma_lien_ket: maLk++, ...o, hong: o.ma_ota === 2 && i === 5 }));
    CO_SO.push({
      ma_co_so: ma,
      ma_tinh: t.ma_tinh,
      ten: `${TEN_LOAI[loai]} mẫu ${t.ten_tinh} ${String(i).padStart(2, '0')}`,
      loai_hinh: loai,
      dia_chi: `${i * 3} đường Mẫu, ${KHU[t.ma_tinh][i % KHU[t.ma_tinh].length]}, ${t.ten_tinh}`,
      khu_vuc: KHU[t.ma_tinh][i % KHU[t.ma_tinh].length],
      hang_sao: loai === 'khach_san' || loai === 'resort' ? 3 + (i % 3) : null,
      vi_do: 16.05 + i / 1000,
      kinh_do: 108.2 + i / 1000,
      diem: i % 4 === 3 ? null : 3.8 + (i % 6) / 5,
      so_luot: i % 4 === 3 ? 2 : 4 + i * 3,
      la_du_lieu_mau: true,
      mo_ta: `Mô tả mẫu cho ${TEN_LOAI[loai].toLowerCase()} tại ${t.ten_tinh}. Nội dung chỉ để thử giao diện.`,
      tien_nghi_ma: [1, 2, 3, 4].filter((m) => (i + m) % 3 !== 0),
      so_thich_ma: [1, 2, 3, 4].filter((m) => (i * m) % 4 === 1 || (t.ma_tinh === 48 && m === 1 && i % 2)),
      phong,
      lienKet,
    });
  }
}
// Giá từng đêm: 120 đêm từ hôm nay; cuối tuần đắt hơn; vài lỗ hổng; giá cũ ở một số liên kết.
function giaDem(cs, lp, lk, d) {
  const n = Math.round((d - HOM) / 86400000);
  if (n < 0 || n >= 120) return null;
  if (lk.hong) return null;
  if ((cs.ma_co_so + n + lk.ma_ota) % 29 === 0) return null; // thiếu một đêm
  const thu = d.getUTCDay();
  const cuoiTuan = thu === 5 || thu === 6 ? 1.18 : 1;
  const lech = lk.ma_ota === 1 ? 1 : lk.ma_ota === 2 ? 0.9 : 0.86;
  return Math.round((lp.gia * cuoiTuan * lech * (1 + ((cs.ma_co_so + n) % 5) / 50)) / 1000) * 1000;
}
const capNhat = (lk, cs) => new Date(Date.now() - (cs.ma_co_so % 7 === 2 && lk.ma_ota === 1 ? 5 : 1) * 86400000).toISOString();

function giaOta(cs, lp, lk, nhan, soDem, soPhong) {
  const dem = [];
  for (let k = 0; k < soDem; k++) {
    const d = cong(nhan, k);
    const g = giaDem(cs, lp, lk, d);
    if (g != null) dem.push({ ngay: iso(d), gia_dem: lk.he_so ? Math.round(g * lk.he_so) : g, goc: g });
  }
  const du = dem.length === soDem;
  const soSanh = lk.gom || !!lk.he_so;
  const tong = du ? (lk.he_so ? Math.round(dem.reduce((a, x) => a + x.goc, 0) * lk.he_so) : dem.reduce((a, x) => a + x.goc, 0)) * soPhong : null;
  const cn = capNhat(lk, cs);
  return {
    ma_lien_ket: lk.ma_lien_ket,
    ten_ota: lk.ten_ota,
    url: lk.url,
    gom_thue_phi_goc: lk.gom,
    so_sanh_duoc: soSanh,
    nhan_thue_phi: lk.gom ? 'đã gồm thuế, phí' : lk.he_so ? 'đã quy đổi +15% thuế, phí' : 'chưa gồm thuế, phí · không so',
    du_dem: du,
    dem: dem.map(({ ngay, gia_dem }) => ({ ngay, gia_dem })),
    tong_ca_chuyen: tong,
    cap_nhat_gia: cn,
    gia_cu: Date.now() - new Date(cn).getTime() > 3 * 86400000,
    xep_hang_gia: null,
  };
}

function luaChon(cs, nhan, soDem, soNguoi, soPhong) {
  const kq = [];
  for (const lp of cs.phong) {
    const duSucChua = (lp.suc_chua_nl + lp.suc_chua_te) * soPhong >= soNguoi;
    for (const lk of cs.lienKet) kq.push({ lp, lk, g: giaOta(cs, lp, lk, nhan, soDem, soPhong), duSucChua });
  }
  return kq;
}

function loi422(res, ma, tb, ct = null) {
  return json(res, 422, { ma_loi: ma, thong_bao: tb, chi_tiet: ct });
}
function kiemNgay(res, q) {
  const nhan = q.get('ngay_nhan') ? new Date(`${q.get('ngay_nhan')}T00:00:00Z`) : null;
  const tra = q.get('ngay_tra') ? new Date(`${q.get('ngay_tra')}T00:00:00Z`) : null;
  const soNguoi = Number(q.get('so_nguoi') ?? 2);
  const soPhong = Number(q.get('so_phong') ?? 1);
  if (!nhan || !tra) return { nhan: null, tra: null, soNguoi, soPhong, soDem: null };
  if (nhan < HOM) return void loi422(res, 'NGAY_KHONG_HOP_LE', 'Ngày nhận phòng không được ở quá khứ.');
  if (tra <= nhan) return void loi422(res, 'NGAY_KHONG_HOP_LE', 'Ngày trả phòng phải sau ngày nhận phòng.');
  const soDem = Math.round((tra - nhan) / 86400000);
  if (soDem > 30) return void loi422(res, 'QUA_SO_DEM', 'Mỗi lần ở tối đa 30 đêm.', { so_dem: soDem });
  if (soNguoi < soPhong) return void loi422(res, 'SO_NGUOI_IT_HON_SO_PHONG', 'Số người phải lớn hơn hoặc bằng số phòng.');
  return { nhan, tra, soNguoi, soPhong, soDem };
}

const GHI_CHU =
  'Giá tham khảo cho cả chuyến, đã gồm thuế, phí; giá ghi "chưa gồm thuế, phí · không so" chỉ hiện riêng, không dùng để so. Giá cuối cùng do OTA quyết định. Vsights không nhận đặt chỗ; phòng trống do OTA xác nhận.';

function timLoc(p) {
  const kq = [];
  for (const cs of CO_SO) {
    if (cs.ma_tinh !== p.ma_tinh) continue;
    if (p.loai_hinh && cs.loai_hinh !== p.loai_hinh) continue;
    const tnCs = p.tien_nghi.filter((m) => m < 10);
    if (!tnCs.every((m) => cs.tien_nghi_ma.includes(m))) continue;
    const ls = luaChon(cs, p.nhan, p.soDem, p.soNguoi, p.soPhong).filter(
      (x) => x.duSucChua && x.g.so_sanh_duoc && x.g.du_dem && p.tien_nghi.filter((m) => m >= 10).every((m) => x.lp.tien_nghi.includes(TIEN_NGHI.find((t) => t.ma_tien_nghi === m).ten_tien_nghi)),
    );
    if (!ls.length) continue;
    ls.sort((a, b) => a.g.tong_ca_chuyen - b.g.tong_ca_chuyen);
    const r = ls[0];
    if (p.ngan_sach) {
      const so = p.loai_ngan_sach === 'ca_chuyen' ? r.g.tong_ca_chuyen : r.g.tong_ca_chuyen / p.soDem / p.soPhong;
      if (so > p.ngan_sach) continue;
    }
    const ngoai = luaChon(cs, p.nhan, p.soDem, p.soNguoi, p.soPhong).filter((x) => x.duSucChua && !x.g.so_sanh_duoc && x.g.du_dem);
    ngoai.sort((a, b) => a.g.tong_ca_chuyen - b.g.tong_ca_chuyen);
    kq.push({ cs, r, so: ls.length, ngoai: ngoai.slice(0, 1), khop: p.so_thich.filter((m) => cs.so_thich_ma.includes(m)).length });
  }
  const diem = (x) => (x.cs.so_luot >= 3 ? x.cs.diem : -1);
  if (p.sap_xep === 'gia_tang') kq.sort((a, b) => a.r.g.tong_ca_chuyen - b.r.g.tong_ca_chuyen);
  else if (p.sap_xep === 'danh_gia') kq.sort((a, b) => diem(b) - diem(a) || a.r.g.tong_ca_chuyen - b.r.g.tong_ca_chuyen);
  else kq.sort((a, b) => b.khop - a.khop || a.r.g.tong_ca_chuyen - b.r.g.tong_ca_chuyen || diem(b) - diem(a));
  return kq;
}

function timChoO(res, q) {
  const ng = kiemNgay(res, q);
  if (!ng) return;
  const ma_tinh = Number(q.get('ma_tinh'));
  if (!TINH.some((t) => t.ma_tinh === ma_tinh)) return loi422(res, 'MA_KHONG_TON_TAI', 'Tỉnh, thành không tồn tại.', { ma_tinh });
  if (!ng.nhan) return loi422(res, 'NGAY_KHONG_HOP_LE', 'Thiếu ngày nhận, trả phòng.');
  const p = {
    ma_tinh, ...ng,
    ngan_sach: q.get('ngan_sach') ? Number(q.get('ngan_sach')) : null,
    loai_ngan_sach: q.get('loai_ngan_sach') ?? 'moi_dem',
    loai_hinh: q.get('loai_hinh'),
    tien_nghi: q.getAll('ma_tien_nghi').map(Number),
    so_thich: q.getAll('ma_so_thich').map(Number),
    sap_xep: q.get('sap_xep') ?? 'phu_hop',
  };
  const trang = Math.max(1, Number(q.get('trang') ?? 1));
  const kt = Math.min(100, Math.max(1, Number(q.get('kich_thuoc') ?? 20)));
  const ds = timLoc(p);
  let goi_y = [];
  if (!ds.length) {
    for (const m of [...new Set(p.tien_nghi)].slice(0, 5)) {
      const n = timLoc({ ...p, tien_nghi: p.tien_nghi.filter((x) => x !== m) }).length;
      goi_y.push({ dieu_kien: 'ma_tien_nghi', gia_tri: m, nhan: `Bỏ “${TIEN_NGHI.find((t) => t.ma_tien_nghi === m)?.ten_tien_nghi ?? m}”`, so_ket_qua: n });
    }
    if (new Set(p.tien_nghi).size > 1) goi_y.push({ dieu_kien: 'ma_tien_nghi', gia_tri: null, nhan: 'Bỏ mọi tiện nghi đang lọc', so_ket_qua: timLoc({ ...p, tien_nghi: [] }).length });
    if (p.ngan_sach) goi_y.push({ dieu_kien: 'ngan_sach', gia_tri: null, nhan: 'Bỏ giới hạn ngân sách', so_ket_qua: timLoc({ ...p, ngan_sach: null }).length });
    if (p.loai_hinh) goi_y.push({ dieu_kien: 'loai_hinh', gia_tri: null, nhan: 'Mọi loại hình chỗ ở', so_ket_qua: timLoc({ ...p, loai_hinh: null }).length });
    goi_y = goi_y.filter((g) => g.so_ket_qua);
    if (!goi_y.length) goi_y = [{ dieu_kien: 'ma_tinh', gia_tri: null, nhan: 'Thử tỉnh, thành khác hoặc ngày khác', so_ket_qua: null }];
  }
  const items = ds.slice((trang - 1) * kt, trang * kt).map(({ cs, r, so, ngoai, khop }) => ({
    ma_co_so: cs.ma_co_so, ten: cs.ten, loai_hinh: cs.loai_hinh, dia_chi: cs.dia_chi, khu_vuc: cs.khu_vuc, hang_sao: cs.hang_sao,
    diem_danh_gia: cs.so_luot >= 3 ? Math.round(cs.diem * 10) / 10 : null, so_luot_danh_gia: cs.so_luot,
    so_thich_khop: khop, so_lua_chon: so, la_du_lieu_mau: true,
    re_nhat: {
      ma_loai_phong: r.lp.ma_loai_phong, ten_loai_phong: r.lp.ten_loai_phong, ten_ota: r.lk.ten_ota, ma_lien_ket: r.lk.ma_lien_ket,
      tong_ca_chuyen: r.g.tong_ca_chuyen, gia_tb_moi_dem_moi_phong: Math.round(r.g.tong_ca_chuyen / p.soDem / p.soPhong),
      gom_thue_phi: true, gia_goc_gom_thue_phi: r.lk.gom, cap_nhat_gia: r.g.cap_nhat_gia,
    },
    gia_ngoai_phep_so: ngoai.map((x) => ({
      ten_ota: x.lk.ten_ota, ma_lien_ket: x.lk.ma_lien_ket, ma_loai_phong: x.lp.ma_loai_phong, ten_loai_phong: x.lp.ten_loai_phong,
      tong_chua_gom_thue_phi: x.g.tong_ca_chuyen, gom_thue_phi: false, so_sanh_duoc: false, nhan: 'chưa gồm thuế, phí · không so', cap_nhat_gia: x.g.cap_nhat_gia,
    })),
  }));
  json(res, 200, { items, tong: ds.length, trang, kich_thuoc: kt, so_dem: p.soDem, ghi_chu: GHI_CHU, goi_y_noi_dieu_kien: goi_y });
}

function chiTiet(res, ma, q) {
  const cs = CO_SO.find((c) => c.ma_co_so === ma);
  if (!cs) return json(res, 404, { ma_loi: 'KHONG_TIM_THAY', thong_bao: 'Không tìm thấy chỗ ở.', chi_tiet: null });
  const ng = kiemNgay(res, q);
  if (!ng) return;
  const coNgay = !!ng.nhan;
  const loai_phong = cs.phong.map((lp) => {
    const du = (lp.suc_chua_nl + lp.suc_chua_te) * ng.soPhong >= ng.soNguoi;
    const g = coNgay ? cs.lienKet.map((lk) => giaOta(cs, lp, lk, ng.nhan, ng.soDem, ng.soPhong)) : [];
    const { gia, ...lpRa } = lp;
    void gia;
    return { ...lpRa, du_suc_chua: du, gia_theo_ota: g };
  });
  let re = null;
  const xh = [];
  for (const lp of loai_phong) if (lp.du_suc_chua) for (const g of lp.gia_theo_ota) if (g.so_sanh_duoc && g.du_dem) xh.push({ lp, g });
  xh.sort((a, b) => a.g.tong_ca_chuyen - b.g.tong_ca_chuyen);
  xh.forEach((x, i) => (x.g.xep_hang_gia = i + 1));
  if (xh.length) re = [xh[0].lp.ma_loai_phong, xh[0].g.ma_lien_ket];
  const ngay_re_hon = [];
  if (coNgay && xh.length) {
    for (const lech of [-3, -2, -1, 1, 2, 3]) {
      const n = cong(ng.nhan, lech);
      if (n < HOM) continue;
      const tot = luaChon(cs, n, ng.soDem, ng.soNguoi, ng.soPhong).filter((x) => x.duSucChua && x.g.so_sanh_duoc && x.g.du_dem).map((x) => x.g.tong_ca_chuyen);
      const m = Math.min(...tot);
      if (tot.length && m < xh[0].g.tong_ca_chuyen) ngay_re_hon.push({ ngay_nhan: iso(n), ngay_tra: iso(cong(n, ng.soDem)), tong_ca_chuyen: m });
    }
    ngay_re_hon.sort((a, b) => a.tong_ca_chuyen - b.tong_ca_chuyen).splice(3);
  }
  json(res, 200, {
    ma_co_so: cs.ma_co_so, ma_tinh: cs.ma_tinh, ten: cs.ten, loai_hinh: cs.loai_hinh, dia_chi: cs.dia_chi, khu_vuc: cs.khu_vuc,
    hang_sao: cs.hang_sao, vi_do: cs.vi_do, kinh_do: cs.kinh_do,
    diem_danh_gia: cs.so_luot >= 3 ? Math.round(cs.diem * 10) / 10 : null, so_luot_danh_gia: cs.so_luot, la_du_lieu_mau: true,
    mo_ta: cs.mo_ta, tien_nghi: TIEN_NGHI.filter((t) => cs.tien_nghi_ma.includes(t.ma_tien_nghi)).map((t) => t.ten_tien_nghi),
    so_thich: SO_THICH.filter((s) => cs.so_thich_ma.includes(s.ma_so_thich)).map((s) => s.ten),
    ngay_nhan: coNgay ? iso(ng.nhan) : null, ngay_tra: coNgay ? iso(ng.tra) : null, so_dem: ng.soDem,
    so_nguoi: ng.soNguoi, so_phong: ng.soPhong, loai_phong, re_nhat: re, ngay_re_hon, ghi_chu: GHI_CHU,
  });
}

// ---------- xác thực ----------
const phien = new Map(); // refresh token → { hoPhien, daXoay }
const hoBiThuHoi = new Set();
const accessHopLe = new Map(); // access → { hoPhien, het }

function json(res, status, body, extra = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', ...extra });
  res.end(body === undefined ? '' : JSON.stringify(body));
}
const loi = (res, status, ma_loi, thong_bao, extra) => json(res, status, { ma_loi, thong_bao, chi_tiet: null }, extra);

function capToken(res, hoPhien) {
  const access = crypto.randomBytes(24).toString('base64url');
  const refresh = crypto.randomBytes(32).toString('base64url');
  accessHopLe.set(access, { hoPhien, het: Date.now() + ACCESS_TTL * 1000 });
  phien.set(refresh, { hoPhien, daXoay: false });
  const cookie = `vs_refresh=${refresh}; HttpOnly; SameSite=Strict; Path=/auth; Max-Age=2592000`;
  json(res, 200, { access_token: access, token_type: 'bearer', expires_in: ACCESS_TTL }, { 'Set-Cookie': cookie });
}

const docCookie = (req) =>
  Object.fromEntries((req.headers.cookie ?? '').split(';').map((c) => c.trim().split('=')).filter((p) => p[0]));

const docBody = (req) =>
  new Promise((ok) => {
    let s = '';
    req.on('data', (c) => (s += c));
    req.on('end', () => {
      try {
        ok(s ? JSON.parse(s) : {});
      } catch {
        ok({});
      }
    });
  });

function kiemAccess(req) {
  const m = /^Bearer (.+)$/.exec(req.headers.authorization ?? '');
  if (!m) return null;
  const a = accessHopLe.get(m[1]);
  if (!a || a.het < Date.now() || hoBiThuHoi.has(a.hoPhien)) return null;
  return a;
}

http
  .createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', ORIGIN);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
    res.setHeader('Access-Control-Expose-Headers', 'Retry-After');
    if (req.method === 'OPTIONS') return json(res, 204);

    const url = new URL(req.url, `http://localhost:${PORT}`);
    const p = url.pathname;

    if (['/auth/login', '/auth/refresh', '/auth/logout'].includes(p)) {
      if (req.headers.origin && req.headers.origin !== ORIGIN) return loi(res, 403, 'NGUON_KHONG_HOP_LE', 'Nguồn yêu cầu không hợp lệ.');
    }

    if (p === '/auth/login' && req.method === 'POST') {
      const b = await docBody(req);
      if (String(b.email ?? '').toLowerCase() !== NGUOI_DUNG.email || b.mat_khau !== MAT_KHAU)
        return loi(res, 401, 'SAI_THONG_TIN', 'Email hoặc mật khẩu không đúng.');
      return capToken(res, crypto.randomUUID());
    }

    if (p === '/auth/refresh' && req.method === 'POST') {
      const r = docCookie(req).vs_refresh;
      const ph = r && phien.get(r);
      if (!ph || hoBiThuHoi.has(ph.hoPhien)) return loi(res, 401, 'REFRESH_KHONG_HOP_LE', 'Phiên không hợp lệ.');
      if (ph.daXoay) {
        hoBiThuHoi.add(ph.hoPhien); // gửi lại token đã xoay → thu hồi cả họ
        return loi(res, 401, 'REFRESH_BI_DUNG_LAI', 'Phiên đã bị thu hồi.');
      }
      ph.daXoay = true;
      return capToken(res, ph.hoPhien);
    }

    if (p === '/auth/logout' && req.method === 'POST') {
      const r = docCookie(req).vs_refresh;
      const ph = r && phien.get(r);
      if (ph) hoBiThuHoi.add(ph.hoPhien);
      return json(res, 204, undefined, { 'Set-Cookie': 'vs_refresh=; HttpOnly; SameSite=Strict; Path=/auth; Max-Age=0' });
    }

    if (p === '/auth/me' && req.method === 'GET') {
      if (!kiemAccess(req)) return loi(res, 401, 'TOKEN_HET_HAN', 'Phiên đăng nhập đã hết hạn.');
      return json(res, 200, NGUOI_DUNG);
    }

    if (p === '/catalog/provinces') return json(res, 200, TINH);
    if (p === '/catalog/amenities') return json(res, 200, TIEN_NGHI);
    if (p === '/catalog/interests') return json(res, 200, SO_THICH);

    if (p === '/places' && req.method === 'GET') {
      const q = url.searchParams;
      const trang = Math.max(1, Number(q.get('trang') ?? 1));
      const kt = Math.min(100, Math.max(1, Number(q.get('kich_thuoc') ?? 20)));
      let ds = DIA_DIEM;
      if (q.get('ma_tinh')) ds = ds.filter((d) => d.ma_tinh === Number(q.get('ma_tinh')));
      if (q.get('nhom')) ds = ds.filter((d) => d.loai.nhom === q.get('nhom'));
      if (q.get('q')) ds = ds.filter((d) => d.ten.toLowerCase().includes(q.get('q').toLowerCase()));
      return json(res, 200, { items: ds.slice((trang - 1) * kt, trang * kt), tong: ds.length, trang, kich_thuoc: kt });
    }

    if (p === '/stays/search' && req.method === 'GET') return timChoO(res, url.searchParams);
    const m = /^\/stays\/(\d+)$/.exec(p);
    if (m && req.method === 'GET') return chiTiet(res, Number(m[1]), url.searchParams);

    loi(res, 404, 'KHONG_TIM_THAY', 'Không tìm thấy.');
  })
  .listen(PORT, () => console.log(`Mock API: http://localhost:${PORT} (tài khoản ${NGUOI_DUNG.email} / ${MAT_KHAU})`));
