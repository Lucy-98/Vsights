"""T-024 — kiểm phần SA chuẩn bị cho tích hợp chatbot (SA-017, SA-018).

- Công cụ `tim_cho_o` gọi service `tim_kiem.tim` với ghi_luot=False, loai_tru, trong giao dịch READ ONLY.
- Cột chatbot theo Q-022 = A (D-038): vẫn 66 bảng; ràng buộc đề xuất, xem xét, khoá gửi.
- D-039(a): nơi nghỉ dự kiến (ma_co_so_nghi, chưa có ma_cho_o) và chỗ ở tự khai "Đã đặt" thay thế nó.
"""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.db import engine
from app.services import tim_kiem


def _ma_tinh_co_nhieu_co_so(sql) -> int:
    return sql("SELECT ma_tinh FROM co_so_luu_tru WHERE trang_thai = 'hien' GROUP BY ma_tinh "
               "ORDER BY count(*) DESC, ma_tinh LIMIT 1")[0]["ma_tinh"]


def _tim(conn, ma_tinh, **them):
    hom_nay = date.today()
    return tim_kiem.tim(conn, ma_tinh=ma_tinh, ngay_nhan=hom_nay + timedelta(days=5),
                        ngay_tra=hom_nay + timedelta(days=7), so_nguoi=2, so_phong=1, ngan_sach=None,
                        loai_ngan_sach="ca_chuyen", loai_hinh=None, ma_tien_nghi=[], ma_so_thich=[],
                        sap_xep="phu_hop", trang=1, kich_thuoc=50, ma_nguoi_dung=None, hom_nay=hom_nay, **them)


# ---------------------------------------------------------------- công cụ tim_cho_o
def test_tim_khong_ghi_luot_va_loai_tru_trong_giao_dich_chi_doc(sql):
    ma_tinh = _ma_tinh_co_nhieu_co_so(sql)
    truoc = sql("SELECT count(*) AS n FROM luot_tim_kiem")[0]["n"]
    with engine().connect() as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '2s'"))
            day_du = _tim(conn, ma_tinh, ghi_luot=False)
            assert day_du["tong"] >= 2
            bo = [day_du["items"][0]["ma_co_so"]]
            con_lai = _tim(conn, ma_tinh, ghi_luot=False, loai_tru=bo)
    assert con_lai["tong"] == day_du["tong"] - 1
    assert bo[0] not in {i["ma_co_so"] for i in con_lai["items"]}
    assert sql("SELECT count(*) AS n FROM luot_tim_kiem")[0]["n"] == truoc


def test_tim_mac_dinh_van_ghi_luot(sql):
    ma_tinh = _ma_tinh_co_nhieu_co_so(sql)
    truoc = sql("SELECT count(*) AS n FROM luot_tim_kiem")[0]["n"]
    with engine().connect() as conn:
        _tim(conn, ma_tinh)
        conn.commit()
    assert sql("SELECT count(*) AS n FROM luot_tim_kiem")[0]["n"] == truoc + 1


# ---------------------------------------------------------------- lược đồ chatbot (Q-022 = A)
def test_van_66_bang(sql):
    assert sql("SELECT count(*) AS n FROM information_schema.tables "
               "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")[0]["n"] == 66


@pytest.fixture()
def hoi_thoai(sql):
    return sql("INSERT INTO hoi_thoai (ma_phien_an_danh) VALUES (:p) RETURNING ma_hoi_thoai",
               p=uuid.uuid4())[0]["ma_hoi_thoai"]


def _loi_rang_buoc(sql, cau, **p):
    with pytest.raises(DBAPIError) as e:
        sql(cau, **p)
    return e.value.orig.sqlstate


def test_trang_thai_mac_dinh_va_ban_nhap_phai_co_han(sql, hoi_thoai):
    r = sql("SELECT trang_thai_chuyen_di, phien_ban_trang_thai FROM hoi_thoai WHERE ma_hoi_thoai = :h", h=hoi_thoai)[0]
    assert r["trang_thai_chuyen_di"] == {"v": 1} and r["phien_ban_trang_thai"] == 0
    assert _loi_rang_buoc(sql, "UPDATE hoi_thoai SET ban_nhap_lich_trinh = jsonb_build_object('v', 1) WHERE ma_hoi_thoai = :h",
                          h=hoi_thoai) == "23514"


def test_de_xuat_phai_du_bon_cot_va_chi_o_tin_tro_ly(sql, hoi_thoai):
    # thiếu hạn → sai
    assert _loi_rang_buoc(sql, """INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, ma_xac_nhan, de_xuat,
        trang_thai_de_xuat) VALUES (:h, 'tro_ly', 'x', gen_random_uuid(), jsonb_build_object('v', 1), 'cho')""", h=hoi_thoai) == "23514"
    # tin người dùng không mang đề xuất
    assert _loi_rang_buoc(sql, """INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, ma_xac_nhan, de_xuat,
        trang_thai_de_xuat, de_xuat_het_han) VALUES (:h, 'nguoi_dung', 'x', gen_random_uuid(), jsonb_build_object('v', 1), 'cho',
        now() + interval '30 minutes')""", h=hoi_thoai) == "23514"
    sql("""INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, ma_xac_nhan, de_xuat, trang_thai_de_xuat,
        de_xuat_het_han) VALUES (:h, 'tro_ly', 'x', gen_random_uuid(), jsonb_build_object('v', 1), 'cho', now() + interval '30 minutes')""",
        h=hoi_thoai)


def test_xem_xet_phai_co_trang_thai_muc_va_ly_do(sql, hoi_thoai):
    assert _loi_rang_buoc(sql, """INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, can_xem_xet)
        VALUES (:h, 'tro_ly', 'x', TRUE)""", h=hoi_thoai) == "23514"
    assert _loi_rang_buoc(sql, """INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, can_xem_xet,
        trang_thai_xem_xet, muc_xem_xet, ly_do_xem_xet) VALUES (:h, 'tro_ly', 'x', TRUE, 'cho', 3, '{la_co}')""",
                          h=hoi_thoai) == "23514"
    sql("""INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, can_xem_xet, trang_thai_xem_xet,
        muc_xem_xet, ly_do_xem_xet) VALUES (:h, 'tro_ly', 'x', TRUE, 'cho', 3, '{bao_sai,khan_cap}')""", h=hoi_thoai)


def test_khoa_gui_chong_gui_hai_lan(sql, hoi_thoai):
    k = uuid.uuid4()
    cau = "INSERT INTO tin_nhan_chatbot (ma_hoi_thoai, vai_tro, noi_dung, khoa_gui) VALUES (:h, 'nguoi_dung', 'x', :k)"
    sql(cau, h=hoi_thoai, k=k)
    assert _loi_rang_buoc(sql, cau, h=hoi_thoai, k=k) == "23505"


# ---------------------------------------------------------------- D-039(a): nơi nghỉ dự kiến → Đã đặt
@pytest.fixture()
def lich(sql):
    """Lịch trình 3 ngày của du khách mẫu ở tỉnh có nhiều chỗ ở; trả về mã, các ngày, 2 cơ sở cùng tỉnh, 1 cơ sở khác tỉnh."""
    ma_tinh = _ma_tinh_co_nhieu_co_so(sql)
    u = sql("SELECT ma_nguoi_dung FROM nguoi_dung WHERE email = 'dukhach@vidu.vn'")[0]["ma_nguoi_dung"]
    d0 = date.today() + timedelta(days=20)
    lt = sql("""INSERT INTO lich_trinh (ma_chu, ma_tinh, ten, ngay_bat_dau, ngay_ket_thuc, so_nguoi)
                VALUES (:u, :t, 'Lịch thử T-024', :a, :b, 2) RETURNING ma_lich_trinh""",
             u=u, t=ma_tinh, a=d0, b=d0 + timedelta(days=2))[0]["ma_lich_trinh"]
    for i in range(3):
        sql("INSERT INTO ngay_lich_trinh (ma_lich_trinh, thu_tu_ngay, ngay) VALUES (:l, :i, :n)",
            l=lt, i=i + 1, n=d0 + timedelta(days=i))
    cung = [r["ma_co_so"] for r in sql("SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh = :t ORDER BY ma_co_so LIMIT 2",
                                       t=ma_tinh)]
    khac = sql("SELECT ma_co_so FROM co_so_luu_tru WHERE ma_tinh <> :t LIMIT 1", t=ma_tinh)[0]["ma_co_so"]
    return {"lt": lt, "u": u, "d0": d0, "a": cung[0], "b": cung[1], "khac": khac}


def _dem(sql, lt):
    return [(r["ma_co_so_nghi"], r["ma_cho_o"]) for r in
            sql("SELECT ma_co_so_nghi, ma_cho_o FROM ngay_lich_trinh WHERE ma_lich_trinh = :l ORDER BY thu_tu_ngay", l=lt)]


def _khai_da_dat(sql, L, co_so, tu, so_dem):
    return sql("""INSERT INTO cho_o_cua_toi (ma_nguoi_dung, ma_co_so, ma_lich_trinh, ngay_nhan, ngay_tra)
                  VALUES (:u, :c, :l, :n, :t) RETURNING ma_cho_o""",
               u=L["u"], c=co_so, l=L["lt"], n=L["d0"] + timedelta(days=tu),
               t=L["d0"] + timedelta(days=tu + so_dem))[0]["ma_cho_o"]


def test_noi_nghi_du_kien_khong_can_cho_o(sql, lich):
    sql("UPDATE ngay_lich_trinh SET ma_co_so_nghi = :c WHERE ma_lich_trinh = :l", c=lich["a"], l=lich["lt"])
    assert _dem(sql, lich["lt"]) == [(lich["a"], None)] * 3
    # không tạo chỗ ở "Đã đặt" nào (BR-07)
    assert sql("SELECT count(*) AS n FROM cho_o_cua_toi WHERE ma_lich_trinh = :l", l=lich["lt"])[0]["n"] == 0


def test_noi_nghi_khac_tinh_bi_chan(sql, lich):
    assert _loi_rang_buoc(sql, "UPDATE ngay_lich_trinh SET ma_co_so_nghi = :c WHERE ma_lich_trinh = :l",
                          c=lich["khac"], l=lich["lt"]) == "23514"


def test_da_dat_khac_co_so_thay_noi_nghi_du_kien(sql, lich):
    sql("UPDATE ngay_lich_trinh SET ma_co_so_nghi = :c WHERE ma_lich_trinh = :l", c=lich["a"], l=lich["lt"])
    cho_o = _khai_da_dat(sql, lich, lich["b"], 0, 2)          # 2 đêm đầu ở cơ sở B
    assert _dem(sql, lich["lt"]) == [(lich["b"], cho_o), (lich["b"], cho_o), (lich["a"], None)]


def test_da_dat_cung_co_so_gan_chi_tiet_cho_o(sql, lich):
    sql("UPDATE ngay_lich_trinh SET ma_co_so_nghi = :c WHERE ma_lich_trinh = :l", c=lich["a"], l=lich["lt"])
    cho_o = _khai_da_dat(sql, lich, lich["a"], 1, 2)
    assert _dem(sql, lich["lt"]) == [(lich["a"], None), (lich["a"], cho_o), (lich["a"], cho_o)]


def test_huy_va_doi_ngay_cap_nhat_dem(sql, lich):
    cho_o = _khai_da_dat(sql, lich, lich["b"], 0, 2)
    sql("UPDATE cho_o_cua_toi SET ngay_nhan = ngay_nhan + 1, ngay_tra = ngay_tra + 1 WHERE ma_cho_o = :c", c=cho_o)
    assert _dem(sql, lich["lt"]) == [(None, None), (lich["b"], cho_o), (lich["b"], cho_o)]
    sql("UPDATE cho_o_cua_toi SET trang_thai = 'da_huy' WHERE ma_cho_o = :c", c=cho_o)
    assert _dem(sql, lich["lt"]) == [(None, None)] * 3


def test_gan_cho_o_sai_co_so_hoac_ngoai_dem_bi_chan(sql, lich):
    cho_o = _khai_da_dat(sql, lich, lich["b"], 0, 1)
    # nơi nghỉ khác cơ sở của chỗ ở → khoá ngoại ghép
    assert _loi_rang_buoc(sql, "UPDATE ngay_lich_trinh SET ma_co_so_nghi = :a WHERE ma_lich_trinh = :l AND thu_tu_ngay = 1",
                          a=lich["a"], l=lich["lt"]) == "23503"
    # gắn chỗ ở vào đêm nó không phủ → trigger kiểm
    assert _loi_rang_buoc(sql, """UPDATE ngay_lich_trinh SET ma_cho_o = :c, ma_co_so_nghi = :b
                                  WHERE ma_lich_trinh = :l AND thu_tu_ngay = 3""",
                          c=cho_o, b=lich["b"], l=lich["lt"]) == "23514"


def test_B036_go_cho_o_khoi_lich_trinh_thi_dem_trong(sql, lich):
    """B-036: gỡ chỗ ở khỏi lịch trình (ma_lich_trinh → NULL) → các đêm nó phủ trở thành trống, đêm khác giữ nguyên."""
    sql("UPDATE ngay_lich_trinh SET ma_co_so_nghi = :c WHERE ma_lich_trinh = :l", c=lich["a"], l=lich["lt"])
    cho_o = _khai_da_dat(sql, lich, lich["b"], 0, 2)
    sql("UPDATE cho_o_cua_toi SET ma_lich_trinh = NULL WHERE ma_cho_o = :c", c=cho_o)
    assert _dem(sql, lich["lt"]) == [(None, None), (None, None), (lich["a"], None)]


# ---------------------------------------------------------------- hợp đồng service (chữ ký chốt cho AI)
def test_hop_dong_nhan_dung_thao_tac_va_tu_choi_truong_la():
    from pydantic import TypeAdapter, ValidationError

    from app.services import hop_dong as hd
    ds = TypeAdapter(list[hd.ThaoTac]).validate_python([
        {"loai": "bo_diem", "thu_tu_ngay": 2, "ma_dia_diem": 7},
        {"loai": "gan_noi_nghi", "thu_tu_ngay": [1, 2], "ma_co_so": 21}])
    assert isinstance(ds[0], hd.BoDiem) and isinstance(ds[1], hd.GanNoiNghi)
    with pytest.raises(ValidationError):
        TypeAdapter(hd.ThaoTac).validate_python({"loai": "xoa_lich_trinh", "thu_tu_ngay": 1})
    with pytest.raises(ValidationError):
        hd.Diem(loai="cho_o", ma=1, la="x")
