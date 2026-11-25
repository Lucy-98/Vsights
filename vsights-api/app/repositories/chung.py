"""Hàm dùng chung: INSERT/UPDATE theo danh sách cột cho phép (tên cột không bao giờ lấy từ người dùng)."""
from typing import Any

from sqlalchemy import Connection, text


def chen(conn: Connection, bang: str, khoa: str, du_lieu: dict[str, Any], cot_hop_le: set[str]) -> int:
    cot = [c for c in du_lieu if c in cot_hop_le]
    sql = f"INSERT INTO {bang} ({', '.join(cot)}) VALUES ({', '.join(':' + c for c in cot)}) RETURNING {khoa}"
    return conn.execute(text(sql), {c: du_lieu[c] for c in cot}).scalar_one()


def sua(conn: Connection, bang: str, khoa: str, ma: int, du_lieu: dict[str, Any], cot_hop_le: set[str],
        them_set: str = "") -> int:
    cot = [c for c in du_lieu if c in cot_hop_le]
    if not cot and not them_set:
        return 1
    gan = [f"{c} = :{c}" for c in cot] + ([them_set] if them_set else [])
    sql = f"UPDATE {bang} SET {', '.join(gan)} WHERE {khoa} = :_ma"
    return conn.execute(text(sql), {**{c: du_lieu[c] for c in cot}, "_ma": ma}).rowcount


def thay_bang_noi(conn: Connection, bang: str, cot_cha: str, ma_cha: int, cot_con: str, ds: list[int]) -> None:
    conn.execute(text(f"DELETE FROM {bang} WHERE {cot_cha} = :m"), {"m": ma_cha})
    if ds:
        conn.execute(text(f"INSERT INTO {bang} ({cot_cha}, {cot_con}) SELECT :m, unnest(CAST(:ds AS bigint[]))"),
                     {"m": ma_cha, "ds": sorted(set(ds))})
