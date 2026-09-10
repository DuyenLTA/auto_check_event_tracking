"""index.html phai can bang the.

Vi sao can: mot the <p> khong dong va mot </div> lac cho da lam ca giao dien
sap - </div> do dong som ca <section>, nen moi buoc phia sau bi hut vao trong
nhau. Trinh duyet KHONG bao loi, no tu doan va ve ra mot bo cuc lech.

Test doc tinh, khong can browser, nen re va bat dung loai loi do.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

HTML = (Path(__file__).parent.parent / "src" / "usv" / "web"
        / "index.html").read_text(encoding="utf-8")

# The tu dong (void) khong can the dong.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}


class _Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"dong {self.getpos()[0]}: </{tag}> khong co the mo")
            return
        mo, dong_mo = self.stack.pop()
        if mo != tag:
            self.errors.append(
                f"dong {self.getpos()[0]}: </{tag}> nhung dang mo <{mo}> "
                f"(mo o dong {dong_mo})")


def test_the_can_bang():
    parser = _Balance()
    parser.feed(HTML)
    parser.close()
    con_mo = [f"<{tag}> mo o dong {dong} chua dong" for tag, dong in parser.stack]
    assert not parser.errors and not con_mo, "\n".join(parser.errors + con_mo)


def test_moi_section_step_dong_dung_cho():
    """Cac buoc phai NGANG HANG nhau, khong long vao nhau.

    Khong ghim con so cu the: so buoc con doi (da gop buoc 3 vao buoc 2). Cai
    phai dung la moi <section> mo ra deu duoc dong lai, va so buoc khop voi so
    thu tu in tren tieu de.
    """
    parser = _Balance()
    parser.feed(HTML)
    parser.close()
    so_mo = HTML.count('<section class="step"')
    assert so_mo >= 2, "trang phai con it nhat hai buoc"
    assert HTML.count("</section>") == so_mo, "co section khong duoc dong"


def test_so_thu_tu_buoc_danh_lien_tu_1():
    """Gop/xoa mot buoc ma quen danh so lai thi trang nhay so (1, 2, 4)."""
    so = [int(n) for n in re.findall(r'<span class="num">(\d+)</span>', HTML)]
    assert so == list(range(1, len(so) + 1)), f"so thu tu buoc nhay: {so}"
    assert len(so) == HTML.count('<section class="step"'), \
        "so tieu de danh so khong khop so buoc"
