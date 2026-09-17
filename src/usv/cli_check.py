"""Mot luot cham: spec + package -> lai may that theo flow -> cham -> report.

Cua vao dong lenh nam o `cli_main`; o day chi co viec dieu phoi.

Nguyen tac khong duoc pha: lai hut KHONG phai FAIL. Step chet, tien de khong
dat, chua co flow - tat ca ra NOT_TESTED kem ly do. Chi FAIL khi da lai toi man
ma event sai/thieu.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cli_case_notes, event_check_runner, logcat_stream
from .adb_parsers import AdbError
from .cli_device import CliError, pick_serial
from .flow_yaml import Flow
from .check_config import ConfigError, load as load_config
from .density import ScreenMetrics
from .event_flow_run import expectations, run_flow
from .event_session import lay_mau_app
from .event_spec_models import SpecSheet
from .event_window import cut, with_expectations
from .flow_screenshots import Album
from .fa_event_parse import parse_log
from .report_event_html import build
from .report_event_shots import build_shots

VN = timezone(timedelta(hours=7))


def say(message: str) -> None:
    """Tien do -> stderr. stdout danh RIENG cho dong JSON."""
    print(message, file=sys.stderr, flush=True)


def doc_config():
    """Khong thay file config -> mac dinh, va NOI RA. Im lang thi nguoi doc
    tuong dang chay theo rule cua minh."""
    try:
        config = load_config()
    except ConfigError as exc:
        raise CliError(str(exc)) from exc
    return config


MAN_KHOA = ("Màn hình đang tắt/khoá — mọi thao tác sau đó bấm vào không khí. "
            "Mở khoá máy (và tắt chế độ tự khoá) rồi chạy lại.")


async def danh_thuc(adb, serial: str) -> None:
    """Danh thuc truoc khi chay. KHONG dat `svc power stayon usb`: do la doi
    cai dat may cua nguoi khac, va no o lai sau khi tool chay xong."""
    try:
        if not await adb.is_awake(serial):
            await adb.wake(serial)
            say("[máy] màn đang tắt — đã đánh thức")
    except AdbError:
        pass          # doc khong duoc thi cu chay, dung chan


async def ghi_chu_man_khoa(adb, serial: str, ket_qua) -> None:
    """Case hut ma man dang tat -> noi thang ly do.

    Khong noi thi bao cao chi ghi "khong thay element", va nguoi doc di soi
    selector trong khi loi that nam o cho may tu khoa man giua chung - moi case
    sau deu hut theo cung mot kieu.
    """
    try:
        if await adb.is_awake(serial):
            return
    except AdbError:
        return
    ket_qua.notes.append(MAN_KHOA)
    ket_qua.reason = f"{ket_qua.reason} — {MAN_KHOA}"


async def check(*, spec: SpecSheet, package: str, flow: Flow | None, adb,
                out_dir: Path, serial: str = "", flows_path: str = "") -> dict:
    """Chay ca luot cham. Tra payload de in JSON."""
    if not spec.ok:
        raise CliError("Spec chưa dùng được:\n  " + "\n  ".join(spec.errors))
    if flow is not None and not flow.ok:
        raise CliError("Flow chưa dùng được:\n  " + "\n  ".join(flow.errors))

    config = doc_config()
    serial = await pick_serial(adb, serial)
    say(f"[máy] {serial}")
    try:
        (width, height), density = await adb.screen_metrics(serial)
    except AdbError as exc:
        raise CliError(str(exc)) from exc
    metrics = ScreenMetrics(width_px=width, height_px=height, density=density)

    # start() tu goi enable_fa TRUOC khi mo lai app - thu tu do la bat buoc,
    # setprop chi an tu lan app khoi dong sau no.
    try:
        recording = await logcat_stream.start(adb, serial, package)
    except AdbError as exc:
        raise CliError(str(exc)) from exc
    await lay_mau_app(adb, recording)

    ten_ban, ma_ban = await adb.package_version(serial, package)
    app_version = f"{ten_ban} ({ma_ban})" if ten_ban else ""
    if app_version:
        say(f"[app] {package} {app_version}")
    album = Album(adb, serial)
    await danh_thuc(adb, serial)

    cases = []
    try:
        if flow is None or not flow.cases:
            say("[flow] chưa có case nào — chỉ ghi phiên, mọi event sẽ là chưa test")
        else:
            for order, case in enumerate(flow.cases, start=1):
                say(f"[case {order}/{len(flow.cases)}] {case.label}")
                cases.extend(await run_flow(adb, serial, metrics, package,
                                            recording, Flow(package=package,
                                                            cases=(case,)),
                                            album=album))
                trang_thai = cases[-1]
                if not trang_thai.ran:
                    await ghi_chu_man_khoa(adb, serial, trang_thai)
                    say(f"    -> {trang_thai.status}: {trang_thai.reason}")
    finally:
        await logcat_stream.stop(recording)
    await lay_mau_app(adb, recording)

    events, markers = parse_log(recording.text())
    # Case lai hut VAN chen moc (moc chen truoc khi chay step), nen van sinh
    # cua so. Giu lai thi event ban/khong ban trong cua so do bi cham that -
    # cham mot man chua bao gio lai toi.
    windows = with_expectations(
        cli_case_notes.drop_windows(cut(events, markers), cases),
        expectations(cases))
    results, summary = event_check_runner.run(
        spec, windows, config,
        fa_silent=recording.fa_silent, stream_died=recording.stream_died,
        app_seen_running=recording.app_seen,
        session_events=tuple(e for e in events if e.from_app))
    results = cli_case_notes.annotate(results, cases, flows=flows_path,
                                      co_flow=flow is not None)

    generated_at = datetime.now(VN).strftime("%d/%m/%Y %H:%M")
    html = build(spec, results, summary, package=package,
                 generated_at=generated_at, event_count=len(events),
                 fa_silent=recording.fa_silent, stream_died=recording.stream_died,
                 app_seen=recording.app_seen, foreground=recording.foreground,
                 checked_package=recording.checked_package or package,
                 near_edge=tuple(dict.fromkeys(n for w in windows
                                               for n in w.near_edge)),
                 app_version=app_version, shots=build_shots(album.shots, album.bo_bot))
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / f"report-{package}-{datetime.now(VN):%y%m%d-%H%M%S}.html"
    report.write_text(html, encoding="utf-8")
    say(f"[report] {report}")

    return {
        "report": str(report), "generated_at": generated_at,
        "package": package, "serial": serial,
        "metrics": f"{width}x{height}@{density}",
        "app_version": app_version,
        "pass": summary.passed, "fail": summary.failed,
        "not_tested": summary.not_tested,
        "not_verifiable": summary.not_verifiable, "extra": summary.extra,
        "spec_event_count": len(spec.events),
        "event_count": len(events),
        "fa_silent": recording.fa_silent, "stream_died": recording.stream_died,
        "cases": [c.payload() for c in cases],
        "results": [r.payload() for r in results],
    }
