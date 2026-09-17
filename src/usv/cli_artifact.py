"""Ghi lai link artifact cua luot cham vua publish.

Tool khong publish duoc artifact (no chay o 127.0.0.1, khong co duong toi
claude.ai) - Claude publish roi goi lenh nay de ghi lai. Xem artifact_link.

    usv-artifact --url https://claude.ai/... --generated-at "17/09/2026 15:40"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .artifact_link import doc, ghi


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usv-artifact",
        description="Ghi/đọc link artifact của lượt chấm đã publish.")
    parser.add_argument("--url", default="", help="link artifact vừa publish")
    parser.add_argument("--generated-at", default="",
                        help="mốc `generated_at` của lượt đã publish")
    parser.add_argument("--out", default="out", help="thư mục chứa artifact.json")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
