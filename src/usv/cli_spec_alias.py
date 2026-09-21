"""`usv-spec`: xem/luu ten goi tat cua trang spec.

    usv-spec                  # danh sach ten da luu
    usv-spec rating           # ten -> link (tra Confluence neu chua luu)
    usv-spec --add rating <link>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import spec_alias
from .cli_spec_load import load_env, missing_env
from .confluence_client import ConfluenceError, fetch_page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gọi spec bằng tên chức năng thay vì dán link.")
    parser.add_argument("name", nargs="?", default="",
                        help="tên chức năng, vd rating / widget / daily checkin")
    parser.add_argument("--add", nargs=2, metavar=("TÊN", "LINK"),
                        help="lưu tên này trỏ tới link này")
    args = parser.parse_args(argv)

    load_env(Path(".env"))
    if thieu := missing_env():
        print(f"Thiếu {', '.join(thieu)} trong env.", file=sys.stderr)
        return 2

    if args.add:
        ten, link = args.add
        # Lay tieu de that tu Confluence: vua xac nhan link mo duoc, vua de
        # lan sau in ra cho nguoi doc biet minh dang cham trang nao.
        try:
            title, _ = fetch_page(link)
        except ConfluenceError as exc:
            print(f"Không mở được {link}: {exc}", file=sys.stderr)
            return 1
        spec_alias.save_entry(ten, link, title)
        print(f"{spec_alias._slug(ten)} -> {title}\n  {link}")
        return 0

    if not args.name:
        registry = spec_alias.load_registry()
        if not registry:
            print("Chưa lưu tên nào. Lưu bằng: usv-spec --add rating <link>")
            return 0
        for alias in sorted(registry):
            entry = registry[alias]
            print(f"{alias} -> {entry.get('title','')}\n  {entry['url']}")
        return 0

    try:
        url, title, nguon = spec_alias.resolve(args.name)
    except spec_alias.SpecAliasError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"{title or args.name}  ({nguon})\n  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
