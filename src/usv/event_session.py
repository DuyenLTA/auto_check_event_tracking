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


async def phai_co_app(adb, serial: str, package: str, *,
                      from_launch: bool) -> None:
    """Tu choi ghi khi app khong co tren may VA tool phai tu mo app.

    `from_launch=False` -> tool khong mo app, tester tu mo tay. Luc do khong
    con cai im lang can chan, nen KHONG duoc chan: do la cach duy nhat de ghi
    mot app ma `pm list packages` khong tra ra (app cho user khac, app vua cai
    chua kip xuat hien, hoac ten khac ten tren store).

    Bat buoc phai chan o day: `adb shell monkey -p <app khong ton tai>` in ra
    "No activities found to run" nhung EXIT CODE VAN LA 0, nen mo app that bai
    trong IM LANG. Tool cu the ghi tiep va bao cao gan event cua app khac cho
    app dang test - da ra "5 pass" cho mot app khong he duoc cai tren may.
    PASS gia te hon FAIL gia: fail thi con di kiem tra, pass thi dong so.

    Goi y ten gan giong: go lech mot chu la loi hay gap nhat, va tu do lai
    mot chuoi 40 ky tu bang mat thi rat de bo qua.
    """
    if not from_launch:
        return
    try:
        installed = await adb.packages(serial)
    except AdbError:
        return           # khong doc duoc danh sach thi de logcat_stream bao loi
    if package in installed:
        return
    gan = get_close_matches(package, installed, n=3, cutoff=0.6)
    raise HTTPException(status_code=400, detail=(
        f"May {serial} khong co app {package!r}. "
        + (f"Ý bạn là: {', '.join(gan)}? " if gan else "")
        + "Nếu tên đúng mà máy không trả ra, hãy bỏ tick \"Tool tự mở app\" "
          "rồi tự mở app trên máy SAU khi bấm Ghi."))


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
