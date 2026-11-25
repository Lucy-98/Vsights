// Ngày theo giờ Việt Nam, định dạng theo base/03 ("T6 20/11", "T6 20/11 → CN 22/11").

const THU = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];

/** Ngày hôm nay ở Việt Nam (không phụ thuộc múi giờ máy). */
export function homNay(): Date {
  const s = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }); // YYYY-MM-DD
  return tuIso(s)!;
}

/** "2026-11-20" → Date (nửa đêm giờ máy, chỉ dùng phần ngày). */
export function tuIso(s: string | null | undefined): Date | null {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const [y, m, d] = s.split('-').map(Number);
  const kq = new Date(y, m - 1, d);
  return kq.getMonth() === m - 1 ? kq : null;
}

export function sangIso(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const n = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${n}`;
}

export function congNgay(d: Date, so: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + so);
}

export function soNgayGiua(a: Date, b: Date): number {
  return Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate()) - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / 86400000);
}

export function cungNgay(a: Date | null, b: Date | null): boolean {
  return !!a && !!b && sangIso(a) === sangIso(b);
}

/** "T6 20/11" */
export function ngayNgan(d: Date): string {
  return `${THU[d.getDay()]} ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** "T6 20/11 → CN 22/11 · 2 đêm" */
export function khoangNgay(nhan: Date, tra: Date, kemSoDem = true): string {
  const s = `${ngayNgan(nhan)} → ${ngayNgan(tra)}`;
  return kemSoDem ? `${s} · ${soNgayGiua(nhan, tra)} đêm` : s;
}

/** Cuối tuần gần nhất: nhận T6, trả CN (D-037(5)); hôm nay T7 → nhận hôm nay; CN → tuần sau. */
export function cuoiTuanToi(): [Date, Date] {
  const h = homNay();
  const thu = h.getDay();
  if (thu === 6) return [h, congNgay(h, 1)];
  const nhan = congNgay(h, (5 - thu + 7) % 7); // T6 hôm nay → nhận hôm nay
  return [nhan, congNgay(nhan, 2)];
}

export const TEN_THU_LICH = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
