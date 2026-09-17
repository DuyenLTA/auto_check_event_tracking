"""Chup man lam bang chung, va doc version app dang cai.

Hai cai bay:
  - Man tat thi `screencap` ra anh DEN ma khong bao loi. Phai `wake` truoc.
  - Chup that bai KHONG duoc lam sap ca luot cham: mat mot tam anh con hon
    mat ca bao cao.
"""

from __future__ import annotations

import asyncio

import pytest

from usv.adb_parsers import AdbError, parse_package_version
from usv.flow_screenshots import Album

PNG = b"\x89PNG\r\n\x1a\n" + b"gia-lap"

DUMPSYS = """
Packages:
  Package [com.example.app] (b1a2c3):
    userId=10234
    versionCode=125 minSdk=24 targetSdk=34
    versionName=2.4.1
    flags=[ HAS_CODE ALLOW_CLEAR_USER_DATA ]
"""


class FakeAdb:
    def __init__(self, awake: bool = True) -> None:
        self.awake = awake
        self.calls: list[str] = []
        self.no_png = False

    async def is_awake(self, serial):
        self.calls.append("is_awake")
        return self.awake

    async def wake(self, serial):
        self.calls.append("wake")
        self.awake = True

    async def screencap(self, serial):
        self.calls.append("screencap")
        if self.no_png:
            raise AdbError("screencap không trả về PNG hợp lệ.")
        return PNG


def run(coro):
    return asyncio.run(coro)


def test_man_tat_thi_danh_thuc_TRUOC_khi_chup():
    """Chup khi man tat ra anh den - mot bang chung vo dung ma nhin nhu that."""
    adb = FakeAdb(awake=False)
    album = Album(adb, "S1")
    run(album.snap("case A", "sau"))
    assert adb.calls.index("wake") < adb.calls.index("screencap"), adb.calls


def test_man_dang_sang_thi_khong_danh_thuc_thua():
    adb = FakeAdb(awake=True)
    run(Album(adb, "S1").snap("case A", "sau"))
    assert "wake" not in adb.calls


def test_chup_hong_khong_lam_sap_luot_cham():
    adb = FakeAdb()
    adb.no_png = True
    album = Album(adb, "S1")
    run(album.snap("case A", "sau"))      # khong duoc raise
    assert album.shots == {}


def test_anh_gom_theo_case_va_giu_thu_tu():
    adb = FakeAdb()
    album = Album(adb, "S1")
    run(album.snap("case A", "trước bước cuối"))
    run(album.snap("case A", "sau bước cuối"))
    run(album.snap("case B", "sau bước cuối"))
    assert list(album.shots) == ["case A", "case B"]
    assert [s.moment for s in album.shots["case A"]] == [
        "trước bước cuối", "sau bước cuối"]
    assert album.shots["case A"][0].png == PNG


def test_recorder_dung_duoc_lam_callback_cua_run_case():
    """`run_case` goi callback voi ten moc; album tu gan vao dung case."""
    adb = FakeAdb()
    album = Album(adb, "S1")
    ghi = album.recorder("case A")
    run(ghi("sau bước cuối"))
    assert album.shots["case A"][0].moment == "sau bước cuối"


@pytest.mark.parametrize("raw, mong_doi", [
    (DUMPSYS, ("2.4.1", "125")),
    ("Packages:\n  versionName=1.0\n", ("1.0", "")),
    ("", ("", "")),
    ("Unable to find package: com.khong.co", ("", "")),
])
def test_doc_version_app(raw, mong_doi):
    assert parse_package_version(raw) == mong_doi


def test_version_lay_ban_dau_tien_khong_lay_ban_cu_trong_lich_su():
    """dumpsys in ca ban dang cai lan ban he thong - lay nham ban kia thi
    report ghi sai bang app da check."""
    raw = ("    versionCode=125 minSdk=24\n    versionName=2.4.1\n"
           "  Hidden system packages:\n"
           "    versionCode=1 minSdk=24\n    versionName=1.0.0\n")
    assert parse_package_version(raw) == ("2.4.1", "125")
