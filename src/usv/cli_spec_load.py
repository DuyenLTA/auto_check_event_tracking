"""Nap spec cho CLI: tu link Confluence hoac tu file TSV dan tay.

Tach khoi `cli_check` de cho do phinh, va vi nap spec la thu duy nhat trong ca
workflow cham vao mang - no hong theo kieu rieng (token het han, VPN, link go
sai), khong lien quan gi den may Android.

`.env` duoc nap o day luon: tren Windows khong co `~/.bashrc` de `export`, ma
`confluence_client` thi doc thang `os.environ`.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import spec_alias
from .confluence_client import ConfluenceError, fetch_page
from .event_spec_confluence import parse_page
from .event_spec_models import SpecSheet
from .event_spec_parse import parse_paste

ENV_KEYS = ("CONFLUENCE_BASE_URL", "CONFLUENCE_TOKEN")


class SpecLoadError(Exception):
    """Khong nap duoc spec. Message da doc duoc, nguoi goi in thang ra."""


def load_env(path: Path) -> None:
    """KEY=VALUE -> os.environ. Bien da co san KHONG bi de len: shell that
    (vd token trong ~/.bashrc) phai thang file .env trong repo."""
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


def missing_env() -> list[str]:
    return [key for key in ENV_KEYS if not os.environ.get(key)]


def from_confluence(url: str) -> tuple[SpecSheet, str]:
    """(spec, tieu de trang). Loi mang/token/link -> SpecLoadError.

    `url` nhan ca ten chuc nang ("rating", "widget") - xem `spec_alias`.
    """
    if missing_env():
        raise SpecLoadError(
            f"Thiếu {', '.join(missing_env())}. Đặt trong .env cạnh repo, "
            "hoặc export trong shell rồi chạy lại.")
    try:
        url, _, _ = spec_alias.resolve(url)
        title, html = fetch_page(url)
    except (ConfluenceError, spec_alias.SpecAliasError) as exc:
        raise SpecLoadError(str(exc)) from exc
    return parse_page(html), title


def from_tsv(path: Path) -> tuple[SpecSheet, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecLoadError(f"Không đọc được {path}: {exc}") from exc
    return parse_paste(text), path.name


def load(*, url: str = "", tsv: Path | None = None,
         env_file: Path | None = None) -> tuple[SpecSheet, str]:
    """Nap spec theo mot trong hai duong. Tra (spec, nguon)."""
    if bool(url) == bool(tsv):
        raise SpecLoadError("Chọn đúng một: --spec <link Confluence> "
                            "hoặc --spec-tsv <file>.")
    if env_file is not None:
        load_env(env_file)
    return from_confluence(url) if url else from_tsv(tsv)
