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
# Cho task doc not phan con trong pipe sau khi kill. Khong cho mai: kill roi ma
# task khong ket thuc la co gi sai, thoi con hon treo ca server.
STOP_TIMEOUT = 5.0


@dataclass(slots=True)
class Recording:
    """Mot phien ghi dang mo."""

    serial: str
    package: str
    lines: list[str] = field(default_factory=list)
    marks: list[str] = field(default_factory=list)
    process: object | None = None
    reader: object | None = None      # asyncio.Task doc stream lien tuc
    stopped: bool = False
    # Stream chet TRUOC khi ai bam Dung: rut may, USB ngu, mat authorize.
    # Phan con lai cua phien khong duoc ghi -> KHONG duoc ket luan app thieu
    # event. Cung nguyen tac voi fa_silent. Xem _pump.
    stream_died: bool = False
    # stop() da duoc goi -> EOF sap toi la CO Y, khong phai dut.
    stopping: bool = False

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
                "stopped": self.stopped, "fa_silent": self.fa_silent,
                "stream_died": self.stream_died}


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
    # Bat doc NGAY, truoc khi mo app: khong thi event dau tien (first_open,
    # session_start) ban ra ma chua ai doc.
    recording.reader = asyncio.create_task(_pump(recording))

    if from_launch and package:
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)
    return recording


async def _pump(recording: Recording) -> None:
    """Doc stream LIEN TUC vao `recording.lines`, tu luc start den luc stop.

    Phai chay nen chu KHONG doc luc bam moc. Doc luc bam moc thi giua hai lan
    bam khong ai doc cai ong: pipe cua OS chi khoang 64 KB, dong log trung binh
    204 byte -> day sau ~320 dong. Day thi adbd nghen, tut lai sau ring buffer,
    va log BI MAT AM THAM.

    Do that: mot lan mo app cua AIP922 sinh 1 259 dong sau khi da loc tag. Nen
    mot khoang nghi dai giua hai buoc la du de mat dong - va mat am tham thi
    report sai ma khong ai biet.

    Loi doc KHONG lam sap phien ghi: bao ra qua log roi dung, phan da doc duoc
    van dung de cham check.
    """
    process = recording.process
    if process is None or process.stdout is None:
        return
    try:
        while True:
            raw = await process.stdout.readline()
            if not raw:            # EOF - process da dung
                if not recording.stopping:
                    # Chua ai bam Dung ma ong da dong -> adb dut. Ghi lai:
                    # khong ghi thi phien ghi chet am tham, va check ket luan
                    # "app thieu event" tren du lieu chi co phan dau.
                    recording.stream_died = True
                    log.warning(
                        "Stream logcat dut truoc khi Dung ghi - chi doc duoc "
                        "%d dong.", len(recording.lines))
                return
            recording.lines.append(raw.decode("utf-8", "replace").rstrip("\n"))
    except asyncio.CancelledError:
        raise
    except Exception as exc:       # noqa: BLE001 - doc log hong khong duoc lam sap phien
        # Doc loi = mat log tu day tro di, khong khac gi EOF som.
        if not recording.stopping:
            recording.stream_died = True
        log.warning("Doc stream logcat that bai: %s", exc)


async def mark(client, recording: Recording, label: str) -> None:
    """Chen moc vao logcat. MOT nut mot buoc: moc sau la diem ket cua buoc truoc."""
    if recording.stopped:
        raise AdbError("Phien ghi da dung - khong chen moc duoc nua.")
    # KHONG doc stream o day - task nen dang doc lien tuc. Doc o ca hai cho la
    # hai ben gianh cung mot stdout.
    await client.shell_log(recording.serial, MARK_TAG, label)
    recording.marks.append(label)


async def stop(recording: Recording) -> Recording:
    """Dung ghi. Luon kill process du co loi.

    Thu tu: kill TRUOC roi moi cho task doc. Kill lam stdout ve EOF nen `_pump`
    doc het phan con dong trong pipe roi tu ket thuc - khong mat dong nao. Huy
    task truoc khi kill thi mat dung phan cuoi.
    """
    # Bao truoc y dinh TRUOC khi kill: kill lam stdout ve EOF, va `_pump` phai
    # biet EOF do la co y - khong thi moi lan Dung binh thuong deu bi gan co
    # "da dut", canh bao keu oan thi tester hoc cach bo qua no.
    recording.stopping = True
    process = recording.process
    if process is not None and process.returncode is None:
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass

    reader = recording.reader
    if reader is not None:
        try:
            await asyncio.wait_for(reader, timeout=STOP_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            reader.cancel()
        except Exception as exc:  # noqa: BLE001
            log.warning("Task doc logcat ket thuc voi loi: %s", exc)
    recording.reader = None
    recording.process = None
    recording.stopped = True
    return recording
