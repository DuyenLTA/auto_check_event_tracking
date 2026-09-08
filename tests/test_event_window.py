"""Cat timeline theo moc USV_MARK."""

from __future__ import annotations

from usv.event_window import EDGE_MS, cut_log, mark_label, split_label, to_ms

MARK = "09-08 15:00:{sec}.{ms} I/USV_MARK( 9): {label}"
EVENT = ("09-08 15:00:{sec}.{ms} V/FA-SVC  ( 9): Logging event: origin=app,"
         "name={name},params=Bundle[{{placement_name=home}}]")


def _mark(sec, ms, label):
    return MARK.format(sec=f"{sec:02d}", ms=f"{ms:03d}", label=label)


def _event(sec, ms, name):
    return EVENT.format(sec=f"{sec:02d}", ms=f"{ms:03d}", name=name)


def test_nhan_moc_ghep_va_tach_lai_duoc():
    label = mark_label("rating_star_clicked", "Khi user click rate")
    assert split_label(label) == ("rating_star_clicked", "Khi user click rate")


def test_nhan_moc_khong_co_van_xuoi():
    assert split_label(mark_label("ev_a")) == ("ev_a", "")


def test_to_ms_tru_duoc():
    a = to_ms("09-08 15:00:01.000")
    b = to_ms("09-08 15:00:01.250")
    assert b - a == 250.0


def test_to_ms_chuoi_la_tra_None():
    assert to_ms("khong phai gio") is None
    assert to_ms("") is None


def test_khong_co_moc_thi_khong_co_cua_so():
    assert cut_log(_event(1, 0, "ev_a")) == ()


def test_event_truoc_moc_dau_tien_bi_bo():
    """Chua bam moc nao thi chua bat dau buoc nao."""
    log = "\n".join([_event(1, 0, "ev_a"), _mark(5, 0, "ev_b"), _event(6, 0, "ev_b")])
    windows = cut_log(log)
    assert len(windows) == 1
    assert [e.name for e in windows[0].events] == ["ev_b"]


def test_moc_sau_la_diem_ket_cua_buoc_truoc():
    """MOT nut mot buoc - khong can nut Xong rieng."""
    log = "\n".join([
        _mark(1, 0, "ev_a"), _event(2, 0, "ev_a"),
        _mark(5, 0, "ev_b"), _event(6, 0, "ev_b"),
    ])
    windows = cut_log(log)
    assert len(windows) == 2
    assert [e.name for e in windows[0].events] == ["ev_a"]
    assert [e.name for e in windows[1].events] == ["ev_b"]


def test_cua_so_cuoi_keo_den_het_log():
    log = "\n".join([_mark(1, 0, "ev_a"), _event(2, 0, "ev_a"), _event(9, 0, "ev_x")])
    windows = cut_log(log)
    assert {e.name for e in windows[0].events} == {"ev_a", "ev_x"}


def test_named_chi_lay_event_dung_ten_va_origin_app():
    log = "\n".join([_mark(1, 0, "ev_a"), _event(2, 0, "ev_a"), _event(3, 0, "ev_b")])
    window = cut_log(log)[0]
    assert len(window.named("ev_a")) == 1
    assert window.named("ev_zzz") == ()


def test_event_sat_bien_duoc_gan_co_near_edge():
    """R4: khong tu doi cua so cho no - chi bao ra de tester tu phan."""
    log = "\n".join([_mark(1, 0, "ev_a"), _event(1, int(EDGE_MS) - 50, "ev_a")])
    window = cut_log(log)[0]
    assert "ev_a" in window.near_edge


def test_event_xa_bien_thi_khong_gan_co():
    log = "\n".join([_mark(1, 0, "ev_a"), _event(3, 0, "ev_a")])
    window = cut_log(log)[0]
    assert window.near_edge == ()


def test_payload_noi_ra_near_edge():
    log = "\n".join([_mark(1, 0, "ev_a"), _event(1, 100, "ev_a")])
    assert cut_log(log)[0].payload()["near_edge"] == ["ev_a"]
