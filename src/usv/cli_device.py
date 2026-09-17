"""Chon may cho duong CLI. Tach rieng vi day la cho DUY NHAT duoc phep hoi
"may nao" - moi cho khac trong `cli_check` da co serial roi.

Nguyen tac: khong bao gio chon bua. Cam hai may ma tu chon mot thi ca bao cao
noi ve mot may khong ai dinh cham, va khong co gi trong report noi ra dieu do.
"""

from __future__ import annotations

from .adb_client import AdbClient
from .adb_parsers import AdbError


class CliError(Exception):
    """Loi da co message doc duoc - in ra stderr roi thoat, khong traceback."""


def make_client() -> AdbClient:
    try:
        return AdbClient()
    except AdbError as exc:
        raise CliError(str(exc)) from exc


async def pick_serial(adb, muon: str = "") -> str:
    """Dung mot may -> lay may do. Nhieu may ma khong chi dinh -> bao ten ra."""
    try:
        found = await adb.devices()
    except AdbError as exc:
        raise CliError(str(exc)) from exc

    dung_duoc = [d for d in found if d.state == "device"]
    if not dung_duoc:
        # May o trang thai unauthorized/offline VAN phai duoc noi ten: khac han
        # "khong cam may nao", va cach sua cung khac (bam Cho phep tren man).
        khac = ", ".join(f"{d.serial} ({d.state})" for d in found)
        raise CliError("Không thấy máy Android nào sẵn sàng."
                       + (f" Đang thấy: {khac}." if khac else
                          " Cắm cáp, bật USB debugging rồi chạy lại."))
    if muon:
        if muon not in {d.serial for d in dung_duoc}:
            raise CliError(f"Không thấy máy {muon!r}. Đang có: "
                           + ", ".join(d.serial for d in dung_duoc))
        return muon
    if len(dung_duoc) > 1:
        ten = ", ".join(f"{d.serial} ({d.model or 'không rõ'})" for d in dung_duoc)
        raise CliError(f"Đang cắm {len(dung_duoc)} máy: {ten}. "
                       "Chọn một bằng --serial <serial>.")
    return dung_duoc[0].serial
