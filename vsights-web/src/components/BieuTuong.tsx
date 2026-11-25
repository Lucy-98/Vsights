// Biểu tượng SVG nét (không dùng emoji trong giao diện — UX-014).
type Ten = 'tim' | 'lich' | 'tro-ly' | 'tai-khoan' | 'cua-toi' | 'dong' | 'loc' | 'mui-ten' | 'ra-ngoai' | 'sao';

const DUONG: Record<Ten, string> = {
  tim: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-4.3-4.3',
  lich: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  'tro-ly': 'M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z',
  'tai-khoan': 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0',
  'cua-toi': 'M6 3h12v18l-6-4-6 4z',
  dong: 'M6 6l12 12M18 6 6 18',
  loc: 'M4 6h16M7 12h10M10 18h4',
  'mui-ten': 'M5 12h14M13 6l6 6-6 6',
  'ra-ngoai': 'M14 4h6v6M20 4l-9 9M18 14v6H4V6h6',
  sao: 'M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z',
};

export function BieuTuong({ ten, co = 20, mau = 'currentColor' }: { ten: Ten; co?: number; mau?: string }) {
  return (
    <svg width={co} height={co} viewBox="0 0 24 24" fill="none" stroke={mau} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={DUONG[ten]} />
    </svg>
  );
}
