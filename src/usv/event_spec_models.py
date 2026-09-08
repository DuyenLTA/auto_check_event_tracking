"""Tu vung spec event tracking: SpecParam, SpecEvent, SpecSheet.

Bang spec cua tester co 8 cot (Screen Name, Event_Name, Triggered, Params,
Param Description, Value Type, Value, Value Description). Ba cot quyet dinh
pass/fail la Event_Name, Params, Value Type + Value; con lai la van xuoi cho
nguoi doc.

Cot `Triggered` KHONG cham verdict: no la van xuoi ("Khi man rating hien thi")
nen chi dung lam NHAN cho nut bam cua tester, de ho biet phai lam dong tac gi.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SpecParam:
    """Mot param cua mot event, kem danh sach gia tri cho phep."""

    name: str
    value_type: str                      # "String" | "Number" | "Boolean" | ...
    allowed: tuple[str, ...] = ()        # rong = free-form
    description: str = ""

    @property
    def free_form(self) -> bool:
        """Cot Value de trong -> khong co danh sach de doi chieu.

        Luc do chi kiem CO MAT va KIEU, khong kiem gia tri. Nhieu param that su
        la free-form (ten file nguoi dung chon, ma loi tu SDK) nen bat buoc phai
        co duong nay - khong thi tester phai liet ke vo han gia tri.
        """
        return not self.allowed

    @property
    def wants_number(self) -> bool:
        return self.value_type.strip().casefold() in {"number", "int", "long",
                                                      "double", "float"}

    @property
    def wants_string(self) -> bool:
        return self.value_type.strip().casefold() in {"string", "text"}


@dataclass(frozen=True, slots=True)
class SpecEvent:
    """Mot event trong spec, kem cac param cua no."""

    name: str
    screen: str = ""
    triggered: str = ""
    params: tuple[SpecParam, ...] = ()

    def param(self, name: str) -> SpecParam | None:
        for p in self.params:
            if p.name == name:
                return p
        return None

    @property
    def param_names(self) -> frozenset[str]:
        return frozenset(p.name for p in self.params)

    def payload(self) -> dict:
        return {
            "name": self.name,
            "screen": self.screen,
            "triggered": self.triggered,
            "params": [
                {"name": p.name, "value_type": p.value_type,
                 "allowed": list(p.allowed), "free_form": p.free_form,
                 "description": p.description}
                for p in self.params
            ],
        }


@dataclass(frozen=True, slots=True)
class SpecSheet:
    """Ket qua parse ca bang.

    Tra CA `events` LAN `errors` chu khong raise: tester can thay dong nao sai de
    tu sua trong o text, con nhung dong dung thi vao preview luon.
    """

    events: tuple[SpecEvent, ...] = ()
    errors: tuple[str, ...] = ()
    columns: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """Du dieu kien cho Ghi. Con loi la khong cho - spec sai thi bao cao sai."""
        return bool(self.events) and not self.errors

    def event(self, name: str) -> SpecEvent | None:
        for e in self.events:
            if e.name == name:
                return e
        return None

    def payload(self) -> dict:
        return {
            "ok": self.ok,
            "columns": list(self.columns),
            "events": [e.payload() for e in self.events],
            "errors": list(self.errors),
            "event_count": len(self.events),
            "param_count": sum(len(e.params) for e in self.events),
        }
