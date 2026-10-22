# Change log knowledge base — check-event

KB của workflow này là những file tool và agent đọc để biết phải làm gì, tách khỏi code:
`flows/*.yaml` (đường lái app), `config/event-check-rules.yaml` (ngưỡng thời gian, luật trùng,
luật thừa param), `specs.json` (tên chức năng → trang spec), `.claude/` (lệnh, workflow, CLAUDE.md),
`SKILL.md`.

Mỗi lần sửa KB: thêm một dòng vào mục "Bài học" nếu sửa vì đầu ra sai, ghi số trước và sau.
Bảng commit bên dưới sinh lại từ git bằng lệnh ở cuối file.

## Bài học (sửa vì đầu ra sai)

| Ngày | Đầu ra sai | Sửa gì | Trước → sau |
|---|---|---|---|
| 18/09/2026 | Lượt chạy thật đầu tiên trên texttoimage không ra kết quả | `ad_close` hai bậc, mở app đúng 1 lần sau mốc, `wait_text` tự dọn màn chắn | 7 lượt mới ra kết quả → 2/2 khớp |
| 05–06/10/2026 | FAIL_TIMING do mốc kích hoạt đặt sai bước | Khai `trigger: true`, `after_event`, `max_delay_ms` trong flow; ghi các kiểu mốc sai vào `check-event.md` mục 5 | Chưa đo lại riêng |
| 10/10/2026 | hairai: `daily_checkin_screen_view` báo bắn sớm 5717 ms | Mốc lấy cú bấm có hiệu lực cuối (`125623c`) | 1 sai → 2/2 khớp |
| 22/10/2026 | FAIL được publish thẳng, chưa có người xác nhận trước khi báo dev | `check-event.md` mục 6: hỏi tester từng dòng Sai, không tự log Jira | Chưa có lượt chạy sau thay đổi |

## Commit đụng tới KB

| Ngày | Commit | Loại | Thay đổi | File KB |
|---|---|---|---|---|
| 10/10/2026 | `bfb8952` | Khác | Merge remote-tracking branch 'origin/main' |  |
| 06/10/2026 | `527a84a` | Thêm quy tắc | feat(check-event): quy trinh cham thoi diem va chay le gop base | `.claude/commands/check-event.md`, `.claude/commands/record-flow.md` |
| 06/10/2026 | `125623c` | Sửa sau lỗi | fix(check): moc thoi diem lay cu bam co hieu luc cuoi, gen_fail tinh sau gen_start | `flows/ai.photogenerator.aivideo.aivideogenerator.aiart.yaml` |
| 05/10/2026 | `c17901d` | Thêm quy tắc | feat(check): cham event ban dung luc cu bam kich hoat | `config/event-check-rules.yaml`, `flows/ai.photogenerator.aivideo.aivideogenerator.aiart.yaml` |
| 05/10/2026 | `1158215` | Thêm quy tắc | feat(check): xem ads theo so tren nut, gop luot chay le vao luot truoc | `.claude/commands/check-event.md`, `.claude/commands/record-flow.md`, `flows/ai.photogenerator.aivideo.aivideogenerator.aiart.yaml` |
| 22/09/2026 | `2808c5c` | Sửa sau lỗi | fix(flow): app nexus ai chay duoc ca bon vi tri rating | `flows/ai.photogenerator.aivideo.aivideogenerator.aiart.yaml` |
| 21/09/2026 | `05d39df` | Thêm quy tắc | feat(flow): app sorapix them hai case SDK daily checkin | `flows/com.ai.aiimage.aivideogenerator.yaml` |
| 21/09/2026 | `0498575` | Thêm quy tắc | feat(spec): goi spec bang ten chuc nang thay vi dan link | `.claude/commands/check-event.md`, `.claude/commands/spec-cases.md`, `specs.json` |
| 21/09/2026 | `3971f52` | Thêm quy tắc | feat(flow): duong lai app sorapix, hai event SDK widget | `flows/com.ai.aiimage.aivideogenerator.yaml` |
| 21/09/2026 | `cf4e3e6` | Khác | docs(flow): chi viet case cho vi tri app that su co | `flows/README.md` |
| 21/09/2026 | `e4946d7` | Thêm quy tắc | feat(flow): duong lai app linguza, ba placement rating (app khong co result) | `flows/com.nxl.aienglishtutor.ailearnlanguage.aichatbot.yaml` |
| 19/09/2026 | `0ad36d6` | Sửa sau lỗi | fix(commands): duong dan venv doc theo he dieu hanh, khong hardcode .venv/bin | `.claude/CLAUDE.md`, `.claude/commands/check-event.md`, `.claude/commands/record-flow.md`, `.claude/workflows/spec-to-cases.js` |
| 19/09/2026 | `23ef7b3` | Thêm quy tắc | feat(flow): duong lai app lynix aibeauty, sau case bon placement rating | `flows/com.aiphotoeditor.aiphotogenerator.aivideogenerator.aibeauty.yaml` |
| 19/09/2026 | `d525832` | Thêm quy tắc | feat(flow): duong lai app nexus ai, du bon placement rating | `flows/ai.photogenerator.aivideo.aivideogenerator.aiart.yaml` |
| 19/09/2026 | `3355a0d` | Thêm quy tắc | feat(flow): app aisong do duoc ca bon placement rating | `flows/aisong.generator.creatsong.music.yaml` |
| 19/09/2026 | `5565869` | Thêm quy tắc | feat(flow): duong lai app aisong, du bon placement | `flows/aisong.generator.creatsong.music.yaml` |
| 19/09/2026 | `065097f` | Thêm quy tắc | feat(command): /check-event chay toi khi do duoc that roi moi publish | `.claude/commands/check-event.md` |
| 18/09/2026 | `6f41f80` | Sửa sau lỗi | fix(flow): close_popup kiem lai sau khi bam, va don quang cao trong luc cho | `flows/com.aiprofile.aiheadshot.aiimagegenerator.aiphotogenerator.yaml` |
| 18/09/2026 | `e09ec90` | Thêm quy tắc | feat(flow): duong lai app aiphotogenerator cho SDK Rating | `flows/com.aiprofile.aiheadshot.aiimagegenerator.aiphotogenerator.yaml` |
| 18/09/2026 | `0c4d431` | Thêm quy tắc | feat(command): /spec-cases sinh khung case tu trang spec | `.claude/CLAUDE.md`, `.claude/commands/spec-cases.md` |
| 18/09/2026 | `58136f0` | Thêm quy tắc | feat(command): /record-flow do duong lai app roi chot thanh case | `.claude/CLAUDE.md`, `.claude/commands/record-flow.md` |
| 18/09/2026 | `0f15427` | Thêm quy tắc | feat(command): /check-event chay ca luot va publish artifact | `.claude/CLAUDE.md`, `.claude/commands/check-event.md` |
| 18/09/2026 | `8027811` | Khác | note: cap nhat trang thai repo va luot cham that dau tien | `.claude/CLAUDE.md` |
| 18/09/2026 | `8f98acc` | Sửa sau lỗi | fix(flow): di het onboarding cua app texttoimage truoc khi cho popup widget | `flows/com.nxl.aiphotocreator.aivideogenerator.texttoimage.yaml` |
| 18/09/2026 | `82920a9` | Thêm quy tắc | feat(workflow): hai buoc sinh khung case, va ghi chu trang thai repo | `.claude/CLAUDE.md`, `.claude/workflows/spec-to-cases.js` |
| 18/09/2026 | `213e156` | Thêm quy tắc | feat(flow): buoc close_ad tu tim nut dong quang cao va buoc allow cho dialog quyen | `flows/com.nxl.aiphotocreator.aivideogenerator.texttoimage.yaml` |
| 17/09/2026 | `247f75f` | Sửa sau lỗi | fix(report): so tren dau noi ro con bao nhieu muc chua test | `flows/com.nxl.aiphotocreator.aivideogenerator.texttoimage.yaml` |
| 17/09/2026 | `74f52a8` | Sửa sau lỗi | fix: moc logcat boc nhay o phia may, va step tuy chon cho man quang cao | `flows/com.nxl.aiphotocreator.aivideogenerator.texttoimage.yaml`, `flows/com.nxl.aiphotocreator.aivideogenerator.texttoimage.yaml.bak` |
| 17/09/2026 | `b53f473` | Khác | docs: SKILL.md va README noi dung hai lenh CLI, kem test giu tai lieu khong noi sai | `SKILL.md` |
| 17/09/2026 | `64f68c3` | Thêm quy tắc | feat(flow): doc flow YAML thanh Flow, sai dong nao noi dong do | `flows/README.md`, `flows/example.yaml` |
| 17/09/2026 | `db1c85f` | Khác | merge: hop nhat nhanh triage tu origin voi ban chay Windows |  |
| 11/09/2026 | `94d6916` | Sửa sau lỗi | fix: tach ro so event APP voi so event CA PHIEN | `.claude/workflows/triage-event-fail.js` |
| 11/09/2026 | `13ce600` | Thêm quy tắc | feat: workflow soi nguyen nhan loi bang agent, va tai lieu | `.claude/workflows/triage-event-fail.js` |
| 11/09/2026 | `f3350ef` | Thêm quy tắc | feat: chay duoc tren Windows, va tu publish artifact sau moi luot cham | `SKILL.md` |
| 08/09/2026 | `468aa14` | Thêm quy tắc | feat: base plumbing for adb, verdicts, xlsx and UI dump parsing | `config/event-check-rules.yaml` |

Sinh lại bảng: `git log --name-only -- flows config specs.json .claude SKILL.md`
