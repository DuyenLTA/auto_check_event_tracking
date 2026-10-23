"""Cua vao dong lenh cua luot cham.

    usv-check --spec rating --package com.x        # ten chuc nang
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
import time
from pathlib import Path

from . import cli_chay_lai, cli_check, cli_check_merge, cli_spec_load, discord_notify
from .run_message import build_run_message
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="usv-check",
        description="Chấm event tracking: spec + máy thật -> report HTML.")
    parser.add_argument("--spec", default="",
                        help="link Confluence, hoặc tên chức năng "
                             "(rating, widget, daily checkin)")
    parser.add_argument("--spec-tsv", default="", help="file TSV dán tay")
    parser.add_argument("--package", required=True)
    parser.add_argument("--flows", default="",
                        help="file flow YAML (mặc định flows/<package>.yaml)")
    parser.add_argument("--out", default="out", help="thư mục ghi report")
    parser.add_argument("--serial", default="", help="chọn máy khi cắm nhiều máy")
    parser.add_argument("--case", action="append", default=[],
                        help="chỉ chạy case có nhãn/tên event khớp chuỗi này "
                             "(lặp được). Case tiền đề được kéo theo.")
    parser.add_argument("--base", default="",
                        help="stdout JSON của lượt đầy đủ trước: kết quả chạy lẻ "
                             "--case được gộp vào đó, report ra đủ mọi event")
    parser.add_argument("--khong-claude", action="store_true",
                        help="chạy không có agent: tự chạy lại case hụt, event chưa "
                             "chấm được ghi 'Cần người xem', Discord đính kèm report")
    parser.add_argument("--tu-chay-lai", type=int, default=None, metavar="N",
                        help="số lần tự chạy lại case lái hụt (mặc định 1 khi "
                             "--khong-claude, 0 khi không)")
    return parser


def parse_args(argv: list[str] | None):
    return build_parser().parse_args(argv)


def ep_utf8() -> None:
    """Console Windows mac dinh cp1252 - moi chu tieng Viet in ra la
    UnicodeEncodeError, ke ca dong `--help`. Ep UTF-8 TRUOC khi in bat cu gi."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass          # stream bi thay the (pytest capture) - khong sao


def thong_bao_discord(payload: dict) -> None:
    """Mot tin Discord cho moi lan chay. Hong o day khong duoc doi ket qua luot cham.

    Khong co Claude thi khong ai publish artifact: dinh kem chinh file report de
    team mo duoc tu Discord.
    """
    try:
        cli_spec_load.load_env(Path(".env"))
        kind, title, lines, action = build_run_message(
            payload, payload.get("duration_s"))
        dinh_kem = Path(payload["report"]) if (payload.get("khong_claude")
                                               and payload.get("report")) else None
        discord_notify.send(kind, title, lines, action, file=dinh_kem)
    except Exception as exc:  # noqa: BLE001 - thong bao la tien nghi, khong duoc nem
        cli_check.say(f"discord: bỏ qua thông báo ({type(exc).__name__})")


def main(argv: list[str] | None = None) -> int:
    ep_utf8()
    args = parse_args(argv)
    bat_dau = time.monotonic()
    try:
        spec, nguon = cli_spec_load.load(
            url=args.spec, tsv=Path(args.spec_tsv) if args.spec_tsv else None,
            env_file=Path(".env"))
        cli_check.say(f"[spec] {nguon}: {len(spec.events)} event")
        flow, flows_path = doc_flow(args.package, args.flows)

        def mot_luot(chi_case: tuple[str, ...], base, chinh_xac: bool = False):
            # Client moi cho moi asyncio.run: client cu co the giu tai nguyen
            # cua event loop da dong.
            return asyncio.run(cli_check.check(
                spec=spec, package=args.package, flow=flow, adb=make_client(),
                out_dir=Path(args.out), serial=args.serial, flows_path=flows_path,
                chi_case=chi_case, base=base, khong_claude=args.khong_claude,
                chinh_xac=chinh_xac))

        payload = mot_luot(tuple(args.case), cli_check_merge.doc_base(Path(args.base))
                           if args.base else None)
        so_lan = args.tu_chay_lai if args.tu_chay_lai is not None else (
            1 if args.khong_claude else 0)
        for lan in range(1, max(so_lan, 0) + 1):
            hut = cli_chay_lai.case_hut(payload)
            if not hut:
                break
            cli_check.say(f"[chạy lại {lan}/{so_lan}] {len(hut)} case hụt: "
                          + " | ".join(hut))
            try:
                base = cli_check_merge.doc_base(cli_chay_lai.ghi_base(payload))
                payload = mot_luot(hut, base, chinh_xac=True)
            except (CliError, cli_check_merge.MergeError, OSError) as exc:
                # Lan chay lai hong (rut cap, may khoa sau 30 phut) khong duoc
                # lam mat ket qua cua luot day du da co: giu payload truoc do.
                cli_check.say(f"[chạy lại {lan}/{so_lan}] bỏ dở, giữ kết quả lượt trước: {exc}")
                break
    except (CliError, cli_spec_load.SpecLoadError, cli_check_merge.MergeError) as exc:
        cli_check.say(f"Lỗi: {exc}")
        return 1
    payload["duration_s"] = round(time.monotonic() - bat_dau, 1)
    print(json.dumps(payload, ensure_ascii=False))
    thong_bao_discord(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
