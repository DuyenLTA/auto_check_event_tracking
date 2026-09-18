"""CLI cho tang sinh case tu spec: `dump` de doc trang, `check` de doi chieu.

Tach rieng khoi hai module kia vi chung la thu vien - web cung goi duoc. Cho
agent thi can mot cho de goi bang Bash, va can EXIT CODE: agent doc van xuoi
rat de tu cho la minh dung, nen phai co cai tra loi 0/1 dut khoat thay vi mot
doan van de agent tu dien giai.

    usv-cases dump <url>
    usv-cases check <cases.json> --url <url>
"""

from __future__ import annotations

import argparse
import json
import sys

from . import confluence_client, event_spec_confluence, spec_case_rules
from . import spec_case_skeleton, spec_prose_sections


def _check(path: str, url: str) -> int:
    raw = json.loads(open(path, encoding="utf-8").read())
    cases, parse_errors = spec_case_skeleton.parse(raw)
    _, page_html = confluence_client.fetch_page(url)
    sheet = event_spec_confluence.parse_page(page_html)
    if sheet.errors:
        print("Bảng spec trên trang tự nó đã lỗi, chưa đối chiếu được:")
        for line in sheet.errors:
            print(f"  - {line}")
        return 1

    keys = spec_prose_sections.remote_keys(page_html)
    errors = (parse_errors
              + spec_case_rules.validate(
                  cases, sheet, keys,
                  spec_prose_sections.remote_defaults(page_html))
              + spec_case_rules.chain(cases))
    gaps = spec_case_rules.missed(cases, sheet)

    print(f"{len(cases)} case đọc được, {len(sheet.events)} event trong bảng spec, "
          f"{len(keys)} remote key.")
    if errors:
        print(f"\nSAI {len(errors)}:")
        for line in errors:
            print(f"  - {line}")
    # Thu tu chay suy ra tu chuoi `sau` - in ra de nguoi doc thay no KHAC thu
    # tu dong trong file, va biet phai chay theo cai nao.
    if not errors:
        # In kem ten event that su cham: id case dat kieu "viewed-exit-click"
        # doc y het mot ten event, va nguoi doc rat de tuong tool dang cham mot
        # event khong co trong spec.
        print("\nThứ tự chạy:")
        for i, case in enumerate(spec_case_rules.order(cases), start=1):
            gia_tri = ", ".join(f"{k}={v}" for k, v
                                in case.expect_params.items())
            print(f"  {i:>2}. {case.id:<24} {case.event}"
                  + (f"  [{gia_tri}]" if gia_tri else ""))

    # In ca khi rong: "bo sot: khong" la mot ket luan, im lang thi khong phai.
    print(f"\nBỏ sót {len(gaps)}:"
          + ("".join(f"\n  - {g}" for g in gaps) if gaps else " không"))
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usv-cases",
        description="Sinh/đối chiếu khung case với bảng spec event tracking.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    dump = sub.add_parser("dump", help="đổ trang spec ra text cho agent đọc")
    dump.add_argument("url")
    check = sub.add_parser("check", help="đối chiếu case với bảng spec")
    check.add_argument("cases")
    check.add_argument("--url", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "dump":
            print(spec_prose_sections.dump(args.url))
            return 0
        return _check(args.cases, args.url)
    except confluence_client.ConfluenceError as err:
        print(f"Không đọc được trang: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
