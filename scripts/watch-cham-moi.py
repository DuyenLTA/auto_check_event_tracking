"""Do tool: cham xong luot moi thi tai report ve va bao Claude republish.

Tool KHONG publish artifact duoc (chay o 127.0.0.1, khong co duong toi
claude.ai) - xem artifact_link.py. Nen o day chi lam phan may lam duoc: phat
hien luot cham moi, tai report ve dung file nguon cua artifact. Viec publish
van phai Claude goi.

Moc de so la `generated_at` cua luot cham, KHONG phai so luot: republish cung
file giu nguyen URL, nen chi can biet luot dang publish co phai luot hien tai.

In ca luc LOI: mot monitor chi in tin tot thi luc server chet se im lang, ma
im lang trong y het "chua cham lan nao".

Chay tu goc repo:  .venv/Scripts/python.exe -u scripts/watch-cham-moi.py
"""
import json
import pathlib
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out/artifact-page.html")
NHIP = 5              # giay giua hai lan do
NGUONG_LOI = 6        # ~30s khong noi duoc thi bao mot lan


def lay(path: str, timeout: float = 10.0) -> bytes:
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def main() -> None:
    da_bao = None      # generated_at da bao roi - khong bao lai
    loi_lien = 0
    da_bao_loi = False
    while True:
        try:
            data = json.loads(lay("/event/artifact", 5).decode("utf-8"))
            loi_lien = 0
            da_bao_loi = False
        except Exception as exc:
            loi_lien += 1
            if loi_lien >= NGUONG_LOI and not da_bao_loi:
                print(f"LOI: khong noi duoc tool ({exc}) - da thu {loi_lien} lan",
                      flush=True)
                da_bao_loi = True
            time.sleep(NHIP)
            continue

        gen = str(data.get("run_generated_at") or "")
        khop = data.get("khop") is True
        if gen and not khop and gen != da_bao:
            try:
                OUT.parent.mkdir(parents=True, exist_ok=True)
                OUT.write_bytes(lay("/event/report", 20))
                print(f"CHAM MOI {gen} - report da luu vao {OUT.name}, can republish",
                      flush=True)
            except Exception as exc:
                print(f"CHAM MOI {gen} - KHONG tai duoc report: {exc}", flush=True)
            da_bao = gen
        time.sleep(NHIP)


if __name__ == "__main__":
    main()
