"""SQL cho người dùng, phiên đăng nhập, đếm đăng nhập sai."""
import uuid
from datetime import datetime

from sqlalchemy import Connection, text


def tim_theo_email(conn: Connection, email: str):
    return conn.execute(text(
        "SELECT ma_nguoi_dung, email, mat_khau_bam, ho_ten, vai_tro, email_da_xac_thuc, trang_thai, tao_luc "
        "FROM nguoi_dung WHERE email = :e"), {"e": email}).mappings().first()


def tim_theo_ma(conn: Connection, ma: int):
    return conn.execute(text(
        "SELECT ma_nguoi_dung, email, ho_ten, vai_tro, email_da_xac_thuc, trang_thai, tao_luc "
        "FROM nguoi_dung WHERE ma_nguoi_dung = :m"), {"m": ma}).mappings().first()


def giu_cho_luot_thu(conn: Connection, email: str, ip: str, toi_da: int, phut_khoa: int):
    """UPSERT nguyên tử: tăng bộ đếm trước khi so mật khẩu, nên N yêu cầu song song không lọt quá giới hạn.
    Bộ đếm reset khi lần sai cuối đã quá `phut_khoa` phút và không còn bị khoá."""
    return conn.execute(text("""
        INSERT INTO dang_nhap_that_bai AS t (email_chuan, dia_chi_ip, so_lan, cap_nhat_luc)
        VALUES (:e, CAST(:ip AS inet), 1, now())
        ON CONFLICT (email_chuan, dia_chi_ip) DO UPDATE SET
          so_lan = CASE WHEN t.cap_nhat_luc < now() - make_interval(mins => :pk)
                         AND (t.khoa_den IS NULL OR t.khoa_den <= now()) THEN 1
                        ELSE LEAST(t.so_lan + 1, 32000) END,
          khoa_den = CASE
                       WHEN t.khoa_den > now() THEN t.khoa_den
                       WHEN t.cap_nhat_luc >= now() - make_interval(mins => :pk) AND t.so_lan + 1 > :td
                         THEN now() + make_interval(mins => :pk)
                       ELSE NULL END,
          cap_nhat_luc = now()
        RETURNING so_lan, khoa_den"""), {"e": email, "ip": ip, "td": toi_da, "pk": phut_khoa}).mappings().one()


def xoa_luot_thu(conn: Connection, email: str, ip: str) -> None:
    conn.execute(text("DELETE FROM dang_nhap_that_bai WHERE email_chuan = :e AND dia_chi_ip = CAST(:ip AS inet)"),
                 {"e": email, "ip": ip})


def tao_phien(conn: Connection, ma_nguoi_dung: int, ho: uuid.UUID, token_bam: str, thiet_bi: str | None,
              het_han: datetime) -> None:
    conn.execute(text(
        "INSERT INTO phien_dang_nhap (ma_nguoi_dung, ma_ho_phien, token_bam, thiet_bi, het_han) "
        "VALUES (:u, :h, :t, :tb, :hh)"), {"u": ma_nguoi_dung, "h": ho, "t": token_bam, "tb": thiet_bi, "hh": het_han})


def khoa_phien_theo_token(conn: Connection, token_bam: str):
    """FOR UPDATE: hai yêu cầu refresh cùng token được tuần tự hoá; yêu cầu sau thấy xoay_luc đã đặt."""
    return conn.execute(text(
        "SELECT ma_phien, ma_nguoi_dung, ma_ho_phien, thiet_bi, het_han, xoay_luc, het_han <= now() AS da_het_han "
        "FROM phien_dang_nhap WHERE token_bam = :t FOR UPDATE"), {"t": token_bam}).mappings().first()


def danh_dau_da_xoay(conn: Connection, ma_phien: int) -> None:
    conn.execute(text("UPDATE phien_dang_nhap SET xoay_luc = now() WHERE ma_phien = :p"), {"p": ma_phien})


def xoa_ho_phien(conn: Connection, ho: uuid.UUID) -> int:
    return conn.execute(text("DELETE FROM phien_dang_nhap WHERE ma_ho_phien = :h"), {"h": ho}).rowcount


def ho_phien_con_hieu_luc(conn: Connection, ho: str, ma_nguoi_dung: int) -> bool:
    return conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM phien_dang_nhap WHERE ma_ho_phien = CAST(:h AS uuid) "
        "AND ma_nguoi_dung = :u AND xoay_luc IS NULL AND het_han > now())"), {"h": ho, "u": ma_nguoi_dung}).scalar()
