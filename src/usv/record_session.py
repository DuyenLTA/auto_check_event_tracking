"""Phien ghi dang do: buoc da bam nam tren dia giua hai lan goi lenh.

Vi sao phai nam tren dia: moi lenh cua `record` la mot lan goi rieng, de nguoi
(hay Claude) con nhin man that giua hai lenh. Giu trong bo nho thi moi lan goi
la mot phien moi, va khong bao gio gom du buoc thanh mot case.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .cli_device import CliError
from .flow_yaml import parse
from .flow_yaml_write import append_case

SESSION_DIR = Path("out")


def say(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def session_path(package: str, out: str) -> Path:
    return (Path(out) if out else SESSION_DIR) / f"record-{package}.json"


def doc_phien(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("steps", [])


def ghi_phien(path: Path, package: str, steps: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"package": package, "steps": steps},
                               ensure_ascii=False, indent=2), encoding="utf-8")


def luu(args, steps: list[dict]) -> int:
    """Gom buoc da bam thanh mot case roi noi vao file flow."""
    if not steps:
        raise CliError("Chưa bấm bước nào — không ghi case rỗng.")
    case_raw: dict = {"event": args.event, "steps": steps}
    if args.label:
        case_raw["label"] = args.label
    if args.expect:
        case_raw["expect_params"] = dict(p.split("=", 1) for p in args.expect)
    if args.rc or args.clear_prefs:
        case_raw["reset"] = {"remote_config": dict(p.split("=", 1) for p in args.rc),
                             "clear_prefs": list(args.clear_prefs),
                             "relaunch": True}

    # Doc lai bang chinh parser cua `check`: sai gi thi bao NGAY o day, chu
    # khong de den luc chay that moi vo.
    flow = parse({"package": args.package, "cases": [case_raw]})
    if not flow.ok:
        raise CliError("Case vừa ghi không hợp lệ:\n  " + "\n  ".join(flow.errors))

    path = Path(args.flows) if args.flows else Path("flows") / f"{args.package}.yaml"
    append_case(path, args.package, flow.cases[0])
    say(f"Đã ghi case {args.event!r} vào {path}")
    return 0
