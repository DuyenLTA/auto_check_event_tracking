"""Chuan bi va don phien ghi - hai viec phai lam TRUOC khi ghi.

Tach khoi routes_event vi ca hai deu la LUAT, khong phai chuyen HTTP: mot cai
tra loi "co duoc ghi app nay khong", cai kia "phien truoc con gi phai don".
Route chi con viec goi va doi ma loi ra HTTP.
"""

from __future__ import annotations

from difflib import get_close_matches

from fastapi import HTTPException

from . import logcat_stream
from .adb_parsers import AdbError
from .event_state import state


async def co_the_tu_mo(adb, serial: str, package: str) -> tuple[bool, str]:
    """(tool co tu mo app duoc khong, cau nhac cho tester).

    KHONG chan khi khong tim thay: tester phai test duoc ca app ma
    `pm list packages` khong tra ra (app cho user khac, app vua cai, ten khac
    ten tren store). Phien ghi van chay, va van chay TU DAU - stream mo truoc
    khi app duoc mo nen event dau tien khong mat.

    Nhung cung KHONG duoc tu mo bua: `adb shell monkey -p <app khong ton tai>`
    in "No activities found to run" ma tra EXIT CODE 0, nen mo that bai trong
    im lang - roi phien ghi bat log cua app dang mo san va bao cao gan event
    cua app KHAC cho app dang test. Da ra "5 pass" cho mot app khong duoc cai.

    Nen: tim thay -> tu mo. Khong thay -> de tester tu mo, va NOI RA.
    """
    try:
        installed = await adb.packages(serial)
    except AdbError:
        return False, ("Không đọc được danh sách app trên máy — hãy tự mở app "
                       "trên máy BÂY GIỜ.")
    if package in installed:
        return True, ""
    gan = get_close_matches(package, installed, n=3, cutoff=0.6)
    return False, (
        f"Máy không có app {package!r} nên tool không tự mở. "
        + (f"Ý bạn là: {', '.join(gan)}? " if gan else "")
        + "Nếu tên đúng thì hãy tự MỞ APP trên máy BÂY GIỜ — phiên ghi đã bắt "
          "đầu nên vẫn bắt được event từ lúc mở.")


async def bo_phien_cu() -> None:
    """Nap spec moi = lam lai tu dau, nen bo het ket qua cua phien truoc.

    Bo ca `recording` chu khong chi `windows`/`run`: giu lai mot phien ghi da
    dung thi stage ket o 'ready_to_check' - nut Ghi khoa, nut Cham mo, va
    tester ket cung vi Reset se mat luon spec vua nap.

    Con dang ghi thi phai KILL that: de treo thi process logcat cu doc song
    song voi phien sau, hai ben an mat log cua nhau.
    """
    recording = state.recording
    if recording is not None and not recording.stopped:
        await logcat_stream.stop(recording)
    state.recording = None
    state.run = None
    state.windows = ()
