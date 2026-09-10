"""Doc link Confluence va goi REST. Chay KHONG can mang.

Hai thu khong the bo:
  - User-Agent gia trinh duyet. nginx truoc Confluence tra 403 cho UA mac dinh
    cua thu vien HTTP, va 403 do trong y het token sai -> di sua nham cho.
  - Bao loi phai NOI CACH SUA. Token het han, link sai dang, chua export bien
    moi truong: ba loi khac nhau, ba cach sua khac nhau.
"""

from __future__ import annotations

import json
import io

import pytest

from usv import confluence_client
from usv.confluence_client import ConfluenceError, fetch_page, locate


def test_link_dang_pageId():
    assert locate("https://x.vn/pages/viewpage.action?pageId=306053648") == \
        {"page_id": "306053648"}


def test_link_dang_display():
    assert locate("https://x.vn/display/VL/1.+SDK+Widget+V+1.0.0") == \
        {"space": "VL", "title": "1. SDK Widget V 1.0.0"}


def test_link_dang_pages_moi():
    assert locate("https://x.vn/spaces/VL/pages/12345/Ten") == {"page_id": "12345"}


def test_dan_thang_so_pageId():
    assert locate("306053648") == {"page_id": "306053648"}


def test_link_rac_bao_loi_kem_cac_dang_hop_le():
    with pytest.raises(ConfluenceError) as err:
        locate("khong-phai-link")
    assert "khong phai mot link hop le" in str(err.value)


def test_chua_export_bien_thi_noi_ro_phai_export_gi(monkeypatch):
    monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
    monkeypatch.delenv("CONFLUENCE_TOKEN", raising=False)
    with pytest.raises(ConfluenceError) as err:
        fetch_page("https://x.vn/pages/viewpage.action?pageId=1")
    assert "CONFLUENCE_TOKEN" in str(err.value)


def _fake_urlopen(captured: dict, payload: dict):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(payload).encode()

    def urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        return Response()
    return urlopen


def test_gui_kem_user_agent_trinh_duyet(monkeypatch):
    """Bo UA -> nginx tra 403. Da do that, khong phai lo xa."""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://x.vn")
    monkeypatch.setenv("CONFLUENCE_TOKEN", "tok")
    seen: dict = {}
    monkeypatch.setattr(confluence_client.urllib.request, "urlopen",
                        _fake_urlopen(seen, {"title": "T",
                                             "body": {"storage": {"value": "<p>x</p>"}}}))
    title, html = fetch_page("https://x.vn/pages/viewpage.action?pageId=9")
    assert (title, html) == ("T", "<p>x</p>")
    ua = seen["headers"].get("User-agent", "")
    assert "Mozilla" in ua, f"phai gia UA trinh duyet, dang gui {ua!r}"
    assert seen["headers"].get("Authorization") == "Bearer tok"
    assert "/rest/api/content/9" in seen["url"]


def test_403_goi_y_dung_cho_thay_vi_do_tai_token(monkeypatch):
    import urllib.error
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://x.vn")
    monkeypatch.setenv("CONFLUENCE_TOKEN", "tok")

    def boom(request, timeout=None):
        raise urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b""))

    monkeypatch.setattr(confluence_client.urllib.request, "urlopen", boom)
    with pytest.raises(ConfluenceError) as err:
        fetch_page("306053648")
    assert "User-Agent" in str(err.value)
