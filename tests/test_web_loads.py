"""Tab web co khoi tao duoc khong - chay that tren DOM gia bang node.

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

SCRIPT = Path(__file__).parent.parent / "scripts" / "check-web-loads.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="khong co node")
def test_6_file_js_nap_duoc_khong_loi():
    done = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                          timeout=30)
    assert done.returncode == 0, done.stdout + done.stderr
