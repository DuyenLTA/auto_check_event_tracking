"""index.html phai can bang the.

Vi sao can: mot the <p> khong dong va mot </div> lac cho da lam ca giao dien
sap - </div> do dong som ca <section>, nen moi buoc phia sau bi hut vao trong
nhau. Trinh duyet KHONG bao loi, no tu doan va ve ra mot bo cuc lech.

Test doc tinh, khong can browser, nen re va bat dung loai loi do.
"""

from __future__ import annotations

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
    """Bon buoc phai la bon <section> NGANG HANG, khong long nhau."""
    parser = _Balance()
    parser.feed(HTML)
    parser.close()
    assert HTML.count('<section class="step"') == 4
    assert HTML.count("</section>") == 4
