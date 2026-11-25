// Quy ước định dạng theo base/03 mục 3.1 và mục 10.

const tien = new Intl.NumberFormat('vi-VN');

/** 1240000 → "1.240.000 ₫" */
export function dinhDangTien(so: number): string {
  return `${tien.format(Math.round(so))} ₫`;
}

/** Khoảng giá mỗi người của địa điểm; không có thì trả null để UI ghi "Chưa có thông tin". */
export function dinhDangKhoangGia(tu?: number | null, den?: number | null): string | null {
  if (tu == null && den == null) return null;
  if (tu === 0 && (den == null || den === 0)) return 'Miễn phí';
  if (tu != null && den != null && tu !== den) return `${dinhDangTien(tu)} – ${dinhDangTien(den)} / người`;
  return `${dinhDangTien((tu ?? den) as number)} / người`;
}

/** Điểm luôn một chữ số thập phân, dấu phẩy: 4 → "4,0". Dưới 3 lượt → "Chưa đủ đánh giá". */
export function dinhDangDiem(diem?: number | null, soLuot?: number | null): string {
  if (diem == null || (soLuot != null && soLuot < 3)) return 'Chưa đủ đánh giá';
  const chu = `★ ${diem.toFixed(1).replace('.', ',')}`;
  return soLuot != null ? `${chu} (${soLuot})` : chu;
}
