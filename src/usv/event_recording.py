"""Trang thai mot phien ghi logcat.

Tach khoi logcat_stream vi day la DU LIEU, con logcat_stream la dieu khien
process. Ba co o day tra loi ba cau khac nhau, va lan lon chung la nguon cua
bug that:

  stopped     - da bam Dung chua
  stream_died - ong da dong ma chua ai bam Dung (may rot khoi USB)
  live        - con dang ghi THAT = ca hai co tren deu tat

Lay `not stopped` lam "dang ghi" thi mot phien da chet van bi tinh la dang
chay, va tool chan lan Ghi tiep theo bang mot thong bao sai su that.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Recording:
    """Mot phien ghi dang mo."""

    serial: str
    package: str
    lines: list[str] = field(default_factory=list)
    marks: list[str] = field(default_factory=list)
    process: object | None = None
    reader: object | None = None      # asyncio.Task doc stream lien tuc
    stopped: bool = False
    # Stream chet TRUOC khi ai bam Dung: rut may, USB ngu, mat authorize.
    # Phan con lai cua phien khong duoc ghi -> KHONG duoc ket luan app thieu
    # event. Cung nguyen tac voi fa_silent. Xem _pump.
    stream_died: bool = False
    # App duoi test da tung chay trong phien nay chua. Lay mau luc bat dau va
    # luc dung. Chua tung thay -> event bat duoc la cua app KHAC, xem
    # checks/event_presence.py.
    app_seen: bool = False
    # App dang o foreground luc Dung ghi, chi ghi khi app_seen=False. De bao
    # cao chi thang ten dung cho tester thay vi de ho tu do lai bang mat.
    foreground: str = ""
    # stop() da duoc goi -> EOF sap toi la CO Y, khong phai dut.
    stopping: bool = False

    @property
    def live(self) -> bool:
        """Con dang ghi THAT.

        Khac han `not stopped`: may rot khoi USB thi ong da dong, khong con ghi
        gi nua, ma `stopped` van False vi chi stop() moi bat no. Lay `not
        stopped` lam "dang ghi" thi tool chan luon lan Ghi tiep theo bang mot
        thong bao sai su that.
        """
        return not self.stopped and not self.stream_died

    @property
    def fa_silent(self) -> bool:
        """Khong co dong FA nao -> khong doc duoc log Firebase (R3).

        Khac han "app khong ban event": voi truong hop nay tuyet doi KHONG duoc
        ket luan app thieu event.
        """
        return not any("/FA" in line for line in self.lines)

    def text(self) -> str:
        return "\n".join(self.lines)

    def payload(self) -> dict:
        return {"serial": self.serial, "package": self.package,
                "line_count": len(self.lines), "marks": list(self.marks),
                "stopped": self.stopped, "fa_silent": self.fa_silent,
                "stream_died": self.stream_died,
                "app_seen": self.app_seen,
                "foreground": self.foreground}
