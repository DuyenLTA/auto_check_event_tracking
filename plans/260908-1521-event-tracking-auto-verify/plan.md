---
title: "Auto-verify Event Tracking (Firebase Analytics)"
status: in-progress
created: 2026-09-08
source: plans/reports/from-brainstorm-to-planner-260908-1521-event-tracking-auto-verify-report.md
blockedBy: []
blocks: []
---

# Auto-verify Event Tracking

Đối chiếu event Firebase Analytics app thật bắn ra với bảng spec tester dán vào,
ra report pass/fail theo mẫu tool check ID ads. Tab mới trong `ui-spec-verifier`.

**Brainstorm + spike:** [report](../reports/from-brainstorm-to-planner-260908-1521-event-tracking-auto-verify-report.md)
**Mock report:** [mock HTML](../reports/260908-1521-event-report-mock.html) · https://claude.ai/code/artifact/d33633ec-6594-457f-a024-ac4b153f27e5
**Fixture:** `tests/fixtures/fa-events-aip922.log` (134 dòng, đã redact)

## Phase

| # | Phase | Ưu tiên | Trạng thái | File |
|---|---|---|---|---|
| 1 | Verdict + config nền tảng — **test trước** | P1 | completed | [phase-01](phase-01-verdict-va-config-nen-tang.md) |
| 2 | Parse spec dán TSV — **rủi ro cao nhất** | P1 | completed | [phase-02](phase-02-parse-spec-dan-tsv.md) |
| 3 | Capture logcat + parse FA-SVC | P1 | completed | [phase-03](phase-03-capture-logcat-va-parse-fa.md) |
| 4 | Cắt cửa sổ theo marker + chấm check | P1 | completed | [phase-04](phase-04-cat-cua-so-va-cham-check.md) |
| 5 | Report theo mẫu tool ads | P2 | completed | [phase-05](phase-05-report-theo-mau-tool-ads.md) |
| 6 | Route + tab web (luồng bấm tay) | P2 | completed | [phase-06](phase-06-route-va-tab-web.md) |
| 7 | Driver tự động lái app theo flow | P2 | pending | [phase-07](phase-07-driver-tu-dong-lai-app.md) |

Phụ thuộc tuyến tính 1→2→3→4→5→6→7. Phase 2 và 3 độc lập nhau, chạy song song được.

**Phase 7 thay cái NÚT BẤM marker, không thay tầng check** — script tự chèn `USV_MARK`
nên phase 1→6 không đổi một dòng. Luồng bấm tay ở phase 6 **vẫn cần** làm fallback:
`app_shortcut` không lái được bằng tap trong app.

## Ràng buộc tuyệt đối (user đã chốt từng cái)

- **Chỉ Firebase Analytics.** Không Adjust, không AppsFlyer.
- **Nạp spec bằng dán TSV vào ô text.** Không Google Sheet, không upload file.
- **Gán nhãn từng bước, MỘT nút một bước** — marker bước sau là điểm kết bước trước.
- **FAIL khi:** thiếu param spec khai · giá trị ngoài danh sách · bắn trùng trong cùng cửa sổ · app gửi thêm param.
- **Report theo mẫu `ad-checklist-diff`**, KHÔNG dùng `report_css.py` / `report_blocks.py` / `report_matrix.py`.
- ⚠️ **ĐÃ ĐỔI (2026-09-08, sau phase 5):** user chốt lại là **repo RIÊNG**, không phải tab
  trong `ui-spec-verifier`. Xem mục "Tách repo" ở cuối file.
- **Verdict CHỈ THÊM**, không đổi tên 5 cái đang có — `check_models.py:38` ghi rõ lý do (giá trị enum nằm trong xlsx và report cũ).
- Mọi module **<200 LOC**. Không `shell=True`. Test **xanh khi không cắm máy** (marker `device`).
- `UNMATCHED` / `EXTRA` / `NOT_TESTED` **không bao giờ** tính vào fail.
- Không verify được thì nói không verify được, **không pass giả**.

## Facts đã đo, KHÔNG verify lại

| Việc | Số đo |
|---|---|
| Tag chở event | **`FA-SVC`**, không phải `FA`. `FA` in `Logging telemetry`, không kèm params |
| Format | `Logging event: origin=app,name=EVENT(_short),params=Bundle[{k(_s)=v, k=v}]` |
| Lọc 2 tầng | device `adb logcat -s FA-SVC:V USV_MARK:I` → 12 964→1 259 · host `Logging event:` → 67 |
| origin | `app` 42 · `auto` 8 · `am` 17 |
| Param hệ thống | tiền tố `ga_` / `_` |
| Tách param | lookahead `,\s+(?=[A-Za-z_][\w.]*(\([^)]*\))?=)` — **verified 67/67**, không `split(", ")` |
| Marker | `adb shell log -t USV_MARK` nằm chung timeline → không lệch giờ host/device |
| setprop | không cần root · **không sống qua reboot** · app phải restart sau khi set |
| Dòng bị cắt | 0/67, dài nhất 513 B, trần payload 4 068 B |

## Câu chưa chốt — ĐỪNG tự quyết

1. Cột `Screen Name` đối chiếu thế nào (log cho `ga_screen_class=...Activity`, spec ghi "Home") — vòng 1 **chỉ in ra, không chấm**
2. Bảng spec thật có bao nhiêu event/screen — đổi hẳn UX bấm marker
3. Có app nào global param tự khai không (AIP922 không có)
4. `NOT_VERIFIABLE` String-vs-Number có gây ồn không — chưa đo được
5. **Reset giữa các case ở phase 7** — popup rating bị chặn tần suất nên lái tới
   `home` 4 lần không hiện 4 lần. `pm clear` (mất data/login) hay override Remote
   Config (đã có kỹ thuật patch `frc_*.json` + throttle)? Phần khó nhất của phase 7,
   khó hơn chuyện tapping.
6. Đổi tên repo/tool khi thêm tab

---

## Tách repo (2026-09-08, sau khi phase 5 xong)

Ban đầu user chốt "cùng repo, tab mới". Sau khi push, user đổi: *"bỏ hết figma với pen ra,
cái đấy là tool khác"*. Đã làm theo.

**Repo này** (`auto_check_event_tracking`) giờ chỉ còn tool event.
**Tool UI** (Figma/pen.dev) ở lại `DuyenLTA/ui-spec-verifier` — remote `archive`.

### Bỏ đi
Toàn bộ `figma_*` · `pen_*` · `matcher` + `match_*` · 10 check UI · `report_*` của tab UI ·
`session_state` · `routes_*` · `web/` · `color_*` · `evidence` · `geometry_util` ·
`design_payload` · `group_run` · `env_config` · `screencap` · `check_context` ·
`check_mapping` · `icon_coverage` + test và fixture của chúng (**65 module**).

### Giữ lại và vì sao
| Module | Lý do |
|---|---|
| `adb_client` + `adb_logcat` + `adb_parsers` | chạy adb, chèn mốc. `adb_client` **không** hiện trong closure vì `logcat_stream` nhận client qua tham số (duck-typing) — static analysis không thấy, phải thêm tay |
| `check_models` · `check_config` · `check_sort` | từ vựng verdict + đọc YAML |
| `exporter` | xuất xlsx, chỉ phụ thuộc `check_models` nên dùng lại được nguyên |
| `models` (đã cắt `DesignNode`) · `ui_dump` · `density` | phase 7 cần: phân giải selector rồi bấm vào tâm `bounds` |
| `main` (đã cắt hết router) | giữ middleware chặn non-loopback — thứ đáng giữ nhất trong đó |
| `resources` | tìm `config/` |

### Dọn theo
- `check_runner` bị bỏ → tách `sort_for_report` sang `check_sort.py`. Một dòng
  `from .check_runner import sort_for_report` kéo theo **20 module** không liên quan
  (toàn bộ `checks/`, qua đó là `matcher`, `match_*`, `models`, `color_*`).
- `Verdict`: bỏ 7 `FAIL_*` của UI + `UNMATCHED`. Còn 9 giá trị, tất cả đều được tool này
  dùng thật. Có test khoá: `test_khong_con_verdict_cua_tool_UI`.
- `models_geometry` bị bỏ → gộp `Bounds` về `models.py` (109 LOC).
- `check_config`: bỏ `tolerance` · `scale_mode` · `min_iou` · `drop_ads` ·
  `case_sensitive` · `exact_whitespace` · `ignore_nodes` — đều là chuyện của matcher UI.
  165 → 109 LOC. Không khai check nào thì **bật hết** (tắt mặc định thì report rỗng mà
  không ai biết vì sao).
- `config/ui-check-rules.yaml` → `config/event-check-rules.yaml`, bỏ `node-mapping.yaml`.
- Dependency: bỏ `pillow` (lấy màu pixel) và `python-multipart` (upload `.pen`). Còn
  `fastapi` · `uvicorn` · `pyyaml` · `openpyxl`.
- `.env` không còn cần token nào. `start.sh` tự lo `ADB_PATH`, `find_adb` đọc env var,
  nên `env_config` bỏ được mà không mất gì.

### Giá phải trả, nói thẳng
`adb_client` · `adb_parsers` · `check_models` · `ui_dump` · `models` · `density` giờ **tồn
tại ở cả hai repo**. Sửa bug ở tầng adb là phải sửa hai nơi. Đã cảnh báo trước khi tách,
user quyết tách.

### Test
577 → **152**. Giảm vì test của code đã bỏ cũng bỏ theo. Toàn bộ 152 xanh khi rút cáp.
