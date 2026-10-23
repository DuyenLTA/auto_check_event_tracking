"""Discord: format tin, khong bao gio raise, khong bao gio doi ket qua luot cham.

Webhook gia la http.server that chay trong thread - khong mock logic gui.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from usv import cli_artifact, discord_notify, usage_log
from usv.run_message import build_run_message

ROOT = Path(__file__).resolve().parent.parent


class _Hook:
    def __init__(self, status: int = 204, delay: float = 0.0) -> None:
        self.received: list[dict] = []
        self.headers: list[dict] = []
        self.raw: list[bytes] = []
        hook = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = self.rfile.read(int(self.headers["Content-Length"]))
                hook.headers.append(dict(self.headers))
                hook.raw.append(body)
                # Tin co dinh kem la multipart: JSON nam trong phan `payload_json`.
                if self.headers["Content-Type"].startswith("multipart/"):
                    phan = body.split(b'name="payload_json"', 1)[1]
                    phan = phan.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0]
                    hook.received.append(json.loads(phan.decode("utf-8")))
                else:
                    hook.received.append(json.loads(body.decode("utf-8")))
                time.sleep(delay)
                try:
                    self.send_response(status)
                    self.end_headers()
                    self.wfile.write(b"ok")
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _bat_discord(monkeypatch, url: str) -> None:
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", url)


@pytest.fixture
def hook(monkeypatch):
    h = _Hook()
    _bat_discord(monkeypatch, h.url)
    yield h
    h.close()


def test_done_co_link_dung_format(hook):
    assert discord_notify.send("done", "Xong", ["dòng 1", "dòng 2"],
                             link="https://claude.ai/artifact/x") is True
    assert hook.received[0]["content"] == (
        "✅ **check-event** · Xong\ndòng 1\ndòng 2\n"
        "[Mở report](<https://claude.ai/artifact/x>)")


def test_stop_co_action_khong_co_link(hook):
    discord_notify.send("stop", "Dừng", ["a"], action="Chọn máy")
    assert hook.received[0]["content"] == "⛔ **check-event** · Dừng\na\n→ Chọn máy"


def test_bug_chi_co_tieu_de(hook):
    discord_notify.send("bug", "Lỗi")
    assert hook.received[0]["content"] == "🐞 **check-event** · Lỗi"


def test_204_la_thanh_cong_gui_UA_rieng_va_allowed_mentions(hook):
    assert gui_thu(hook) is True
    sent = hook.headers[0]
    assert sent["User-Agent"] == "qa-workflow-bot/1.0"
    assert sent["Content-Type"] == "application/json"
    assert hook.received[0]["allowed_mentions"] == {"parse": ["roles", "users"]}
    assert set(hook.received[0]) == {"content", "allowed_mentions"}


def gui_thu(hook) -> bool:
    return discord_notify.send("done", "x")


def test_noi_dung_dai_bi_cat_o_2000_theo_dong(hook):
    lines = [f"dòng {i} " + "a" * 90 for i in range(40)]
    discord_notify.send("done", "T", lines)
    content = hook.received[0]["content"]
    rows = content.split("\n")
    assert len(content) <= 2000 and content.endswith("…")
    assert rows[1] == lines[0]
    assert all(row in lines for row in rows[1:-1]) and rows[-1][:-1] in lines      # chi cat o ranh gioi dong


def test_khong_dat_webhook_thi_false_va_nhac_stderr(monkeypatch, capsys):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert discord_notify.send("done", "x") is False
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err.strip() == "discord: DISCORD_WEBHOOK_URL chưa đặt, bỏ qua thông báo"


def test_server_500_thi_false_khong_raise_khong_lo_url(monkeypatch, capsys):
    h = _Hook(status=500)
    _bat_discord(monkeypatch, h.url)
    try:
        assert discord_notify.send("done", "x") is False
    finally:
        h.close()
    out = capsys.readouterr()
    assert out.out == "" and "500" in out.err and h.url not in out.err


def test_timeout_thi_false_khong_raise(monkeypatch, capsys):
    h = _Hook(delay=0.6)
    monkeypatch.setattr(discord_notify, "TIMEOUT_S", 0.1)
    _bat_discord(monkeypatch, h.url)
    try:
        assert discord_notify.send("done", "x") is False
    finally:
        h.close()
    assert h.url not in capsys.readouterr().err


def test_webhook_khong_ket_noi_duoc_thi_false(monkeypatch, capsys):
    _bat_discord(monkeypatch, "http://127.0.0.1:1/bi-mat")
    assert discord_notify.send("done", "x") is False
    assert "bi-mat" not in capsys.readouterr().err


def test_DISCORD_NOTIFY_0_khong_gui_request(hook, monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "0")
    assert discord_notify.send("done", "x") is False
    assert hook.received == []


def test_usv_notify_cli_luon_exit_0(hook, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)                    # khong co .env o day
    code = discord_notify.main(["--kind", "stop", "--title", "T", "--line", "l1",
                              "--line", "l2", "--action", "A", "--link", "https://x.y"])
    assert code == 0
    assert hook.received[0]["content"] == (
        "⛔ **check-event** · T\nl1\nl2\n→ A\n[Mở report](<https://x.y>)")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://127.0.0.1:1/x")
    assert discord_notify.main(["--kind", "done", "--title", "T"]) == 0


# --- quyet dinh stop/done cua mot luot ---------------------------------------

def _payload(**kw) -> dict:
    base = {"package": "com.x", "app_version": "1.0 (1)", "report": "out/r.html",
            "pass": 5, "fail": 0, "not_tested": 0, "not_verifiable": 0, "results": []}
    return {**base, **kw}


def test_luot_sach_la_done():
    kind, title, lines, action = build_run_message(_payload(), 125)
    assert kind == "done" and action is None
    assert lines[0] == "com.x 1.0 (1)"
    assert "2 phút 5 giây" in " ".join(lines) and "out/r.html" in lines[-1]


@pytest.mark.parametrize("extra", [{"not_tested": 1}, {"not_verifiable": 2},
                                   {"blocked": 1}])
def test_con_viec_do_la_stop_luot_chua_xong(extra):
    kind, title, _, action = build_run_message(_payload(fail=3, **extra))
    assert (kind, title) == ("stop", "Lượt chưa xong")
    assert action == "Agent đang sửa flow và chạy lại case hụt"


def test_fail_het_viec_do_la_stop_cho_tester_toi_da_10_dong():
    rows = [{"element": f"ev_{i}", "verdict": "FAIL_VALUE", "message": f"sai {i}"}
            for i in range(12)]
    rows.append({"element": "ok", "verdict": "PASS", "message": ""})
    kind, title, lines, action = build_run_message(_payload(fail=12, results=rows))
    assert kind == "stop" and title == "Có 12 dòng Sai cần tester xác nhận"
    assert action == "Xác nhận từng dòng trước khi báo dev / log Jira"
    assert "• ev_0: sai 0" in lines and "• ev_9: sai 9" in lines
    assert "• ev_10: sai 10" not in lines and "… còn 2 dòng nữa" in lines
    assert not any("ok" in ln for ln in lines if ln.startswith("•"))


# --- usage-log ---------------------------------------------------------------

LOG = """# Log

| Ngày | App |
|---|---|
| a | b |
| c | d |

**Tổng:** 2 lần.
Dòng cuối.
"""


def test_chen_dong_truoc_Tong_khong_dong_vao_noi_dung_khac(tmp_path):
    path = tmp_path / "usage-log.md"
    path.write_text(LOG, encoding="utf-8")
    row = usage_log.build_row(package="com.x", version="1.0 (1)", passed=4, failed=1,
                              duration_s=125, url="https://claude.ai/artifact/z",
                              ngay="22/10/2026")
    assert usage_log.append_row(path, row) is True
    assert usage_log.append_row(path, row) is False          # khong chen trung
    lines = path.read_text(encoding="utf-8").split("\n")
    assert lines[:6] == LOG.split("\n")[:6]
    assert lines[6] == row and lines[7:] == LOG.split("\n")[6:]
    assert "4/5 khớp, 1 sai" in row and "[artifact](https://claude.ai/artifact/z)" in row
    assert row.endswith("| 60 phút | 58 phút |")


def test_chen_dong_vao_ban_sao_file_that_cua_repo(tmp_path):
    goc = (ROOT / usage_log.DEFAULT_PATH).read_text(encoding="utf-8")
    path = tmp_path / "usage-log.md"
    path.write_text(goc, encoding="utf-8")
    row = usage_log.build_row(package="com.new", version="1 (1)", passed=1, failed=0,
                              duration_s=60, url="https://claude.ai/a")
    assert usage_log.append_row(path, row)
    moi = path.read_text(encoding="utf-8").split("\n")
    cu = goc.split("\n")
    vi_tri = moi.index(row)
    assert moi[vi_tri + 1] == "" and moi[vi_tri + 2].startswith("**Tổng:**")
    assert moi[:vi_tri] + moi[vi_tri + 1:] == cu


def test_usv_artifact_them_dong_va_gui_done(hook, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    log = tmp_path / "usage-log.md"
    log.write_text(LOG, encoding="utf-8")
    code = cli_artifact.main([
        "--url", "https://claude.ai/artifact/q", "--generated-at", "22/10/2026 10:00",
        "--package", "com.x", "--version", "2.0 (3)", "--pass", "3", "--fail", "0",
        "--duration-s", "90", "--usage-log", str(log), "--out", str(tmp_path)])
    out = capsys.readouterr()
    assert code == 0
    assert len(out.out.strip().splitlines()) == 1
    assert "com.x" in log.read_text(encoding="utf-8").split("**Tổng:**")[0]
    text = hook.received[0]["content"]
    assert text.startswith("✅ **check-event** · Report đã publish · com.x 2.0 (3)")
    assert text.endswith("[Mở report](<https://claude.ai/artifact/q>)")


def test_usv_artifact_discord_hong_van_exit_0(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _bat_discord(monkeypatch, "http://127.0.0.1:1/x")
    assert cli_artifact.main(["--url", "https://claude.ai/a", "--generated-at", "t",
                              "--out", str(tmp_path)]) == 0


# --- chay khong Claude: dinh kem report, khong hua "agent dang sua" ----------

def test_khong_claude_con_viec_thi_bao_can_nguoi_xem_khong_noi_agent():
    rows = [{"element": "ev_sai", "verdict": "FAIL_VALUE", "message": "sai gia tri"}]
    kind, title, lines, action = build_run_message(
        _payload(fail=1, not_tested=2, khong_claude=True, results=rows))
    assert kind == "stop"
    assert title == "Xong, 2 dòng cần người xem · 1 dòng Sai"
    assert "Agent" not in action and "Cần người xem" in action
    assert "• ev_sai: sai gia tri" in lines


def test_khong_claude_luot_sach_van_la_done():
    kind, _, _, action = build_run_message(_payload(khong_claude=True))
    assert kind == "done" and action is None


def test_gui_kem_file_report_bang_multipart(hook, tmp_path):
    report = tmp_path / "report-x.html"
    report.write_text("<h1>Báo cáo</h1>", encoding="utf-8")
    assert discord_notify.send("done", "Xong", ["dòng 1"], file=report)
    assert hook.headers[0]["Content-Type"].startswith("multipart/form-data; boundary=")
    assert 'filename="report-x.html"'.encode() in hook.raw[0]
    assert "<h1>Báo cáo</h1>".encode("utf-8") in hook.raw[0]
    assert "dòng 1" in hook.received[0]["content"]


def test_file_qua_lon_thi_gui_tin_khong_kem_va_ghi_duong_dan(hook, tmp_path, monkeypatch):
    report = tmp_path / "to.html"
    report.write_text("x" * 50, encoding="utf-8")
    monkeypatch.setattr(discord_notify, "MAX_FILE", 10)
    assert discord_notify.send("done", "Xong", [], file=report)
    assert hook.headers[0]["Content-Type"] == "application/json"
    assert "quá lớn" in hook.received[0]["content"]


def test_file_khong_doc_duoc_van_gui_tin(hook, tmp_path):
    assert discord_notify.send("done", "Xong", [], file=tmp_path / "khong-co.html")
    assert "Không đọc được report" in hook.received[0]["content"]


def test_upload_hong_thi_van_gui_tin_chu_kem_duong_dan(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://127.0.0.1:9/hook")
    report = tmp_path / "r.html"
    report.write_text("x", encoding="utf-8")
    gui: list = []

    def post(url, payload, dinh_kem):
        gui.append((payload["content"], dinh_kem is not None))
        return dinh_kem is None          # upload hong, tin chu qua

    monkeypatch.setattr(discord_notify, "_post", post)
    assert discord_notify.send("done", "Xong", [], file=report)
    assert [co for _, co in gui] == [True, False]
    assert "Không gửi kèm được report" in gui[1][0]


def test_ten_file_dinh_kem_bo_dau_va_nhay():
    assert discord_notify._ten_file(Path('báo "cáo".html')) == "b_o__c_o_.html"
