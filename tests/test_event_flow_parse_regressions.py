"""Cac duong ma flow SAI van parse ok, roi dan den verdict sai ve app.

Moi test o day ung voi mot lo trong da tung xanh: parser nhan input sai, im
lang bo qua, va cai gia phai tra khong phai la mot error message - la mot ket
luan sai ve app trong report.

Tach khoi `test_event_flow_parse` de doc duoc: file kia mo ta parser LAM GI,
file nay khoa nhung gi no PHAI TU CHOI.
"""

from __future__ import annotations

import asyncio

from usv.adb_input import KEYEVENTS
from usv.event_flow_parse import parse_flow


def _one_case(steps: str, extra: str = "") -> str:
    return f"- event: e\n  cases:\n    - steps:\n{steps}{extra}"


# --- Khoa la bi bo qua -> bam sai node / mat assert gia tri ------------------

def test_khoa_la_o_cap_case__go_thieu_s_thanh_param_la_PASS_GIA():
    """`param` thieu chu s -> expect_params rong -> mat kha nang bat loi 'man
    Result ma bao placement_name=home'. Spec cho phep 'home' nen ra PASS."""
    flow = parse_flow("- event: e\n  cases:\n    - param: {placement_name: home}\n"
                      "      steps: [launch]\n")
    assert not flow.ok
    assert any("param" in e and "khóa lạ" in e for e in flow.errors)


def test_khoa_la_trong_selector__indx_lam_bam_sai_card():
    """`indx` -> index ve 0 -> bam card thu 1 thay vi thu 3 -> lai sang man
    khac -> event khong ban -> FAIL oan cho app."""
    flow = parse_flow(_one_case("        - tap_id: {id: borderContainer, indx: 2}\n"))
    assert not flow.ok
    assert any("indx" in e for e in flow.errors)


def test_khoa_la_trong_swipe_va_wait_text():
    for step in ("        - swipe: {id: rv, direciton: down}\n",
                 "        - wait_text: {text: Home, timeut: 5s}\n"):
        assert not parse_flow(_one_case(step)).ok, step


def test_khai_hai_khoa_tim_kiem__bao_loi_chu_khong_chon_ngam():
    flow = parse_flow(_one_case("        - tap_text: {id: btnX, text: Home}\n"))
    assert not flow.ok
    assert any("chọn một cái" in e for e in flow.errors)


# --- Kieu du lieu YAML --------------------------------------------------------

def test_clear_prefs_sai_kieu__bao_loi_chu_khong_RAISE():
    """Truoc khi sua: tuple(1) -> TypeError -> POST /event/flow tra 500 thay vi
    200 kem errors, pha hop dong cua route."""
    for value in ("1", "true", "1.5"):
        flow = parse_flow("- event: e\n  cases:\n    - reset: {clear_prefs: "
                          + value + "}\n      steps: [launch]\n")
        assert not flow.ok, value
        assert any("clear_prefs" in e for e in flow.errors), value


def test_bool_khong_nhay_trong_remote_config__chan_doan_sai_neu_lot():
    """`true` -> str(True) = 'True', lech voi 'true' may giu -> prepare() tra
    BLOCKED kem message quy toi build dat minimumFetchInterval = 0. Tester di
    soi build trong khi loi nam o mot cap nhay thieu."""
    flow = parse_flow("- event: e\n  cases:\n"
                      "    - reset: {remote_config: {rate_enable: true}}\n"
                      "      steps: [launch]\n")
    assert not flow.ok
    assert any('"true"' in e for e in flow.errors), flow.errors


def test_bool_khong_nhay_trong_params__FAIL_VALUE_oan_neu_lot():
    flow = parse_flow("- event: e\n  cases:\n    - params: {is_new: true}\n"
                      "      steps: [launch]\n")
    assert not flow.ok


def test_timeout_am():
    """timeout am -> `_wait_text` khong vao vong lap lan nao -> AdbError ngay,
    ma report doc ra nhu 'khong cho duoc chu do xuat hien'."""
    flow = parse_flow(_one_case("        - wait_text: {text: Home, timeout: -5}\n"))
    assert not flow.ok
    assert any("âm" in e for e in flow.errors)


def test_khoa_YAML_trung__khong_im_lang_lay_cai_sau():
    """yaml mac dinh lay cai sau -> case chay thieu buoc -> FAIL oan."""
    flow = parse_flow("- event: e\n  cases:\n    - steps: [launch, back]\n"
                      "      steps: [home]\n")
    assert not flow.ok
    assert any("khai hai lần" in e for e in flow.errors)


# --- Bat bien ma runner dua vao nhung parser truoc day khong thuc thi --------

def test_nhan_case_trung__expectations_khoa_theo_nhan():
    """`expectations()` la dict keyed by label -> hai case cung nhan thi mot
    cai de mat expectations cua cai kia, va ca hai cua so nhan cung mot bo."""
    flow = parse_flow("- event: e\n  cases:\n    - params: {p: home}\n"
                      "      steps: [launch]\n    - params: {p: home}\n"
                      "      steps: [back]\n")
    assert not flow.ok
    assert any("trùng với case trước" in e for e in flow.errors)


def test_nhan_khac_nhau_thi_khong_bi_chan():
    flow = parse_flow("- event: e\n  cases:\n    - params: {p: home}\n"
                      "      steps: [launch]\n    - params: {p: result}\n"
                      "      steps: [back]\n")
    assert flow.ok and len(flow.cases) == 2


def test_case_co_step_loi_thi_bo_CA_case():
    """Chay case thieu buoc con te hon khong chay: no ra ket luan ve app dua
    tren duong di khong phai duong tester mo ta."""
    flow = parse_flow(_one_case("        - launch\n        - tap_di: x\n"))
    assert flow.cases == ()


# --- Loi bi mat / bao sai noi dung -------------------------------------------

def test_steps_rong_bao_dung_noi_dung_chu_khong_bao_sai_kieu():
    flow = parse_flow("- event: e\n  cases:\n    - steps: []\n")
    assert any("steps rỗng" in e for e in flow.errors)
    assert not any("phải là một danh sách" in e for e in flow.errors)


def test_loi_reset_khong_bi_mat_khi_case_thieu_step():
    """Bo case som thi loi reset bien mat -> tester sua step, chay lai, moi lo
    ra loi reset. Dung vong lap ma 'gom het loi mot luot' ton tai de tranh."""
    flow = parse_flow("- event: e\n  cases:\n    - steps: []\n"
                      "      reset: {pm_clear: true}\n")
    assert any("pm_clear" in e for e in flow.errors)


# --- Phim va chuoi go: bat luc doc file, khong doi luc chay -------------------

def test_phim_ngoai_whitelist_bi_chan_NGAY_LUC_PARSE():
    """Doi den luc chay thi case da reset RC, xoa prefs, force-stop, mo lai app
    va chen moc roi moi bao not_tested vi mot chu go sai - mat ca mot chu ky
    chay may. POWER lai la phim lam hong ca phien test."""
    for name in ("POWER", "BAKC", "SLEEP"):
        flow = parse_flow(_one_case(f"        - key: {name}\n"))
        assert not flow.ok, name
        assert any(name in e and "không được phép" in e for e in flow.errors), name


def test_whitelist_phim_lay_tu_adb_input_chu_khong_khai_lai():
    flow = parse_flow(_one_case("        - key: xyz\n"))
    assert all(key in flow.errors[0] for key in sorted(KEYEVENTS))


def test_dau_nhay_trong_type_bi_chan_som():
    # `adb_input.input_text` raise vi dau nhay - bat luc doc file cho re hon.
    flow = parse_flow(_one_case('        - type: "it\'s me"\n'))
    assert not flow.ok
    assert any("dấu nháy" in e for e in flow.errors)


def test_launch_kem_doi_so__package_khai_o_cap_flow():
    # Dang nay co trong vi du cua tai lieu phase nen tester se go dung the.
    flow = parse_flow(_one_case("        - launch: {package: com.other.app}\n"))
    assert not flow.ok
    assert any("không nhận đối số" in e for e in flow.errors)


def test_package_sai_dinh_dang_bi_bao():
    flow = parse_flow("package: 'khong hop le!'\nevents:\n  - event: e\n"
                      "    cases:\n      - steps: [launch]\n")
    assert any("package" in e.lower() for e in flow.errors)


# --- Hop dong voi runner: khong hardcode danh sach kind trong test ------------

def test_MOI_kind_sinh_duoc_deu_chay_qua_run_step(recorder, metrics, no_sleep):
    """Test o file kia chi chay cac kind CO TRONG fixture - `type` va `home`
    chua di qua `run_step` lan nao. Day chay du ca bay kind."""
    from usv import event_flow_run

    flow = parse_flow(_one_case(
        "        - launch\n"
        "        - home\n"
        "        - back\n"
        "        - key: ENTER\n"
        "        - type: xin chao\n"
        "        - wait: 1s\n"
        "        - wait_text: Japandi Style\n"
        "        - tap_id: tvQuestionTitle\n"
        "        - tap_text: Japandi Style\n"
        "        - swipe: {id: rvQuestion, dir: down}\n"), package="com.x")
    assert flow.ok, flow.errors

    async def drive():
        for step in flow.cases[0].steps:
            await event_flow_run.run_step(recorder, "S1", metrics, "com.x", step)

    asyncio.run(drive())
    assert {s.kind for s in flow.cases[0].steps} == {
        "launch", "key", "type", "wait", "wait_text", "tap", "swipe"}
    assert "type:xin chao" in recorder.done
    assert "key:HOME" in recorder.done and "key:BACK" in recorder.done


# --- Mang reset truoc day khong co mot assert nao ----------------------------

def test_clear_prefs_dang_chuoi_thanh_tuple_mot_phan_tu(flow_yaml):
    assert parse_flow(flow_yaml).cases[1].reset.clear_prefs == ("apero_rate_prefs.xml",)


def test_remote_config_giu_nguyen_chuoi_da_nhay(flow_yaml):
    assert parse_flow(flow_yaml).cases[0].reset.remote_config == {
        "rate_popup_enable": "true"}


def test_relaunch_mac_dinh_True__app_doc_gia_tri_moi_luc_process_start(flow_yaml):
    assert parse_flow(flow_yaml).cases[0].reset.relaunch is True
    flow = parse_flow("- event: e\n  cases:\n    - reset: {relaunch: false}\n"
                      "      steps: [launch]\n")
    assert flow.cases[0].reset.relaunch is False


def test_case_khong_khai_reset_thi_reset_rong(flow_yaml):
    assert parse_flow(flow_yaml).cases[2].reset.empty
