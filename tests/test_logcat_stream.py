"""Phien ghi logcat. Chay KHONG can may - AdbClient duoc thay bang ban gia.

Ba thu khong the bo:
  - THU TU cac buoc trong start(): setprop -> logcat -c -> stream -> mo app.
    Sai thu tu la mat event dau tien hoac an ca log.
  - DOC LIEN TUC. Doc luc bam moc thi giua hai lan bam khong ai doc cai ong;
    pipe OS ~64 KB, dong log ~204 byte -> day sau ~320 dong, adbd nghen roi
    log MAT AM THAM. Xem test_doc_lien_tuc_*.
  - fa_silent: phan biet "app khong ban event" voi "FA khong in log" (R3).
"""

from __future__ import annotations

import asyncio

import pytest

from usv import logcat_stream
from usv.adb_parsers import AdbError
from usv.logcat_stream import Recording, enable_fa, mark, start, stop


class FakeStdout:
    """stdout gia. GIU ONG MO khi het dong, y nhu `adb logcat` that.

    logcat khong bao gio tu EOF - no chi EOF khi process bi kill hoac khi adb
    dut. Fake cu tra b"" ngay khi het dong nen KHONG phan biet duoc hai chuyen
    nay, ma chung dan tan hai ket luan khac han:
      - stop() kill  -> EOF CO Y, phien ghi day du
      - rut may/adb dut -> EOF NGOAI Y MUON, phan con lai cua phien mat trang
    """

    def __init__(self, lines: list[bytes], *, closed: bool = False) -> None:
        self.queue = list(lines)
        self.reads = 0
        self.closed = closed
        # Dat de bung loi giua phien. Phai kiem TU BEN TRONG vong doi: gan lai
        # readline tu ngoai khong con tac dung vi pump dang ket trong lan goi
        # truoc do - y nhu stream that.
        self.error: Exception | None = None

    async def readline(self) -> bytes:
        self.reads += 1
        while True:
            await asyncio.sleep(0)      # nhuong vong lap nhu I/O that
            if self.error is not None:
                raise self.error
            if self.queue:
                return self.queue.pop(0)
            if self.closed:
                return b""


class FakeProcess:
    def __init__(self, lines: list[bytes], *, closed: bool = False) -> None:
        self.stdout = FakeStdout(lines, closed=closed)
        self.returncode = None
        self.killed = False

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
        self.stdout.closed = True       # kill lam pipe ve EOF nhu that

    async def wait(self) -> int:
        return self.returncode or 0


class FakeClient:
    def __init__(self, lines: list[bytes] | None = None, prop: str = "VERBOSE",
                 *, closed: bool = False) -> None:
        # closed=True: ong dong ngay khi het dong -> gia lap adb dut giua phien.
        self.closed = closed
        self.calls: list[str] = []
        self.props: dict[str, str] = {}
        self.logs: list[tuple[str, str]] = []
        self.lines = lines or []
        self.prop_value = prop
        self.process: FakeProcess | None = None
        self.tags: tuple[str, ...] = ()

    async def setprop(self, serial, key, value):
        self.calls.append("setprop")
        self.props[key] = value

    async def getprop(self, serial, key):
        self.calls.append("getprop")
        return self.prop_value

    async def logcat_clear(self, serial):
        self.calls.append("clear")

    async def logcat_spawn(self, serial, tags):
        self.calls.append("spawn")
        self.tags = tags
        self.process = FakeProcess(self.lines, closed=self.closed)
        return self.process

    async def shell_log(self, serial, tag, message):
        self.calls.append("log")
        self.logs.append((tag, message))

    async def force_stop(self, serial, package):
        self.calls.append("force_stop")

    async def launch(self, serial, package):
        self.calls.append("launch")


@pytest.fixture(autouse=True)
def _no_launch_wait(monkeypatch):
    """Bo thoi gian cho app khoi dong.

    Dat LAUNCH_SETTLE = 0 chu KHONG va vao asyncio.sleep: task doc nen can
    sleep(0) that de duoc nhuong vong lap.
    """
    monkeypatch.setattr(logcat_stream, "LAUNCH_SETTLE", 0)


async def _idle(times: int = 12) -> None:
    """Nhuong vong lap nhieu lan - gia lap khoang nghi giua hai buoc."""
    for _ in range(times):
        await asyncio.sleep(0)


def test_enable_fa_dat_ca_hai_property():
    client = FakeClient()
    assert asyncio.run(enable_fa(client, "S1")) is True
    assert client.props == {"log.tag.FA-SVC": "VERBOSE", "log.tag.FA": "VERBOSE"}


def test_enable_fa_bao_that_bai_khi_doc_lai_khong_dung():
    client = FakeClient(prop="")
    assert asyncio.run(enable_fa(client, "S1")) is False


def test_thu_tu_start_dung():
    """setprop TRUOC khi mo app (property doc luc process start);
    stream TRUOC khi mo app (de bat first_open/session_start)."""
    client = FakeClient()

    async def run():
        recording = await start(client, "S1", "com.x")
        await stop(recording)

    asyncio.run(run())
    order = [c for c in client.calls
             if c in {"setprop", "clear", "spawn", "force_stop", "launch"}]
    assert order.index("setprop") < order.index("spawn")
    assert order.index("clear") < order.index("spawn")
    assert order.index("spawn") < order.index("launch")
    assert order.index("force_stop") < order.index("launch")


def test_from_launch_tat_thi_khong_dong_app():
    client = FakeClient()

    async def run():
        await stop(await start(client, "S1", "com.x", from_launch=False))

    asyncio.run(run())
    assert "force_stop" not in client.calls
    assert "launch" not in client.calls


def test_loc_dung_tag_va_co_ca_USV_MARK():
    """Thieu USV_MARK trong tag la mat moc -> khong cat duoc cua so."""
    client = FakeClient()

    async def run():
        await stop(await start(client, "S1", "com.x"))

    asyncio.run(run())
    assert "USV_MARK" in client.tags
    assert "FA-SVC" in client.tags


# --- DOC LIEN TUC: chinh cai bug da sua ---

def test_doc_lien_tuc_khong_can_bam_moc():
    """Dong log den trong khoang NGHI phai duoc doc ngay.

    Day la bug da sua: truoc kia chi doc luc bam moc, nen mot khoang nghi dai
    lam pipe day va log mat am tham. Chup lines TRUOC khi stop - neu chi doc
    luc stop thi snapshot nay rong.
    """
    client = FakeClient(lines=[b"dong 1\n", b"dong 2\n", b"dong 3\n"])
    snapshot: list[str] = []

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()
        snapshot.extend(recording.lines)       # chua bam moc, chua stop
        await stop(recording)
        return recording

    asyncio.run(run())
    assert snapshot == ["dong 1", "dong 2", "dong 3"], (
        "dong den giua khoang nghi phai duoc doc ngay, khong cho den luc bam moc")


def test_task_doc_chay_ngay_tu_start():
    client = FakeClient(lines=[b"x\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        assert recording.reader is not None, "start() phai tao task doc nen"
        await stop(recording)
        assert recording.reader is None, "stop() phai don task"

    asyncio.run(run())


def test_mark_khong_doc_stream():
    """Doc o ca task nen lan trong mark() la hai ben gianh cung mot stdout."""
    client = FakeClient(lines=[b"a\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()
        before = client.process.stdout.reads
        await mark(client, recording, "buoc 1")
        assert client.process.stdout.reads == before, "mark() khong duoc doc stream"

    asyncio.run(run())


def test_stop_lay_not_phan_con_trong_pipe():
    """kill TRUOC roi moi cho task doc -> khong mat phan cuoi."""
    client = FakeClient(lines=[b"dau\n", b"cuoi\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        await stop(recording)
        return recording

    recording = asyncio.run(run())
    assert recording.lines == ["dau", "cuoi"]


def test_loi_doc_stream_khong_lam_sap_phien():
    """Phan da doc duoc van phai dung de cham check."""
    client = FakeClient(lines=[b"co ich\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()

        client.process.stdout.error = OSError("stream dut")
        await _idle()
        await stop(recording)
        return recording

    recording = asyncio.run(run())
    assert recording.lines == ["co ich"]
    assert recording.stopped is True


# --- moc va trang thai ---

def test_mark_chen_dung_tag_va_ghi_lai_nhan():
    client = FakeClient()

    async def run():
        recording = await start(client, "S1", "com.x")
        await mark(client, recording, "buoc 1")
        await stop(recording)
        return recording

    recording = asyncio.run(run())
    assert client.logs == [("USV_MARK", "buoc 1")]
    assert recording.marks == ["buoc 1"]


def test_mark_sau_khi_dung_thi_bao_loi():
    client = FakeClient()

    async def run():
        recording = await start(client, "S1", "com.x")
        await stop(recording)
        with pytest.raises(AdbError):
            await mark(client, recording, "buoc 2")

    asyncio.run(run())


def test_stop_kill_process_va_danh_dau_stopped():
    client = FakeClient(lines=[b"x\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        process = client.process
        await stop(recording)
        return recording, process

    recording, process = asyncio.run(run())
    assert process.killed is True
    assert recording.stopped is True
    assert recording.process is None


def test_fa_silent_khi_khong_co_dong_FA_nao():
    """R3: app khong in log Firebase. KHONG duoc ket luan app thieu event."""
    recording = Recording(serial="S1", package="com.x",
                          lines=["09-08 15:00:00.000 D/CHRE ( 1): rac"])
    assert recording.fa_silent is True


def test_khong_fa_silent_khi_co_dong_FA():
    recording = Recording(
        serial="S1", package="com.x",
        lines=["09-08 15:40:15.733 I/FA (1): App measurement initialized"])
    assert recording.fa_silent is False


def test_payload_noi_ra_fa_silent():
    assert Recording(serial="S1", package="com.x", lines=[]).payload()["fa_silent"] is True


# --- stream dut giua phien (rut may) ---

def test_stream_dut_giua_phien_thi_ghi_lai():
    """Rut may / adb dut -> phai GHI LAI la stream chet truoc khi bam Dung.

    Da gap that: may rot khoi USB luc 14:31, tester bam tiep 69 phut, log dong
    bang o 315 dong. Khong ghi lai thi check ket luan "app thieu event" tren
    mot phien ghi da chet - dung kieu im lang tool nay sinh ra de chan.
    """
    client = FakeClient(lines=[b"dong 1\n"], closed=True)

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()
        return recording

    recording = asyncio.run(run())
    assert recording.stream_died is True, (
        "stream EOF ma chua ai bam Dung -> phai danh dau la dut giua phien")
    assert recording.payload()["stream_died"] is True


def test_stop_binh_thuong_thi_khong_bao_dut():
    """Chieu nguoc lai: kill do stop() la EOF CO Y, khong duoc bao dut.

    Thieu test nay thi moi phien ghi binh thuong deu bi gan co "da dut", va
    canh bao keu oan thi tester hoc cach bo qua no.
    """
    client = FakeClient(lines=[b"dong 1\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()
        await stop(recording)
        return recording

    recording = asyncio.run(run())
    assert recording.stream_died is False, "stop() chu dong kill thi khong phai dut"
    assert recording.lines == ["dong 1"]


def test_loi_doc_stream_cung_tinh_la_dut():
    """Doc loi cung la mat log tu do tro di - khong khac gi EOF som."""
    client = FakeClient(lines=[b"co ich\n"])

    async def run():
        recording = await start(client, "S1", "com.x")
        await _idle()

        client.process.stdout.error = OSError("stream dut")
        await _idle()
        return recording

    recording = asyncio.run(run())
    assert recording.stream_died is True
