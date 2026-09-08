"""Chan chuoi la truoc khi no di vao dong lenh adb, va bao BLOCKED ro rang khi
app khong phai build debuggable.

Chay khong can may: chi kiem phan VALIDATE, `self._run` duoc thay ban gia.
"""

from __future__ import annotations

import asyncio

import pytest

from usv.adb_appdata import AppDataMixin
from usv.adb_input import KEYEVENTS, InputMixin
from usv.adb_parsers import AdbError


class FakeRunner(InputMixin, AppDataMixin):
    """Ghi lai lenh da goi thay vi chay that."""

    adb = "/fake/adb"

    def __init__(self, out: str = "", err: str = "", code: int = 0) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.out, self.err, self.code = out, err, code

    async def _run(self, *args: str, timeout: float | None = None):
        self.calls.append(args)
        return self.out, self.err, self.code


def run(coro):
    return asyncio.run(coro)


# --- input ---

def test_tap_dung_toa_do_pixel_va_lam_tron():
    fake = FakeRunner()
    run(fake.input_tap("S1", 100.4, 200.6))
    assert fake.calls[0][-2:] == ("100", "201")


@pytest.mark.parametrize("x,y", [(-1, 10), (10, -5), (99999, 10), (10, 99999)])
def test_tap_toa_do_vo_ly_bi_tu_choi(x, y):
    with pytest.raises(AdbError):
        run(FakeRunner().input_tap("S1", x, y))


def test_swipe_ep_thoi_luong_ve_khoang_hop_ly():
    fake = FakeRunner()
    run(fake.input_swipe("S1", 0, 0, 10, 10, duration_ms=999999))
    assert fake.calls[0][-1] == "5000"
    fake = FakeRunner()
    run(fake.input_swipe("S1", 0, 0, 10, 10, duration_ms=1))
    assert fake.calls[0][-1] == "50"


@pytest.mark.parametrize("name", list(KEYEVENTS))
def test_keyevent_trong_danh_sach_trang_chay_duoc(name):
    fake = FakeRunner()
    run(fake.input_keyevent("S1", name.lower()))
    assert fake.calls[0][-1] == KEYEVENTS[name]


@pytest.mark.parametrize("name", ["POWER", "SLEEP", "KEYCODE_POWER", "; rm -rf /"])
def test_keyevent_ngoai_danh_sach_bi_tu_choi(name):
    """POWER/SLEEP lam hong ca phien test, con chuoi la thi khong duoc vao lenh."""
    with pytest.raises(AdbError):
        run(FakeRunner().input_keyevent("S1", name))


def test_go_chu_doi_khoang_trang_thanh_phan_tram_s():
    fake = FakeRunner()
    run(fake.input_text("S1", "xin chao"))
    assert fake.calls[0][-1] == "xin%schao"


@pytest.mark.parametrize("text", ["co ' nhay", 'co " nhay'])
def test_go_chu_co_dau_nhay_bi_tu_choi(text):
    with pytest.raises(AdbError):
        run(FakeRunner().input_text("S1", text))


# --- duong dan trong app ---

@pytest.mark.parametrize("path", [
    "../../etc/passwd", "/data/data/x/files/a", "files/../../x",
    "files/a; rm -rf /", "files/a b", "",
])
def test_duong_dan_khong_hop_le_bi_tu_choi(path):
    with pytest.raises(AdbError):
        FakeRunner()._check_path(path)


@pytest.mark.parametrize("path", [
    "files/frc_1:000000000000:android:0000_firebase_activate.json",
    "shared_prefs/apero_rate_prefs.xml", "files",
])
def test_duong_dan_hop_le_di_qua(path):
    assert FakeRunner()._check_path(path) == path


# --- app khong debuggable ---

def test_is_debuggable_false_khi_run_as_tu_choi():
    fake = FakeRunner(err="run-as: package not debuggable: com.x", code=1)
    assert run(fake.is_debuggable("S1", "com.x")) is False


def test_is_debuggable_true_khi_chay_duoc():
    assert run(FakeRunner(code=0).is_debuggable("S1", "com.x")) is True


def test_doc_file_app_khong_debuggable_bao_loi_kem_cach_sua():
    fake = FakeRunner(err="run-as: package not debuggable: com.x", code=1)
    with pytest.raises(AdbError) as info:
        run(fake.app_read("S1", "com.x", "files/a.json"))
    message = str(info.value)
    assert "debuggable" in message
    assert "build debug" in message, "phai noi cach sua, khong chi bao loi"


def test_khong_co_file_tra_chuoi_rong_chu_khong_no():
    """App chua fetch RC lan nao thi chua co frc_*.json - binh thuong."""
    fake = FakeRunner(err="cat: files/a.json: No such file", code=1)
    assert run(fake.app_read("S1", "com.x", "files/a.json")) == ""


def test_doc_gio_may_tra_so():
    assert run(FakeRunner(out="1757000000123\n").device_time_ms("S1")) \
        == 1757000000123


def test_doc_gio_may_that_bai_thi_bao_loi():
    """Gio host lech gio may la throttle khong an - khong duoc doan."""
    with pytest.raises(AdbError):
        run(FakeRunner(out="khong phai so", code=0).device_time_ms("S1"))
