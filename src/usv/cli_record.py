"""Ghi flow CO NGUOI NGOI XEM: đọc màn, bấm thử, chốt, lưu thành case YAML.

    usv-record --package com.x dump
    usv-record --package com.x tap --id btnStart
    usv-record --package com.x save --event widget_show --label "tại home"

Moi lenh la mot lan goi rieng, buoc da bam giu trong `out/record-<pkg>.json`.
Lam vay de nguoi (hay Claude) nhin man that giua hai lenh - do la ca diem cua
che do nay. `check` khong bao gio tu mo UI ra mo: AI bam loan tren may that co
the mua hang, gui form, dang xuat.

Uu tien selector: resource_id > desc > text. Khop theo chu thi vo ngay lan app
doi ngon ngu, nen dung `text` la co canh bao.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .ad_close import tim_nut_dong
from .adb_foreground_parse import la_man_quang_cao
from .quyen_he_thong import tim_nut_cho_phep
from .adb_parsers import AdbError
from .cli_device import CliError, make_client, pick_serial
from .density import ScreenMetrics
from .device_actions import Selector, swipe, tap
from .flow_yaml import FlowError
from .record_session import doc_phien, ghi_phien, luu, say, session_path
from .ui_dump import parse_dump
from .ui_dump_brief import brief


def selector_tu_args(args) -> Selector | None:
    if args.id:
        return Selector(resource_id=args.id, index=args.index)
    if args.desc:
        return Selector(desc=args.desc, index=args.index)
    if getattr(args, "cls", ""):
        return Selector(cls=args.cls, index=args.index)
    if args.text:
        # Canh bao, khong chan: nhieu man khong co resource_id nao dung duoc.
        say("Cảnh báo: selector khoá bằng chữ sẽ vỡ khi app đổi ngôn ngữ — "
            "tìm resource_id trước khi chốt.")
        return Selector(text=args.text, index=args.index)
    return None


def _them_tuy_chon(buoc: dict, args) -> dict:
    if args.optional:
        buoc["optional"] = True
    return buoc


async def _nodes(adb, serial: str):
    (width, height), density = await adb.screen_metrics(serial)
    metrics = ScreenMetrics(width_px=width, height_px=height, density=density)
    return parse_dump(await adb.dump_ui(serial), metrics)


async def lam(args) -> tuple[int, list[dict]]:
    """Chay mot lenh. Tra (ma thoat, buoc moi them - rong neu khong them)."""
    adb = make_client()
    serial = await pick_serial(adb, args.serial)

    if args.lenh == "dump":
        for line in brief(await _nodes(adb, serial)):
            print(line)
        return 0, []

    if args.lenh == "launch":
        await adb.force_stop(serial, args.package)
        await adb.launch(serial, args.package)
        return 0, [{"kind": "launch"}]

    if args.lenh == "back":
        await adb.input_keyevent(serial, "KEYCODE_BACK")
        return 0, [{"kind": "key", "text": "KEYCODE_BACK"}]

    if args.lenh == "type":
        await adb.input_text(serial, args.chu)
        return 0, [{"kind": "type", "text": args.chu}]

    if args.lenh == "wait":            # cho cung, khong dong vao may
        return 0, [{"kind": "wait", "seconds": args.giay}]

    if args.lenh == "allow":
        node = tim_nut_cho_phep(await _nodes(adb, serial))
        if node is None:
            say("Không thấy dialog quyền nào.")
        else:
            box = node.bounds_px
            await adb.input_tap(serial, (box.left + box.right) / 2,
                                (box.top + box.bottom) / 2)
            say(f"Đã cấp quyền bằng {node.label}")
        return 0, [{"kind": "allow"}]

    if args.lenh == "close-ad":
        # Trong man quang cao thi "Close" mot chu chac chan la nut dong quang
        # cao; o man app thi chinh no cung la nut dong popup cua app.
        man_ads = la_man_quang_cao(await adb.top_activity(serial))
        node = tim_nut_dong(await _nodes(adb, serial), man_ads=man_ads)
        if node is None:
            say("Không thấy nút đóng quảng cáo nào — màn đang sạch.")
        else:
            box = node.bounds_px
            await adb.input_tap(serial, (box.left + box.right) / 2,
                                (box.top + box.bottom) / 2)
            say(f"Đã đóng quảng cáo bằng {node.label}")
        return 0, [{"kind": "close_ad"}]

    if args.lenh == "wait-text":
        return 0, [_them_tuy_chon({"kind": "wait_text", "text": args.chu,
                                   "timeout": args.timeout}, args)]

    chon = selector_tu_args(args)
    if chon is None:
        raise CliError("Cần một selector: --id | --desc | --text.")

    if args.lenh == "tap":
        node = await tap(adb, serial, await _nodes(adb, serial), chon)
        say(f"Đã bấm {node.label}")
        return 0, [_them_tuy_chon({"kind": "tap", chon.kind: chon.needle,
                               "index": chon.index}, args)]

    node = await swipe(adb, serial, await _nodes(adb, serial), chon, args.huong)
    say(f"Đã quét {args.huong} trên {node.label}")
    return 0, [_them_tuy_chon({"kind": "swipe", chon.kind: chon.needle,
                               "index": chon.index, "direction": args.huong}, args)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="usv-record",
        description="Ghi flow có người ngồi xem: bấm thử rồi lưu thành case.")
    parser.add_argument("--package", required=True)
    parser.add_argument("--serial", default="")
    parser.add_argument("--out", default="", help="thư mục giữ phiên đang ghi")
    for ten in ("--id", "--text", "--desc"):
        parser.add_argument(ten, default="")
    # `--cls` la loi thoat cuoi cung: node khong co id/chu/desc nao (o nhap
    # tron, container cua nut) thi khong selector nao kia cham toi duoc.
    parser.add_argument("--cls", default="",
                        help="tên lớp, vd EditText — dùng khi node không có "
                             "id/chữ/desc")
    parser.add_argument("--index", type=int, default=0,
                        help="node thứ mấy trong số các node khớp")
    parser.add_argument("lenh", choices=["dump", "tap", "swipe", "back", "launch",
                                         "type", "wait", "wait-text", "close-ad", "allow",
                                         "show", "save", "drop"])
    parser.add_argument("giay_hoac_chu", nargs="?", default="")
    parser.add_argument("--huong", default="up", help="swipe: up|down|left|right")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--optional", action="store_true",
                        help="bước có thể không xuất hiện (quảng cáo, popup)")
    parser.add_argument("--event", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--flows", default="")
    parser.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--rc", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--clear-prefs", action="append", default=[], metavar="FILE")
    return parser


def parse_args(argv: list[str] | None):
    args = build_parser().parse_args(argv)
    args.chu = args.giay_hoac_chu
    # Cung mot o positional: `wait 3` doc la so giay, `wait-text "Add Widget"`
    # doc la chu. Ep float vo dieu kien thi moi lenh nhan chu deu no ValueError
    # ngay o tang doc tham so - da gap that voi `wait-text`.
    args.giay = 1.0
    if args.lenh == "wait":
        try:
            args.giay = float(args.giay_hoac_chu or 1)
        except ValueError:
            build_parser().error(
                f"`wait` cần số giây, đang nhận {args.giay_hoac_chu!r}.")
    return args


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = parse_args(argv)
    path = session_path(args.package, args.out)
    steps = doc_phien(path)

    try:
        if args.lenh == "drop":
            path.unlink(missing_ok=True)
            say("Đã bỏ phiên đang ghi.")
            return 0
        if args.lenh == "show":
            print(json.dumps(steps, ensure_ascii=False, indent=2))
            return 0
        if args.lenh == "save":
            ma = luu(args, steps)
            path.unlink(missing_ok=True)      # xong case thi don, khong dinh sang case sau
            return ma
        ma, them = asyncio.run(lam(args))
    except (CliError, AdbError, FlowError) as exc:
        say(f"Lỗi: {exc}")
        return 1
    if them:
        ghi_phien(path, args.package, steps + them)
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
