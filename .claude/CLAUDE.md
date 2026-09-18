# CLAUDE.md — Auto Check Event Tracking

Tài liệu cho Claude Code khi làm việc trong repo này. Cập nhật tay khi trạng thái đổi.

## Đọc trước

| File | Nội dung |
|---|---|
| `SKILL.md` | Điểm vào cho agent: 2 lệnh CLI (`usv-check`, `usv-record`), quy ước chạy nền, đọc JSON ở stdout |
| `README.md` | Tài liệu đầy đủ: verdict, format bảng spec, cách đọc logcat, sinh khung case từ spec |
| `flows/README.md` | Format file flow YAML — đường đi để lái app |
| `.claude/workflows/triage-event-fail.js` | Fan-out agent soi nguyên nhân từng dòng FAIL |
| `.claude/workflows/spec-to-cases.js` | Sinh khung case từ trang spec + dò bước bấm trên máy thật |

## Lệnh hay dùng

```bash
.venv/bin/python -m pip install -e .                # lần đầu
usv-check --spec <link Confluence> --package <pkg>  # chạy nền, stdout = 1 dòng JSON
usv-record --package <pkg> dump                     # ghi flow
usv-cases dump "<link Confluence>"                  # spec -> text cho agent doc
usv-cases check out/cases.json --url "<link>"       # doi chieu case voi bang spec
PYTHONPATH=src .venv/bin/python -m pytest -q        # test (hiện 678 passed)
```

## Trạng thái git (18/09/2026)

- `main` = `4ae2ee0`, **đã push, khớp `origin/main`**. Đã fast-forward 22 commit từ
  remote `anduyen` (`github.com/LuuThiAnDuyen/check_event_track` — cùng root commit).
- Remote: `origin` (DuyenLTA/auto_check_event_tracking), `anduyen`
  (LuuThiAnDuyen/check_event_track), `archive` (DuyenLTA/ui-spec-verifier — history cũ).
- Plan `plans/260908-1521-event-tracking-auto-verify/`: **cả 7 phase completed**.

## Lượt chấm thật đầu tiên (18/09/2026)

App `com.nxl.aiphotocreator.aivideogenerator.texttoimage` 2.1.0 (14), Pixel 7
`29301FDH2006K7`, spec SDK Widget → **2/2 khớp**.
Artifact: https://claude.ai/artifact/2mkNh33qpZrNk9tVgKHjia

Mất 7 lượt mới ra, 4 bản sửa: `ad_close` hai bậc mẫu · mở app đúng 1 lần sau mốc ·
`wait_text` tự dọn màn chắn · ảnh bằng chứng đúng lúc. Chi tiết ở cuối
`plans/260908-1521-event-tracking-auto-verify/phase-07-driver-tu-dong-lai-app.md`.

**Bài học:** không màn nào trong app này lên đúng giờ — mọi bước ghim cứng thời gian
đều là xúc xắc. Chốt chặn phải là "thấy gì xử cái đó".

## Nguyên tắc

- Không verify được thì nói không verify được — đừng đổi thành lỗi selector.
- Chốt chặn phải là **exit code / con số**, không phải agent tự đọc kết luận của mình.
- Không mock, không fake data chỉ để CI xanh.
