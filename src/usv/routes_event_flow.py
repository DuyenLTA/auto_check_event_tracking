"""Route soi flow: doc file flow YAML roi tra case va loi cho bang preview.

Tach khoi routes_event vi route nay KHONG cham vao may va KHONG dung vao
state: no chi dich mot file thanh cau truc de tester soi truoc khi chay. Ca
hai thu kia la toan bo cong viec cua routes_event, nen de chung thi moi lan
sua mot ben phai doc ben kia.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .event_flow_parse import parse_flow

router = APIRouter()


class FlowRequest(BaseModel):
    text: str = Field(default="", max_length=2_000_000)
    package: str = ""


@router.post("/event/flow")
async def load_flow(request: FlowRequest) -> dict:
    """Doc flow YAML -> tra case va loi cho bang preview. KHONG chay gi tren may.

    Tra 200 ke ca khi co loi, cung ly do `/event/spec`: flow sai la loi du lieu
    cua tester, can thay het cho sai mot luot de sua.

    Khong luu vao state: buoc nay chi de tester soi flow truoc khi chay. Cai
    `fragile` trong payload la canh bao selector khop theo chu - vo khi doi
    ngon ngu, bao chu khong chan.
    """
    return parse_flow(request.text, request.package).payload()
