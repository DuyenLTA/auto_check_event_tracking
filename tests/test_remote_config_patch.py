"""Sua noi dung file Remote Config - thuan van ban, chay khong can may.

Hai bat buoc lay tu thuc nghiem:
  - PHAI sua ca file gia tri LAN moc throttle. Chi sua gia tri thi lan mo app
    sau app fetch that va de mat sach.
  - Sua prefs mirror phai GIU NGUYEN kieu XML. Doi boolean thanh string la app
    doc khong ra, hoac crash.
"""

from __future__ import annotations

import json

import pytest

from usv.remote_config_patch import (
    patch_activate_json, patch_prefs_xml, patch_throttle_xml, prefs_value,
    read_configs,
)

NOW = 1_757_000_000_000

# Dang that cua file, lay tu app tren may.
ACTIVATE = json.dumps({
    "configs_key": {"enable_rate": "false", "paywall_config": "a"},
    "fetch_time_key": 1_700_000_000_000,
    "abt_experiments_key": [],
})
THROTTLE = ("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n"
            '    <long name="last_fetch_time_in_millis" value="1700000000000" />\n'
            '    <string name="last_fetch_status">success</string>\n</map>\n')
MIRROR = ("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n"
          '    <boolean name="enable_rate" value="false" />\n'
          '    <string name="paywall_config">a</string>\n'
          '    <long name="rate_after_n_open" value="3" />\n</map>\n')


# --- file gia tri ---

def test_dat_gia_tri_moi_va_giu_key_cu():
    out = json.loads(patch_activate_json(ACTIVATE, {"enable_rate": "true"}, NOW))
    assert out["configs_key"]["enable_rate"] == "true"
    assert out["configs_key"]["paywall_config"] == "a", "khong duoc lam mat key khac"


def test_day_moc_fetch_len_bay_gio():
    """Khong day moc thi SDK fetch that va de mat patch."""
    out = json.loads(patch_activate_json(ACTIVATE, {"enable_rate": "true"}, NOW))
    assert out["fetch_time_key"] == NOW


def test_gia_tri_luon_luu_duoi_dang_string():
    """SDK luu moi gia tri la string, ke ca boolean va so."""
    out = json.loads(patch_activate_json(ACTIVATE, {"a": True, "b": 5}, NOW))
    assert out["configs_key"]["a"] == "True"
    assert out["configs_key"]["b"] == "5"


def test_giu_nguyen_cac_field_khac_cua_file():
    out = json.loads(patch_activate_json(ACTIVATE, {"x": "1"}, NOW))
    assert "abt_experiments_key" in out


def test_file_chua_ton_tai_van_tao_duoc():
    out = json.loads(patch_activate_json("", {"enable_rate": "true"}, NOW))
    assert out["configs_key"] == {"enable_rate": "true"}
    assert out["fetch_time_key"] == NOW


def test_json_hong_bao_loi_ro_chu_khong_ghi_bua():
    with pytest.raises(ValueError):
        patch_activate_json("{khong phai json", {"a": "1"}, NOW)


def test_json_la_mang_thi_tu_choi():
    with pytest.raises(ValueError):
        patch_activate_json("[1,2,3]", {"a": "1"}, NOW)


def test_doc_lai_gia_tri_de_verify():
    text = patch_activate_json(ACTIVATE, {"enable_rate": "true"}, NOW)
    assert read_configs(text)["enable_rate"] == "true"


def test_doc_lai_file_hong_tra_rong_chu_khong_no():
    assert read_configs("{hong") == {}
    assert read_configs("") == {}


# --- moc throttle ---

def test_dat_moc_throttle():
    out = patch_throttle_xml(THROTTLE, NOW)
    assert prefs_value(out, "last_fetch_time_in_millis") == str(NOW)
    assert "last_fetch_status" in out, "khong duoc lam mat key khac"


def test_moc_throttle_chua_co_thi_them_vao():
    text = "<?xml version='1.0' ?>\n<map>\n</map>\n"
    assert prefs_value(patch_throttle_xml(text, NOW), "last_fetch_time_in_millis") \
        == str(NOW)


def test_file_throttle_rong_thi_tao_khung_moi():
    out = patch_throttle_xml("", NOW)
    assert "<map>" in out and str(NOW) in out


# --- prefs mirror ---

def test_mirror_giu_nguyen_kieu_boolean():
    out, changed = patch_prefs_xml(MIRROR, {"enable_rate": "true"})
    assert '<boolean name="enable_rate" value="true" />' in out
    assert changed == {"enable_rate"}


def test_mirror_nhan_gia_tri_boolean_duoi_nhieu_dang():
    for raw in ("true", "True", "1", "yes"):
        out, _ = patch_prefs_xml(MIRROR, {"enable_rate": raw})
        assert 'value="true"' in out, raw
    for raw in ("false", "0", "no", "linh tinh"):
        out, _ = patch_prefs_xml(MIRROR, {"enable_rate": raw})
        assert '<boolean name="enable_rate" value="false" />' in out, raw


def test_mirror_giu_nguyen_kieu_string():
    out, changed = patch_prefs_xml(MIRROR, {"paywall_config": "b"})
    assert "<string name=\"paywall_config\">b</string>" in out
    assert changed == {"paywall_config"}


def test_mirror_giu_nguyen_kieu_long():
    out, changed = patch_prefs_xml(MIRROR, {"rate_after_n_open": "9"})
    assert '<long name="rate_after_n_open" value="9" />' in out
    assert changed == {"rate_after_n_open"}


def test_mirror_KHONG_them_key_moi():
    """Them key app khong biet la doan, va lam file khac han ban goc."""
    out, changed = patch_prefs_xml(MIRROR, {"key_la": "1"})
    assert changed == set()
    assert out == MIRROR


def test_mirror_sua_nhieu_key_mot_luot():
    out, changed = patch_prefs_xml(
        MIRROR, {"enable_rate": "true", "rate_after_n_open": "1", "khong_co": "x"})
    assert changed == {"enable_rate", "rate_after_n_open"}
    assert 'value="true"' in out and '<long name="rate_after_n_open" value="1" />' in out


def test_prefs_value_khong_co_key_tra_None():
    assert prefs_value(MIRROR, "khong_ton_tai") is None
