"""In ra spec da parse tu mot link Confluence that, de mat nguoi doi chieu.

Vi sao can script nay: neu bang tren trang that lech format thi moi thu xay
sau (lai may, cham event, report) deu vo nghia. Kiem trong 2 phut, khong phai
sau 14 gio.

Chay:  .venv/Scripts/python.exe scripts/spike-confluence.py "<link>"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from usv.confluence_client import ConfluenceError, fetch_page  # noqa: E402
from usv.event_spec_confluence import parse_page  # noqa: E402

ENV_KEYS = ("CONFLUENCE_BASE_URL", "CONFLUENCE_TOKEN")


def load_env(path: Path) -> None:
    """KEY=VALUE -> os.environ. Bien da co san thi khong de len."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(__file__).resolve().parent.parent
    load_env(root / ".env")
    missing = [k for k in ENV_KEYS if not os.environ.get(k)]
    if missing:
        print(f"Thieu env: {', '.join(missing)} — dat trong {root / '.env'}")
        return 2

    try:
        title, html = fetch_page(sys.argv[1])
    except ConfluenceError as exc:
        # Loi mang/token/link — KHONG phai loi parse. Tach ro de khong ket
        # luan sai rang parser hong.
        print(f"[khong lay duoc trang] {exc}")
        return 1

    sheet = parse_page(html)
    print(f"Trang: {title}")
    print(f"Cot:   {' | '.join(sheet.columns) or '(khong doc duoc header)'}")
    print(f"Event: {len(sheet.events)} — param: "
          f"{sum(len(e.params) for e in sheet.events)}")
    for event in sheet.events:
        print(f"\n- {event.name}  (screen={event.screen or '-'}, "
              f"{len(event.params)} param)")
        for param in event.params:
            allowed = f" in {list(param.allowed)}" if param.allowed else ""
            print(f"    {param.name}: {param.value_type}{allowed}")
    print("\nErrors:" if sheet.errors else "\nErrors: (khong co)")
    for error in sheet.errors:
        print(f"  ! {error}")
    return 0 if sheet.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
