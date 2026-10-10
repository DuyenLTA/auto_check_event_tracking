"""Goi spec bang ten chuc nang ("rating", "widget", "daily checkin") thay link.

`specs.json` chi la CACHE, khong phai danh sach dong: ten chua co trong do thi
hoi thang Confluence. Ghi vao registry la de lan sau khoi tra mang, va - quan
trong hon - de mot lua chon da hoi nguoi dung roi thi khong hoi lai.

Vi sao khong tim thang bang `title~"<ten>"`: nhieu qua. Space VL co 15 trang
title chua "rating", phan lon la trang cua tung app ("AIP801 Luong rating"),
tron ca trang checklist. Trang spec SDK co quy luat rieng:

    "SDK Rating (New) V 1.0.0"      "1. SDK Widget V 1.0.0"
    "SDK Daily checkin - V 1.0.0"   "1. SDK Full Screen Intent + Noti - V 1.0.0"

tuc la title vua chua "SDK", vua chua so version dang "V x.y.z". Loc theo hai
dau hieu do thi 15 trang con dung mot. Con lai thi KHONG doan: tra ca danh sach
ra cho nguoi goi hoi nguoi dung, vi cham nham trang spec lam moi event ra
"khong co trong bang" - trong y het app thieu event.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

from .confluence_client import ConfluenceError, _get, config

# Space chua spec SDK. Doi space thi sua bien nay - chua co nhu cau nen chua
# lam thanh tham so dong lenh.
SPACE = "VL"

# "V 1.0.0" / "V1.0.0" nhung KHONG phai "Ver1.0.4" (trang cua app, khong phai
# spec SDK): sau chu V phai la so ngay.
_VERSION = re.compile(r"\bV\s?\d+\.\d+")
_COPY = re.compile(r"^\s*copy of\b", re.IGNORECASE)


class SpecAliasError(Exception):
    """Khong phan giai duoc ten. Message da doc duoc, nguoi goi in thang ra."""


def registry_path() -> Path:
    """`specs.json` nam canh repo, cung cho voi `flows/`."""
    return Path(__file__).resolve().parents[2] / "specs.json"


def _slug(text: str) -> str:
    """Chuan hoa de so khop: thuong het, bo dau cau, gop khoang trang."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())


def load_registry() -> dict[str, dict[str, str]]:
    path = registry_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecAliasError(f"Đọc {path} hỏng: {exc}") from exc
    return data if isinstance(data, dict) else {}


def save_entry(alias: str, url: str, title: str) -> None:
    data = load_registry()
    data[_slug(alias)] = {"url": url, "title": title}
    registry_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def looks_like_link(text: str) -> bool:
    """Link Confluence hoac pageId tran - dua thang cho `fetch_page`."""
    text = (text or "").strip()
    return text.isdigit() or text.startswith(("http://", "https://"))


def page_url(page_id: str, title: str) -> str:
    """Link /display/... doc duoc bang mat, thay vi pageId tran."""
    base, _ = config()
    return (f"{base}/display/{SPACE}/"
            f"{urllib.parse.quote_plus(title)}")


def search(name: str, *, strict: bool = True) -> list[dict[str, str]]:
    """Cac trang spec SDK khop `name`. Rong = khong thay, khong phai loi.

    `strict=False` bo yeu cau co so version trong title: dung khi loc chat
    khong con gi, de chi ra trang gan dung thay vi bao "khong thay" - trang cha
    ("SDK Retention") chua sinh ban version nao van la thu nguoi ta dang tim.
    """
    base, token = config()
    cql = f'space={SPACE} and type=page and title~"SDK {name}"'
    query = urllib.parse.urlencode({"cql": cql, "limit": 50})
    try:
        found = _get(f"{base}/rest/api/content/search?{query}", token)
    except ConfluenceError as exc:
        raise SpecAliasError(str(exc)) from exc

    words = _slug(name).split()
    out: list[dict[str, str]] = []
    for row in found.get("results") or []:
        title = row.get("title") or ""
        if _COPY.match(title) or (strict and not _VERSION.search(title)):
            continue
        low = _slug(title)
        if "sdk" not in low or not all(word in low for word in words):
            continue
        out.append({"title": title, "url": page_url(row.get("id") or "", title)})
    return out


def resolve(name: str) -> tuple[str, str, str]:
    """`name` -> (url, tieu de, nguon). `nguon` = "registry" | "confluence".

    Link/pageId thi tra nguyen, de `fetch_page` lo.
    """
    text = (name or "").strip()
    if not text:
        raise SpecAliasError("Chưa nêu spec nào.")
    if looks_like_link(text):
        return text, "", "link"

    entry = load_registry().get(_slug(text))
    if entry:
        return entry["url"], entry.get("title", ""), "registry"

    hits = search(text)
    if len(hits) == 1:
        return hits[0]["url"], hits[0]["title"], "confluence"
    if not hits:
        gan = search(text, strict=False)
        if gan:
            lines = "\n".join(f"    {h['title']}\n      {h['url']}" for h in gan)
            raise SpecAliasError(
                f"Không trang nào cho {text!r} có số version trong tiêu đề — "
                f"chưa chắc trang nào là spec cần chấm:\n{lines}\n"
                f"  Chốt một trang rồi lưu lại:  usv-spec --add {text!r} <link>")
        raise SpecAliasError(
            f"Không thấy trang spec SDK nào cho {text!r} trong space {SPACE}.\n"
            "  Tên đã lưu: " + (", ".join(sorted(load_registry())) or "(chưa có)")
            + "\n  Dán thẳng link Confluence, hoặc lưu tên bằng:\n"
              f"    usv-spec --add {text!r} <link>")
    lines = "\n".join(f"    {h['title']}\n      {h['url']}" for h in hits)
    raise SpecAliasError(
        f"{text!r} khớp {len(hits)} trang spec — chọn nhầm là chấm sai bảng "
        f"event, nên không tự đoán:\n{lines}\n"
        f"  Chốt một trang rồi lưu lại:  usv-spec --add {text!r} <link>")
