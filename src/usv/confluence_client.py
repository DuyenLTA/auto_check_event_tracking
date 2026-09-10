"""Tai mot trang Confluence ve dang HTML storage.

Cau hinh qua bien moi truong, KHONG luu token trong repo:
    export CONFLUENCE_BASE_URL=https://confluence.example.com
    export CONFLUENCE_TOKEN=<personal access token>

BAY DA DO DUOC: nginx dung truoc Confluence tra 403 cho request mang
User-Agent mac dinh cua thu vien HTTP. Phai gia User-Agent trinh duyet, khong
thi request khong bao gio toi duoc Confluence - va 403 do trong y het token
sai, rat de di sua nham cho.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 20.0
# Xem docstring - khong phai lam mau.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64)"

_PAGE_ID = re.compile(r"pageId=(\d+)")
_PAGES_PATH = re.compile(r"/pages/(\d+)")


class ConfluenceError(Exception):
    """Loi noi ro sai o dau va cach sua."""


class ConfluenceLinkError(ConfluenceError):
    """Link go sai - loi DU LIEU cua nguoi dung, khong phai loi he thong.

    Tach rieng de route tra 400 chu khong 502: gop chung thi mot cai link go
    thieu chu bi bao nhu su co mang, va tester di kiem tra VPN thay vi doc lai
    cai link."""


def config() -> tuple[str, str]:
    base = (os.environ.get("CONFLUENCE_BASE_URL") or "").rstrip("/")
    token = os.environ.get("CONFLUENCE_TOKEN") or ""
    if not base or not token:
        raise ConfluenceError(
            "Chưa khai báo Confluence. Đặt hai biến này rồi khởi động lại tool:\n"
            "  export CONFLUENCE_BASE_URL=https://confluence.cong-ty.vn\n"
            "  export CONFLUENCE_TOKEN=<personal access token>")
    return base, token


def locate(url: str) -> dict[str, str]:
    """Doc link -> tham so tra cuu. Nhan ca ba dang link Confluence hay gap."""
    text = (url or "").strip()
    if not text:
        raise ConfluenceLinkError("Chưa dán link Confluence nào.")
    if text.isdigit():
        return {"page_id": text}

    parsed = urllib.parse.urlparse(text)
    if not parsed.scheme:
        raise ConfluenceLinkError(f"{text!r} không phải một link hợp lệ.")

    found = _PAGE_ID.search(parsed.query) or _PAGES_PATH.search(parsed.path)
    if found:
        return {"page_id": found.group(1)}

    # /display/<SPACE>/<Tieu+de>
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "display":
        return {"space": urllib.parse.unquote(parts[1]),
                "title": urllib.parse.unquote_plus(parts[2])}
    raise ConfluenceLinkError(
        "Không đọc được link. Dùng một trong các dạng:\n"
        "  .../pages/viewpage.action?pageId=123456\n"
        "  .../display/SPACE/Tên+Trang\n"
        "  hoặc dán thẳng số pageId.")


def _get(path: str, token: str) -> dict:
    request = urllib.request.Request(path, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,        # bo dong nay -> nginx tra 403
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        hint = {
            401: " — token sai hoặc hết hạn.",
            403: " — bị chặn. Nếu token đúng thì thường là nginx chặn User-Agent.",
            404: " — không có trang này, kiểm lại link.",
        }.get(exc.code, "")
        raise ConfluenceError(f"Confluence trả {exc.code}{hint}") from exc
    except urllib.error.URLError as exc:
        raise ConfluenceError(f"Không nối được tới Confluence: {exc.reason}") from exc


def fetch_page(url: str) -> tuple[str, str]:
    """Tra ve (tieu de, HTML storage) cua trang."""
    base, token = config()
    where = locate(url)
    if "page_id" in where:
        data = _get(f"{base}/rest/api/content/{where['page_id']}"
                    "?expand=body.storage", token)
    else:
        query = urllib.parse.urlencode({
            "title": where["title"], "spaceKey": where["space"],
            "expand": "body.storage"})
        found = _get(f"{base}/rest/api/content?{query}", token)
        results = found.get("results") or []
        if not results:
            raise ConfluenceError(
                f"Không tìm thấy trang {where['title']!r} trong space "
                f"{where['space']!r}.")
        data = results[0]

    body = (data.get("body") or {}).get("storage") or {}
    html = body.get("value") or ""
    if not html:
        raise ConfluenceError(
            "Trang trả về rỗng — có thể bạn không có quyền xem trang này.")
    return data.get("title") or "", html
