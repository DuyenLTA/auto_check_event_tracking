"""Mot lenh: spec + package -> lai may that theo flow -> cham -> report HTML.

    python -m usv.cli_check --spec <link Confluence> --package com.x
    python -m usv.cli_check --spec-tsv spec.tsv --package com.x --flows f.yaml

stdout CHI co dung mot dong JSON (agent doc bang may); moi tien do di ra stderr.
Lan lon hai duong nay la agent parse JSON hong.

Nguyen tac khong duoc pha: lai hut KHONG phai FAIL. Step chet, tien de khong
dat, chua co flow - tat ca ra NOT_TESTED kem ly do. Chi FAIL khi da lai toi man
ma event sai/thieu.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cli_case_notes, cli_spec_load, event_check_runner, logcat_stream
from .adb_parsers import AdbError
from .cli_device import CliError, make_client, pick_serial
from .check_config import ConfigError, load as load_config
from .density import ScreenMetrics
from .event_flow_run import expectations, run_flow
from .event_session import lay_mau_app
from .event_spec_models import SpecSheet
from .event_window import cut, with_expectations
from .fa_event_parse import parse_log
from .flow_yaml import Flow, FlowError, load as load_flow
from .report_event_html import build

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

    cases = []
    try:
        if flow is None or not flow.cases:
            say("[flow] chưa có case nào — chỉ ghi phiên, mọi event sẽ là chưa test")
        else:
            for order, case in enumerate(flow.cases, start=1):
                say(f"[case {order}/{len(flow.cases)}] {case.label}")
                cases.extend(await run_flow(adb, serial, metrics, package,
                                            recording, Flow(package=package,
                                                            cases=(case,))))
                trang_thai = cases[-1]
                if not trang_thai.ran:
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
                                               for n in w.near_edge)))
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / f"report-{package}-{datetime.now(VN):%y%m%d-%H%M%S}.html"
    report.write_text(html, encoding="utf-8")
    say(f"[report] {report}")

    return {
        "report": str(report), "generated_at": generated_at,
        "package": package, "serial": serial,
        "metrics": f"{width}x{height}@{density}",
        "pass": summary.passed, "fail": summary.failed,
        "not_tested": summary.not_tested,
        "not_verifiable": summary.not_verifiable, "extra": summary.extra,
        "spec_event_count": len(spec.events),
        "event_count": len(events),
        "fa_silent": recording.fa_silent, "stream_died": recording.stream_died,
        "cases": [c.payload() for c in cases],
        "results": [r.payload() for r in results],
    }


def doc_flow(package: str, duong_dan: str) -> tuple[Flow | None, str]:
    """Khong co file -> (None, duong dan da tim). Chua co flow KHONG phai loi:
    moi event se ra NOT_TESTED kem ly do, con hon FAIL oan ca bang."""
    path = Path(duong_dan) if duong_dan else Path("flows") / f"{package}.yaml"
    if not path.exists():
        say(f"[flow] không thấy {path} — chưa lái được màn nào")
        return None, str(path)
    try:
        return load_flow(path), str(path)
    except FlowError as exc:
        raise CliError(str(exc)) from exc


def parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(
        prog="usv-check",
        description="Chấm event tracking: spec + máy thật -> report HTML.")
    parser.add_argument("--spec", default="", help="link trang Confluence")
    parser.add_argument("--spec-tsv", default="", help="file TSV dán tay")
    parser.add_argument("--package", required=True)
    parser.add_argument("--flows", default="",
                        help="file flow YAML (mặc định flows/<package>.yaml)")
    parser.add_argument("--out", default="out", help="thư mục ghi report")
    parser.add_argument("--serial", default="", help="chọn máy khi cắm nhiều máy")
    return parser.parse_args(argv)


def ep_utf8() -> None:
    """Console Windows mac dinh cp1252 - moi chu tieng Viet in ra la
    UnicodeEncodeError, ke ca dong `--help`. Ep UTF-8 TRUOC khi in bat cu gi."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass          # stream bi thay the (pytest capture) - khong sao


def main(argv: list[str] | None = None) -> int:
    ep_utf8()
    args = parse_args(argv)
    try:
        spec, nguon = cli_spec_load.load(
            url=args.spec, tsv=Path(args.spec_tsv) if args.spec_tsv else None,
            env_file=Path(".env"))
        say(f"[spec] {nguon}: {len(spec.events)} event")
        flow, flows_path = doc_flow(args.package, args.flows)
        payload = asyncio.run(check(
            spec=spec, package=args.package, flow=flow, adb=make_client(),
            out_dir=Path(args.out), serial=args.serial, flows_path=flows_path))
    except (CliError, cli_spec_load.SpecLoadError) as exc:
        say(f"Lỗi: {exc}")
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
