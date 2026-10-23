"""Ghi lai link artifact cua luot cham vua publish.

Tool khong publish duoc artifact (no chay o 127.0.0.1, khong co duong toi
claude.ai) - Claude publish roi goi lenh nay de ghi lai. Xem artifact_link.

    usv-artifact --url https://claude.ai/... --generated-at "17/09/2026 15:40"

Co them `--package --version --pass --fail --duration-s` (lay tu stdout JSON cua
usv-check) thi con tu them mot dong vao docs/usage-log.md. Co --url thi luon gui
Discord "report da publish" (hong thi bo qua, khong doi exit code).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import discord_notify, usage_log
from .artifact_link import doc, ghi
from .cli_spec_load import load_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usv-artifact",
        description="Ghi/đọc link artifact của lượt chấm đã publish.")
    parser.add_argument("--url", default="", help="link artifact vừa publish")
    parser.add_argument("--generated-at", default="",
                        help="mốc `generated_at` của lượt đã publish")
    parser.add_argument("--out", default="out", help="thư mục chứa artifact.json")
    parser.add_argument("--package", default="", help="package app (để ghi usage-log)")
    parser.add_argument("--version", default="", help="app_version trong JSON")
    parser.add_argument("--pass", dest="passed", type=int, default=None)
    parser.add_argument("--fail", type=int, default=None)
    parser.add_argument("--duration-s", type=float, default=None,
                        help="duration_s trong JSON của lượt chấm")
    parser.add_argument("--usage-log", default=str(usage_log.DEFAULT_PATH),
                        help="file log sử dụng (mặc định docs/usage-log.md)")
    args = parser.parse_args(argv)

    goc = Path(args.out)
    if not args.url:
        print(json.dumps(doc(goc), ensure_ascii=False))
        return 0
    if not args.generated_at:
        # Thieu moc thi nut artifact luon trong nhu moi, va bao cao cu bi gui
        # cho team nhu bao cao cua lan chay vua roi.
        print("Lỗi: có --url thì phải có --generated-at.", file=sys.stderr)
        return 1
    print(json.dumps(ghi(args.url, args.generated_at, goc), ensure_ascii=False))
    sau_khi_ghi(args)
    return 0


def sau_khi_ghi(args) -> None:
    """Usage-log + Discord. Chi la tien nghi: loi o day khong duoc lam hong lenh."""
    try:
        load_env(Path(".env"))
        co_so_lieu = (args.package and args.passed is not None
                      and args.fail is not None and args.duration_s is not None)
        if co_so_lieu:
            row = usage_log.build_row(
                package=args.package, version=args.version, passed=args.passed,
                failed=args.fail, duration_s=args.duration_s, url=args.url)
            if usage_log.append_row(Path(args.usage_log), row):
                print(f"[usage-log] đã thêm dòng vào {args.usage_log}", file=sys.stderr)
        elif args.package:
            print("[usage-log] thiếu --pass/--fail/--duration-s, bỏ qua", file=sys.stderr)
        ten = f"{args.package} {args.version}".strip() or "app"
        lines = [f"{args.passed} khớp / {args.fail} sai"] if co_so_lieu else []
        discord_notify.send("done", f"Report đã publish · {ten}", lines, link=args.url)
    except (OSError, ValueError) as exc:
        print(f"[usage-log] bỏ qua ({type(exc).__name__}: {exc})", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
