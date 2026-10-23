"""Thong bao Discord qua Webhook. Chi dung stdlib.

Nguyen tac: thong bao la TIEN NGHI, khong bao gio duoc lam hong luot cham.
`send` khong raise, khong doi exit code, khong in gi ra stdout (stdout cua
usv-check phai la dung mot dong JSON). Loi chi ra stderr, va KHONG BAO GIO in
URL webhook (URL la bi mat).

    DISCORD_WEBHOOK_URL   URL Webhook (env hoac .env)
    DISCORD_NOTIFY=0      tat han (test/CI)

CLI cho slash command dung o cac cho agent dung lai:
    usv-notify --kind stop --title "..." --line "..." --action "..." [--link URL]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

KINDS = {"stop": "⛔", "done": "✅", "bug": "🐞"}
TIMEOUT_S = 5
# Upload report vai MB qua mang cham: 5s la het gio giua chung.
TIMEOUT_FILE_S = 60
MAX_CONTENT = 2000
# Webhook Discord nhan file toi 10 MiB (server khong boost). Chua le cho phan
# con lai cua body multipart.
MAX_FILE = 9 * 1024 * 1024
# Cloudflare truoc Discord chan User-Agent mac dinh Python-urllib.
USER_AGENT = "qa-workflow-bot/1.0"


def _warn(message: str) -> None:
    print(f"discord: {message}", file=sys.stderr)


def _cat_2000(text: str) -> str:
    """Discord tu choi content > 2000 ky tu: cat theo dong roi them "…"."""
    if len(text) <= MAX_CONTENT:
        return text
    cat = text[:MAX_CONTENT - 1]
    if "\n" in cat:
        cat = cat.rsplit("\n", 1)[0]
    return cat + "…"


def format_text(kind: str, title: str, lines: list[str] | tuple[str, ...],
                action: str | None = None, link: str | None = None) -> str:
    """Noi dung tin nhan (Discord markdown). Format dung chung voi cac repo khac."""
    if kind not in KINDS:
        raise ValueError(f"kind phải là một trong {sorted(KINDS)}, nhận '{kind}'")
    parts = [f"{KINDS[kind]} **check-event** · {title}", *lines]
    if action:
        parts.append(f"→ {action}")
    if link:
        # <...> trong ngoac don chan Discord dung embed xem truoc.
        parts.append(f"[Mở report](<{link}>)")
    return _cat_2000("\n".join(parts))


def _doc_dinh_kem(file: Path | None) -> tuple[bytes | None, str]:
    """-> (noi dung file, dong ghi chu them vao tin). File qua lon / doc hong thi
    van gui tin, chi ghi duong dan local - mat tin vi file la mat ca thong bao."""
    if file is None:
        return None, ""
    try:
        if file.stat().st_size > MAX_FILE:
            return None, f"Report quá lớn để đính kèm, mở trên máy chạy: {file}"
        return file.read_bytes(), ""
    except OSError:
        return None, f"Không đọc được report để đính kèm: {file}"


def _multipart(payload: dict, file_name: str, data: bytes) -> tuple[bytes, str]:
    """Body multipart/form-data Discord doc: `payload_json` + `files[0]`."""
    ranh = uuid.uuid4().hex
    crlf = "\r\n"
    dau = (f"--{ranh}{crlf}"
           f'Content-Disposition: form-data; name="payload_json"{crlf}'
           f"Content-Type: application/json{crlf}{crlf}"
           + json.dumps(payload, ensure_ascii=False)
           + f"{crlf}--{ranh}{crlf}"
           f'Content-Disposition: form-data; name="files[0]"; filename="{file_name}"{crlf}'
           f"Content-Type: text/html{crlf}{crlf}").encode("utf-8")
    return dau + data + f"{crlf}--{ranh}--{crlf}".encode("utf-8"), ranh


def send(kind: str, title: str, lines: list[str] | tuple[str, ...] = (),
         action: str | None = None, link: str | None = None,
         file: Path | None = None) -> bool:
    """Gui mot tin. True khi Discord nhan (2xx). Moi loi -> False, khong raise.

    `file`: dinh kem file (report HTML) - dung khi khong co Claude publish artifact.
    """
    if os.environ.get("DISCORD_NOTIFY", "").strip() == "0":
        return False
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        _warn("DISCORD_WEBHOOK_URL chưa đặt, bỏ qua thông báo")
        return False
    try:
        def noi_dung(dong) -> dict:
            return {"content": format_text(kind, title, dong, action, link),
                    "allowed_mentions": {"parse": ["roles", "users"]}}

        data, ghi_chu = _doc_dinh_kem(file)
        if ghi_chu:
            lines = [*lines, ghi_chu]
        if data is not None:
            if _post(url, noi_dung(lines), (_ten_file(file), data)):
                return True
            # Upload hong (mang cham, file lon) khong duoc lam mat ca tin.
            _warn("gửi kèm report hỏng, gửi lại tin không kèm file")
            lines = [*lines, f"Không gửi kèm được report, mở trên máy chạy: {file}"]
        return _post(url, noi_dung(lines), None)
    except ValueError as exc:
        _warn(f"không gửi được ({type(exc).__name__})")
        return False


def _ten_file(file: Path) -> str:
    """Ten file an toan cho header Content-Disposition (khong dau, khong nhay)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", file.name) or "report.html"


def _post(url: str, payload: dict, dinh_kem: tuple[str, bytes] | None) -> bool:
    """Mot request toi webhook. True khi 2xx; moi loi -> False, khong raise."""
    try:
        if dinh_kem is not None:
            body, ranh = _multipart(payload, *dinh_kem)
            loai = f"multipart/form-data; boundary={ranh}"
        else:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            loai = "application/json"
        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": loai, "User-Agent": USER_AGENT})
        timeout = TIMEOUT_FILE_S if dinh_kem is not None else TIMEOUT_S
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        _warn(f"webhook trả HTTP {exc.code}, không gửi được")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # str(exc) cua URLError/ValueError co the chua URL -> chi in ten loi.
        _warn(f"không gửi được ({type(exc).__name__})")
    return False


def main(argv: list[str] | None = None) -> int:
    """usv-notify. Luon tra 0: gui hong khong duoc lam hong slash command."""
    from usv.cli_main import ep_utf8   # console Windows cp1252 lam vo chu tieng Viet
    ep_utf8()
    parser = argparse.ArgumentParser(
        prog="usv-notify", description="Gửi một thông báo Discord.")
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--title", required=True)
    parser.add_argument("--line", action="append", default=[])
    parser.add_argument("--action", default="")
    parser.add_argument("--link", default="")
    args = parser.parse_args(argv)
    from .cli_spec_load import load_env
    load_env(Path(".env"))
    send(args.kind, args.title, args.line, args.action or None, args.link or None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
