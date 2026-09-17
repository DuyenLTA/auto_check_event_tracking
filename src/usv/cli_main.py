"""Cua vao dong lenh cua luot cham.

    usv-check --spec <link Confluence> --package com.x
    usv-check --spec-tsv spec.tsv --package com.x --flows flows/com.x.yaml

stdout CHI co dung mot dong JSON (agent doc bang may); moi tien do di ra stderr.
Lan lon hai duong nay la agent parse JSON hong.

Tach khoi `cli_check` de cho do phinh: o day chi co doc tham so, nap file va in
ket qua; moi quyet dinh ve lai may va cham nam ben kia.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import cli_check, cli_spec_load
from .cli_device import CliError, make_client
from .flow_yaml import Flow, FlowError, load as load_flow


def doc_flow(package: str, duong_dan: str) -> tuple[Flow | None, str]:
    """Khong co file -> (None, duong dan da tim). Chua co flow KHONG phai loi:
    moi event se ra NOT_TESTED kem ly do, con hon FAIL oan ca bang."""
    path = Path(duong_dan) if duong_dan else Path("flows") / f"{package}.yaml"
    if not path.exists():
        cli_check.say(f"[flow] không thấy {path} — chưa lái được màn nào")
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
        cli_check.say(f"[spec] {nguon}: {len(spec.events)} event")
        flow, flows_path = doc_flow(args.package, args.flows)
        payload = asyncio.run(cli_check.check(
            spec=spec, package=args.package, flow=flow, adb=make_client(),
            out_dir=Path(args.out), serial=args.serial, flows_path=flows_path))
    except (CliError, cli_spec_load.SpecLoadError) as exc:
        cli_check.say(f"Lỗi: {exc}")
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
