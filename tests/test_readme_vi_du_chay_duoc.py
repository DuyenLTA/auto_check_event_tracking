"""Vi du Python trong README phai CHAY DUOC, khong chi doc duoc.

Vi sao can: README la thu duy nhat nguoi moi doc truoc khi go lenh dau tien.
Doi API roi quen sua README thi ho copy mot doan code chet, va ket luan tool
hong chu khong ket luan tai lieu cu. Da gap that - vi du con goi `cut_log()`
sau khi giao dien bo han co che moc, tuc la doan do khong con chay dung.

Test rut code ra tu chinh README roi chay, nen khong the lech.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).parent.parent
README = (GOC / "README.md").read_text(encoding="utf-8")
FIXTURES = Path(__file__).parent / "fixtures"

_KHOI = re.compile(r"## Gọi từ Python.*?```python\n(.*?)```", re.S)


def test_readme_co_vi_du_python():
    assert _KHOI.search(README), "README mat muc 'Gọi từ Python'"


def test_vi_du_trong_readme_chay_duoc_va_ra_report(tmp_path: Path):
    code = _KHOI.search(README).group(1)
    # Vi du doc hai file nay theo dung ten do - giu nguyen de khong phai sua
    # code lay tu README.
    shutil.copy(FIXTURES / "event-spec-rating.tsv", tmp_path / "spec.tsv")
    shutil.copy(FIXTURES / "fa-events-aip922.log", tmp_path / "capture.log")
    (tmp_path / "vi_du.py").write_text(code, encoding="utf-8")

    done = subprocess.run([sys.executable, "vi_du.py"], cwd=tmp_path,
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "rating_placement_viewed" in html, "report khong co event nao"
