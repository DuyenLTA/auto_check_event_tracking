"""Link artifact: nut tren trang tro thang toi artifact, khong phai cho Claude.

Cai de sai nhat la STALE: artifact la cua luot truoc ma nut trong nhu cua luot
vua chay, roi tester gui cho team mot bao cao cu. Nen phai luu kem
`generated_at` va doi chieu.
"""

from __future__ import annotations

import json

from usv import artifact_link

URL = "https://claude.ai/code/artifact/43b243a5-cb0f-4482-9601-042ba7cacc73"


def test_chua_publish_thi_tra_rong(tmp_path):
    assert artifact_link.doc(tmp_path) == {}


def test_ghi_roi_doc_lai(tmp_path):
    artifact_link.ghi(URL, "2026-09-10 16:46", tmp_path)
    assert artifact_link.doc(tmp_path) == {"url": URL,
                                          "generated_at": "2026-09-10 16:46"}


def test_file_hong_khong_lam_sap(tmp_path):
    """Nut artifact chi la tien nghi - bao cao local van phai xem duoc."""
    (tmp_path / artifact_link.TEN_FILE).write_text("{ khong phai json", encoding="utf-8")
    assert artifact_link.doc(tmp_path) == {}


def test_tu_choi_url_khong_phai_https(tmp_path):
    """Chan url la: nut nay se duoc bam va gui di cho nguoi khac."""
    (tmp_path / artifact_link.TEN_FILE).write_text(
        json.dumps({"url": "javascript:alert(1)"}), encoding="utf-8")
    assert artifact_link.doc(tmp_path) == {}
