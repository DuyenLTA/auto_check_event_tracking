"""Ghi chu TRIAGE cho tung dong FAIL: lo i do dau ra.

Tool chi noi duoc "spec doi X, app gui Y". Cau hoi ke tiep - app thieu that,
hay app doi ten event, hay spec cu roi - phai doc them trang spec va log tho
moi tra loi duoc. Viec do do agent lam (chay trong Claude Code), roi POST ket
qua vao day; tool chi LUU va HIEN, khong tu suy ra gi.

BA RANG BUOC, thieu cai nao la ghi chu thanh nguon sai lech moi:

1. Chi gan duoc vao dong DANG FAIL. Gan mot "ket luan" vao dong dang PASS thi
   nguoi doc tuong dong do cung co van de.
2. Phai khop `generated_at` cua luot dang xem. Ghi chu cua luot truoc dan vao
   luot sau la kieu sai im lang - da gap dung benh nay o nut artifact.
3. `bo_sot` phai duoc in ra. Cat bot vi qua nhieu loi ma khong noi thi bao cao
   trong nhu da soi het.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Bon ket luan, dung bon. Mo rong tuy y thi moi agent tra ve mot chu khac nhau
# va bao cao khong con doc luot duoc nua.
KET_LUAN = {
    "app_thieu": "App thiếu event thật",
    "app_doi_ten": "App đổi tên event",
    "spec_cu": "Spec đã cũ",
    # Tester khong di toi man do thi event KHONG ban la dung, khong phai bug.
    # Thieu muc nay thi moi lan test do dang deu bi dam thanh "app thieu
    # event", va dev mat thoi gian di tim mot bug khong ton tai. Spec 40-60
    # event thi bo sot vai man la chuyen binh thuong.
    "chua_thao_tac": "Chưa thao tác tới bước này",
    "khong_do_duoc": "Tool không đo được",
}

MAX_LY_DO = 400
MAX_BANG_CHUNG = 300


class TriageError(ValueError):
    """Du lieu triage sai - tra 400, khong phai 500."""


@dataclass(frozen=True, slots=True)
class TriageNote:
    """Mot ghi chu cho mot dong trong bang."""

    element: str          # dung khoa cua CheckResult.element
    ket_luan: str         # mot trong KET_LUAN
    ly_do: str            # cau giai thich cho nguoi doc
    bang_chung: str = ""  # gio, ten event thay the... - thu kiem lai duoc
    # So agent phan bien da DONG Y tren tong so da hoi. Hien ra de nguoi doc
    # biet ghi chu nay chac den dau: 3/3 khac han 2/3.
    dong_y: int = 0
    tong: int = 0

    @property
    def nhan(self) -> str:
        return KET_LUAN[self.ket_luan]

    @property
    def phieu(self) -> str:
        """'2/3 agent đồng ý', rong khi khong co bo phan bien."""
        return f"{self.dong_y}/{self.tong} agent đồng ý" if self.tong else ""

    def payload(self) -> dict:
        return {"element": self.element, "ket_luan": self.ket_luan,
                "nhan": self.nhan, "ly_do": self.ly_do,
                "bang_chung": self.bang_chung,
                "dong_y": self.dong_y, "tong": self.tong}


@dataclass(frozen=True, slots=True)
class TriageBatch:
    """Ket qua triage cua MOT luot cham."""

    notes: dict[str, TriageNote] = field(default_factory=dict)
    # So dong FAIL khong duoc triage (agent chet, hoac cat bot vi qua nhieu).
    bo_sot: int = 0
    generated_at: str = ""

    def cho(self, element: str) -> TriageNote | None:
        return self.notes.get(element)

    def payload(self) -> dict:
        return {"notes": [n.payload() for n in self.notes.values()],
                "bo_sot": self.bo_sot, "generated_at": self.generated_at}


def _chuoi(raw, ten: str, gioi_han: int) -> str:
    if not isinstance(raw, str):
        raise TriageError(f"{ten} phải là chuỗi, đang là {type(raw).__name__}.")
    value = raw.strip()
    if len(value) > gioi_han:
        raise TriageError(f"{ten} dài quá {gioi_han} ký tự.")
    return value


def _mot_note(raw: dict, cho_phep: set[str]) -> TriageNote:
    if not isinstance(raw, dict):
        raise TriageError("Mỗi ghi chú phải là một object.")

    element = _chuoi(raw.get("element"), "element", 200)
    if element not in cho_phep:
        # Khong im lang bo qua: agent gan nham dong thi phai biet ngay, chu
        # khong de bao cao thieu mot ghi chu ma khong ai hay.
        raise TriageError(
            f"Không gắn được ghi chú vào {element!r}: dòng này không nằm trong "
            "danh sách FAIL của lượt chấm hiện tại. Chỉ triage được dòng đang "
            "lỗi.")

    ket_luan = _chuoi(raw.get("ket_luan"), "ket_luan", 40)
    if ket_luan not in KET_LUAN:
        raise TriageError(
            f"ket_luan {ket_luan!r} không hợp lệ. Dùng một trong: "
            + ", ".join(sorted(KET_LUAN)))

    ly_do = _chuoi(raw.get("ly_do"), "ly_do", MAX_LY_DO)
    if not ly_do:
        raise TriageError(f"{element}: thiếu ly_do — ghi chú không có lý do "
                          "thì người đọc không kiểm lại được.")

    dong_y, tong = _phieu(raw)
    return TriageNote(
        element=element, ket_luan=ket_luan, ly_do=ly_do,
        bang_chung=_chuoi(raw.get("bang_chung", ""), "bang_chung", MAX_BANG_CHUNG),
        dong_y=dong_y, tong=tong)


def _phieu(raw: dict) -> tuple[int, int]:
    """(dong_y, tong). Chap nhan khong khai, nhung khai thi phai hop le."""
    dong_y, tong = raw.get("dong_y", 0), raw.get("tong", 0)
    if not isinstance(dong_y, int) or not isinstance(tong, int):
        raise TriageError("dong_y và tong phải là số nguyên.")
    if dong_y < 0 or tong < 0:
        raise TriageError("dong_y và tong không được âm.")
    if dong_y > tong:
        raise TriageError(f"dong_y ({dong_y}) lớn hơn tong ({tong}).")
    return dong_y, tong


def doc(payload: dict, *, fail_elements: set[str],
        generated_at: str) -> TriageBatch:
    """Doc payload tu agent thanh TriageBatch da kiem.

    `fail_elements` la cac dong DANG FAIL cua luot hien tai - xem rang buoc 1
    o dau file.
    """
    if not isinstance(payload, dict):
        raise TriageError("Payload phải là một object.")

    raw_notes = payload.get("notes", [])
    if not isinstance(raw_notes, list):
        raise TriageError("notes phải là một mảng.")

    notes: dict[str, TriageNote] = {}
    for raw in raw_notes:
        note = _mot_note(raw, fail_elements)
        if note.element in notes:
            raise TriageError(f"{note.element}: gắn hai ghi chú cho cùng một dòng.")
        notes[note.element] = note

    bo_sot = payload.get("bo_sot")
    if bo_sot is None:
        # Khong khai thi TU TINH: so dong FAIL chua co ghi chu. Mac dinh 0 se
        # bao "da soi het" cho mot lan triage lam do dang.
        bo_sot = len(fail_elements) - len(notes)
    if not isinstance(bo_sot, int) or bo_sot < 0:
        raise TriageError("bo_sot phải là số nguyên không âm.")

    return TriageBatch(notes=notes, bo_sot=bo_sot, generated_at=generated_at)
