"""Phien ghi logcat: bat log Firebase, mo stream, chen marker, dung.

Ba cai bay da do that, chan san o day:

R2 `setprop` KHONG song qua reboot, va app phai KHOI DONG LAI sau khi dat vi
   property duoc doc luc process start. Nen `start()` luon dat lai property, va
   `from_launch=True` (mac dinh) tu force-stop roi mo lai app.

R3 Build release co the strip log Firebase. Phai phan biet "app khong ban event"
   voi "FA khong in log": khong co MOT dong FA-SVC nao trong ca phien ->
   `fa_silent=True`. Bao "khong doc duoc FA" chu khong bao app thieu event.

Loc o tang TAG (`adb logcat -s FA-SVC USV_MARK`) chu khong grep tren host: loc
ngay tren dien thoai nen tiet kiem ca duong truyen. Do: 12 964 -> 1 259 dong.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from .adb_logcat import FA_TAG, MARK_TAG
from .adb_parsers import AdbError

log = logging.getLogger(__name__)

FA_PROP = "log.tag.FA-SVC"
# Bat luon tag FA: no khong cho event nhung cho biet FA con song (R3), va o mot
# so version SDK chinh no in `Logging event (FE)`.
FA_PROP_ALT = "log.tag.FA"
VERBOSE = "VERBOSE"
TAGS = (FA_TAG, "FA", MARK_TAG)

# Cho app kip khoi dong lai truoc khi tester lam dong tac dau tien.
LAUNCH_SETTLE = 1.5
# Doc stream theo dong; het thoi gian nay ma khong co dong nao thi thoi, khong
# treo mai.
READ_IDLE = 0.4


@dataclass(slots=True)
class Recording:
    """Mot phien ghi dang mo."""

    serial: str
    package: str
    lines: list[str] = field(default_factory=list)
    marks: list[str] = field(default_factory=list)
    process: object | None = None
    stopped: bool = False

    @property
    def fa_silent(self) -> bool:
        """Khong co dong FA nao -> khong doc duoc log Firebase (R3).

        Khac han "app khong ban event": voi truong hop nay tuyet doi KHONG duoc
        ket luan app thieu event.
        """
        return not any("/FA" in line for line in self.lines)

    def text(self) -> str:
        return "\n".join(self.lines)

    def payload(self) -> dict:
        return {"serial": self.serial, "package": self.package,
                "line_count": len(self.lines), "marks": list(self.marks),
                "stopped": self.stopped, "fa_silent": self.fa_silent}


async def enable_fa(client, serial: str) -> bool:
    """Bat log Firebase. Tra True neu doc lai dung VERBOSE."""
    await client.setprop(serial, FA_PROP, VERBOSE)
    await client.setprop(serial, FA_PROP_ALT, VERBOSE)
    got = await client.getprop(serial, FA_PROP)
    if got.strip().upper() != VERBOSE:
        log.warning("setprop %s khong an: doc lai duoc %r", FA_PROP, got)
        return False
    return True


async def start(client, serial: str, package: str, *,
                from_launch: bool = True) -> Recording:
    """Bat dau ghi. Thu tu QUAN TRONG, khong doi duoc.

    1. setprop  - phai truoc khi app start, property doc luc process start
    2. logcat -c - xoa log cu, khong thi event cua lan truoc lan vao
    3. mo stream - phai truoc khi app ban event dau tien
    4. mo app   - de bat duoc ca first_open / session_start / app_shortcut
    """
    await enable_fa(client, serial)
    await client.logcat_clear(serial)
    process = await client.logcat_spawn(serial, TAGS)
    recording = Recording(serial=serial, package=package, process=process)

    if from_launch and package:
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)
    return recording


async def drain(recording: Recording) -> None:
    """Doc het dong dang cho trong stream vao `recording.lines`."""
    process = recording.process
    if process is None or process.stdout is None:
        return
    while True:
        try:
            raw = await asyncio.wait_for(process.stdout.readline(), timeout=READ_IDLE)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            return
        if not raw:
            return
        recording.lines.append(raw.decode("utf-8", "replace").rstrip("\n"))


async def mark(client, recording: Recording, label: str) -> None:
    """Chen moc vao logcat. MOT nut mot buoc: moc sau la diem ket cua buoc truoc."""
    if recording.stopped:
        raise AdbError("Phien ghi da dung - khong chen moc duoc nua.")
    await drain(recording)
    await client.shell_log(recording.serial, MARK_TAG, label)
    recording.marks.append(label)


async def stop(recording: Recording) -> Recording:
    """Dung ghi, doc not phan con lai. Luon kill process du co loi."""
    await drain(recording)
    process = recording.process
    if process is not None and process.returncode is None:
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass
    recording.process = None
    recording.stopped = True
    return recording
