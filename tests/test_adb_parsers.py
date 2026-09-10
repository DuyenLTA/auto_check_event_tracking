"""Parser thuan cua tang adb. Khong goi adb that."""

from __future__ import annotations

import pytest

from usv.adb_parsers import (
    AdbError, check_package, check_serial, parse_current_focus, parse_devices,
    parse_packages, parse_wm_density, parse_wm_size,
)


def test_parse_devices_lay_model():
    out = (
        "List of devices attached\n"
        "99261FFAZ0077C\tdevice product:x model:Pixel_5 device:y\n"
        "emulator-5554\toffline\n"
    )
    devices = parse_devices(out)
    assert [d.serial for d in devices] == ["99261FFAZ0077C", "emulator-5554"]
    assert devices[0].model == "Pixel_5"
    assert devices[0].usable is True
    assert devices[1].usable is False


def test_parse_packages_bo_prefix_va_sap_xep():
    out = "package:com.b.app\npackage:com.a.app\nrac khong phai package\n"
    assert parse_packages(out) == ["com.a.app", "com.b.app"]


def test_parse_wm_size_va_density():
    assert parse_wm_size("Physical size: 1080x2280") == (1080, 2280)
    assert parse_wm_density("Physical density: 440") == 440


def test_override_thang_physical():
    """Nguoi dung co the doi resolution bang `wm size` - luc do Physical khong
    con la cai dang render, phai lay Override."""
    out = "Physical size: 1080x2280\nOverride size: 720x1520"
    assert parse_wm_size(out) == (720, 1520)
    out_d = "Physical density: 440\nOverride density: 320"
    assert parse_wm_density(out_d) == 320


def test_parse_current_focus_app():
    line = "  mCurrentFocus=Window{3c95eb1 u0 com.x.app/com.x.app.MainActivity}"
    assert parse_current_focus(line) == "com.x.app"


def test_parse_current_focus_notification_shade():
    """Da xay ra that luc spike: shade giu focus nen dump ra cay SystemUI."""
    line = "  mCurrentFocus=Window{36bbaea u0 NotificationShade}"
    assert parse_current_focus(line) == "NotificationShade"


@pytest.mark.parametrize("bad", ["", "x; rm -rf /sdcard", "com.x app", "com/x"])
def test_check_package_chan_ky_tu_la(bad):
    """adb shell noi cac arg lai va chay qua sh TREN DEVICE - ten package la
    se chay lenh that. Dropdown khong phai bao dam vi API nhan input tu do."""
    with pytest.raises(AdbError):
        check_package(bad)


def test_check_package_va_serial_cho_gia_tri_that_di_qua():
    assert check_package("com.aihomedesign.aihomedecor.designidea.aiinterior")
    assert check_serial("99261FFAZ0077C")
    assert check_serial("emulator-5554")


# --- mo app: monkey tra exit 0 ke ca khi that bai ---

def test_launch_bao_loi_khi_may_noi_khong_co_man_nao_de_mo():
    """`monkey -p <app khong ton tai>` in "No activities found to run" nhung
    EXIT CODE VAN LA 0. Chi xem returncode thi mo app that bai trong im lang,
    roi phien ghi bat log cua app dang mo san - bao cao gan event cua app khac
    cho app dang test.
    """
    import asyncio

    from usv.adb_client import AdbClient
    from usv.adb_parsers import AdbError

    adb = AdbClient("/fake/adb")

    async def fake_run(*args, timeout=None):
        return ("** No activities found to run, monkey aborted.", "", 0)

    adb._run = fake_run
    with pytest.raises(AdbError) as err:
        asyncio.run(adb.launch("SERIAL1", "com.khong.he.co"))
    assert "khong co man nao de mo" in str(err.value)


def test_launch_im_lang_khi_mo_duoc():
    import asyncio

    from usv.adb_client import AdbClient

    adb = AdbClient("/fake/adb")

    async def fake_run(*args, timeout=None):
        return ("Events injected: 1", "", 0)

    adb._run = fake_run
    asyncio.run(adb.launch("SERIAL1", "com.example.app"))   # khong duoc nem gi


def test_app_running_doc_pidof():
    """pidof tra rong -> app khong chay. Can vi log FA-SVC do Play Services in
    ra chu khong phai process app, nen khong the doi chieu PID."""
    import asyncio

    from usv.adb_client import AdbClient

    adb = AdbClient("/fake/adb")
    calls = []

    async def fake_run(*args, timeout=None):
        calls.append(args)
        return (out, "", 0)

    adb._run = fake_run
    out = "4524\n"
    assert asyncio.run(adb.app_running("SERIAL1", "com.example.app")) is True
    out = "\n"
    assert asyncio.run(adb.app_running("SERIAL1", "com.example.app")) is False
    assert calls[0][-2:] == ("pidof", "com.example.app")


# --- app dang o foreground ---

DUMPSYS = """
  Stack #0:
    mResumedActivity: ActivityRecord{8a8d4a9 u0 com.ai.aiimage.aivideogenerator/.MainActivity t212}
    topResumedActivity=ActivityRecord{8a8d4a9 u0 com.ai.aiimage.aivideogenerator/.MainActivity}
"""


def test_doc_duoc_package_dang_o_foreground():
    from usv.adb_parsers import parse_resumed_package
    assert parse_resumed_package(DUMPSYS) == "com.ai.aiimage.aivideogenerator"


def test_khong_co_dong_resumed_thi_tra_None():
    from usv.adb_parsers import parse_resumed_package
    assert parse_resumed_package("Stack #0:\n  (khong co gi)") is None


def test_khong_nham_sang_dong_khac_co_dau_gach_cheo():
    from usv.adb_parsers import parse_resumed_package
    rac = "  mLastPausedActivity: ActivityRecord{1 u0 com.khac.app/.Main t1}"
    assert parse_resumed_package(rac) is None, "chi doc dong *ResumedActivity*"
