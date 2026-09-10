"""Cac hop canh bao dau bao cao event.

Tach khoi report_event_html vi day la mot moi quan tam rieng: moi hop tra loi
mot cau "vi sao KHONG duoc doc bang phia duoi theo nghia mat chu". Chung dai va
se con dai them, con phan render bang thi on dinh.

THU TU CO Y NGHIA - hop nao lam vo hieu nhieu ket luan hon thi dat truoc:
  1. stream_died  - phien ghi chet, moi dong "khong bat duoc" thanh vo nghia
  2. quick        - khong ket luan duoc thoi diem ban
  3. fa_silent    - khong doc duoc log Firebase
  4. extra/near_edge - chi thu hep pham vi vai dong
"""

from __future__ import annotations

import html

from .check_models import CheckResult, Verdict


def esc(value: object) -> str:
    """Gia tri den TU LOG - du lieu khong kiem soat, phai escape het.

    Do that: `error_msg` chua backtick, dau ngoac, dau hai cham.

    Dat o module NAY chu khong o report_event_html: html import callouts, nen
    dat nguoc lai la vong import. Mot ban duy nhat - hai ban thi mot ngay sua
    escape mot ben.
    """
    return html.escape(str(value if value is not None else ""))


def _callouts(results: list[CheckResult], fa_silent: bool,
              near_edge: tuple[str, ...], quick: bool = False,
              stream_died: bool = False, app_seen: bool = True) -> str:
    out = []
    if not app_seen:
        # Dat DAU TIEN, tren ca stream_died: neu app duoi test khong he chay
        # thi khong mot dong nao trong bao cao noi ve app do.
        out.append(
            "<div class='callout alarm'><h3>App dưới test không chạy lần nào</h3>"
            "<p>Suốt phiên ghi, máy không có process nào của app này. Log "
            "Firebase do <b>Google Play Services</b> in ra chứ không phải "
            "process của app, nên nó <b>không cho biết event thuộc app nào</b> "
            "— event bắt được ở đây là của <b>app khác</b>. Kiểm lại tên "
            "package, và nếu tự mở app bằng tay thì mở <b>sau</b> khi bấm "
            "Ghi.</p></div>")
    if stream_died:
        # Dat DAU TIEN: neu phien ghi da chet thi moi ket luan phia duoi chi
        # noi ve phan dau cua phien, va nguoi doc phai biet dieu do truoc khi
        # doc bat cu dong nao.
        out.append(
            "<div class='callout alarm'><h3>Phiên ghi bị đứt giữa đường</h3>"
            "<p>Stream logcat dừng <b>trước</b> khi bấm Dừng ghi — thường là "
            "máy rớt khỏi USB, USB ngủ, hoặc mất authorize. Phần sau của phiên "
            "<b>không được ghi</b>, nên các mục \"không bắn\" đã bị hạ xuống "
            "<b>không kiểm được</b> chứ không tính là lỗi app. Cắm lại máy và "
            "ghi lại.</p></div>")

    if quick:
        # Khong noi ra thi nguoi doc tuong da kiem ca thoi diem ban.
        out.append(
            "<div class='callout'><h3>Chạy ở chế độ nhanh</h3>"
            "<p>Không đánh dấu từng bước, nên báo cáo này <b>chỉ</b> kết luận "
            "event có bắn ra trong cả phiên và param có đúng hay không. Nó "
            "<b>không</b> kết luận event bắn đúng lúc — không có biên bước thì "
            "không có gì để so. Kiểm bắn trùng cũng đã tắt, vì một phiên dài vào "
            "ra cùng một màn thì event đó bắn lại là đúng.</p></div>")
    if fa_silent:
        out.append(
            "<div class='callout alarm'><h3>Không đọc được log Firebase</h3>"
            "<p>Cả phiên ghi không có một dòng <code>FA-SVC</code> nào. Rất có thể "
            "build này strip log Firebase, <b>không phải</b> app thiếu event — "
            "đừng kết luận app sai từ báo cáo này. Thử lại với build debug, hoặc "
            "kiểm tra <code>setprop log.tag.FA-SVC VERBOSE</code> đã ăn chưa "
            "(property không sống qua reboot, và app phải khởi động lại sau khi "
            "set).</p></div>")

    extras = [r for r in results if r.verdict is Verdict.EXTRA]
    if extras:
        chips = "".join(f"<span class='chip'>{esc(r.element)} {esc(r.actual)}</span>"
                        for r in extras)
        out.append(
            "<div class='callout'><h3>Không tính vào fail</h3>"
            "<p>Event/param app có mà spec không khai. Có thể spec chưa cập nhật, "
            "không hẳn app sai.</p>"
            f"<div class='chip-list'>{chips}</div></div>")

    if near_edge:
        chips = "".join(f"<span class='chip'>{esc(n)}</span>" for n in near_edge)
        out.append(
            "<div class='callout'><h3>Event bắn sát mốc đánh dấu</h3>"
            "<p>Những event này bắn rất gần lúc bấm mốc nên có thể thuộc bước "
            "liền kề. Tool <b>không</b> tự đổi bước cho chúng — xem lại bằng mắt "
            "nếu kết quả của chúng bất thường.</p>"
            f"<div class='chip-list'>{chips}</div></div>")
    return "".join(out)
