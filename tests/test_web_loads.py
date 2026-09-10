"""Kiem JS bang node tren DOM gia: trang co khoi tao duoc, vong do may co dung.

Vi sao khong test duoc bang cach khac: mot loi o tang module (goi ham chua
dinh nghia chang han) lam moi dong phia sau khong chay, nhung file van tra
200 va moi test HTTP van xanh. Da gap that - applyMode() duoc goi ma khong co
than ham, o "dang tim may..." dung nguyen suot mot ngay.

Khong co node thi bo qua: node khong phai thu bat buoc de chay tool.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CHECKS = ["check-web-loads.js", "check-device-watch.js"]


@pytest.mark.skipif(shutil.which("node") is None, reason="khong co node")
@pytest.mark.parametrize("name", CHECKS)
def test_kiem_js_bang_node(name: str):
    done = subprocess.run(["node", str(SCRIPTS / name)], capture_output=True,
                          text=True, timeout=30)
    assert done.returncode == 0, done.stdout + done.stderr
