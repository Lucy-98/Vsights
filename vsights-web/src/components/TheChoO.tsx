import { Link } from 'react-router-dom';
import { giaCu, nhanThuePhi, TEN_LOAI_HINH, type KetQuaChoO } from '../api/stays';
import { dinhDangDiem, dinhDangTien } from '../utils/dinhDang';

// Thẻ kết quả (W03/M03). Giá to = rẻ nhất trong phép so (đã gồm thuế, phí — D-021, D-035).
// Giá "không so" (gia_ngoai_phep_so, B-023) hiện riêng, chữ nhỏ, không tô "rẻ nhất".
export function TheChoO({ c, soDem, soPhong, thamSo }: { c: KetQuaChoO; soDem: number; soPhong: number; thamSo: string }) {
  const r = c.re_nhat;
  const cu = giaCu(r.cap_nhat_gia);
  const tenLoai = TEN_LOAI_HINH[c.loai_hinh] ?? c.loai_hinh;
  return (
    <article className="the-cho-o">
      <div className="anh-cho" aria-hidden="true">
        {c.la_du_lieu_mau && <span className="nhan nhan-xam">Dữ liệu mẫu</span>}
      </div>
      <div style={{ minWidth: 0, display: 'grid', gap: 6, alignContent: 'start' }}>
        <p className="nhan-in-hoa" style={{ margin: 0 }}>
          {tenLoai}
          {c.hang_sao ? ` · ${c.hang_sao} sao` : ''}
          {c.khu_vuc ? ` · ${c.khu_vuc}` : ''}
        </p>
        <h3 style={{ fontSize: 20, lineHeight: 1.25 }}>
          <Link to={`/cho-o/${c.ma_co_so}?${thamSo}`} style={{ color: 'var(--chu)', textDecoration: 'none' }}>
            {c.ten}
          </Link>
        </h3>
        <p className="phu mot-dong" style={{ margin: 0 }}>{c.dia_chi ?? 'Chưa có thông tin địa chỉ'}</p>
        <p style={{ margin: 0, fontSize: 14 }}>
          <span style={{ color: c.diem_danh_gia != null ? 'var(--chu)' : 'var(--chu-phu)' }}>{dinhDangDiem(c.diem_danh_gia, c.so_luot_danh_gia)}</span>
          <span className="phu"> · đánh giá của người dùng Vsights</span>
        </p>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
          {c.so_thich_khop > 0 && <span className="nhan">Khớp {c.so_thich_khop} sở thích</span>}
          <span className="nhan nhan-xam">
            {r.ten_loai_phong}
            {c.so_lua_chon > 1 ? ` · ${c.so_lua_chon} lựa chọn có giá` : ''}
          </span>
        </div>
      </div>
      <div className="cot-gia">
        <div>
          <div className="phu">
            Giá tham khảo {soDem} đêm{soPhong > 1 ? `, ${soPhong} phòng` : ''}
          </div>
          <div className="gia-lon">{dinhDangTien(r.tong_ca_chuyen)}</div>
          <div className="phu">≈ {dinhDangTien(r.gia_tb_moi_dem_moi_phong)} / đêm / phòng</div>
          <div style={{ fontSize: 13, marginTop: 2 }}>
            trên <b>{r.ten_ota}</b> · {nhanThuePhi(r.gia_goc_gom_thue_phi)}
          </div>
          {cu && (
            <span className="nhan nhan-vang" style={{ marginTop: 6 }}>
              Giá có thể đã thay đổi
            </span>
          )}
          {c.gia_ngoai_phep_so.map((x) => (
            <div key={x.ma_lien_ket} className="phu" style={{ marginTop: 6 }}>
              {x.ten_ota} {dinhDangTien(x.tong_chua_gom_thue_phi)} · {x.nhan}
            </div>
          ))}
        </div>
        <Link to={`/cho-o/${c.ma_co_so}?${thamSo}`} className="nut nut-chinh nut-nho">
          Xem giá từng trang
        </Link>
      </div>
    </article>
  );
}
