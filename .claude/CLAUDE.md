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
PYTHONPATH=src .venv/bin/python -m pytest -q        # test (hiện 665 passed)
```

## Trạng thái git (18/09/2026)

- `main` = `213e156`, đã fast-forward từ remote `anduyen`
  (`github.com/LuuThiAnDuyen/check_event_track` — cùng root commit `43972c0`, đi trước 22 commit).
- `main` **đi trước `origin/main` 22 commit — chưa push**.
- Remote: `origin` (DuyenLTA/auto_check_event_tracking), `anduyen` (LuuThiAnDuyen/check_event_track),
  `archive` (DuyenLTA/ui-spec-verifier — history cũ).
- Toàn bộ test pass sau merge.

## Việc còn dở (uncommitted)

Nhánh sinh khung case từ trang spec — chưa commit:

- Sửa: `README.md` (thêm mục "Sinh khung case từ trang spec"), `src/usv/event_recording.py`,
  `src/usv/logcat_stream.py`
- Mới: `src/usv/spec_case_skeleton.py`, `spec_case_rules.py`, `spec_cases_cli.py`,
  `spec_prose_sections.py`, `event_shot.py`, `.claude/workflows/spec-to-cases.js`,
  `tests/test_spec_case_skeleton.py`, `tests/test_event_shot.py`

Đo trên máy thật (Pixel 4, `ai.photogenerator.aivideo.aivideogenerator.aiart` 3.1.0):
`rating_star_clicked` bắn ngay khi chạm sao, không đợi RATE → nhóm case star **không cần**
`pm_clear`; chỉ nút RATE mới tắt popup vĩnh viễn.

## Nguyên tắc

- Không verify được thì nói không verify được — đừng đổi thành lỗi selector.
- Chốt chặn phải là **exit code / con số**, không phải agent tự đọc kết luận của mình.
- Không mock, không fake data chỉ để CI xanh.
