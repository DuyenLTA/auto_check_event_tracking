# Log sử dụng — check-event

Mỗi lượt chạy thật thêm một dòng. "Test tay (TB)" là thời gian tester ước tính nếu làm cùng việc bằng tay, lấy trung bình; spec dài hay ngắn thì lệch lên xuống. "Tiết kiệm" = Test tay − Thời gian tool. Thời gian tool là thời gian máy chạy; trong lúc đó tester làm việc khác được, nên con số tiết kiệm là mức thấp nhất.

Test tay (TB): **60 phút** cho một lần kiểm event của một tính năng trên một app (tester ước tính 22/10/2026).
Thời gian tool: chỉ tính lượt chạy ra kết quả, không tính thời gian sửa tool hay sửa flow giữa các lượt.
hairai đo từ log phiên `out/report-*.log` (lượt cuối 11:50:52–11:52:43). texttoimage không có log phiên,
ước tính ~2 phút theo khoảng cách ngắn nhất giữa hai report liên tiếp (1–2 phút).

| Ngày | App | Version | Số lượt | Kết quả lượt cuối | Bug app xác nhận | Report | Thời gian tool | Test tay (TB) | Tiết kiệm |
|---|---|---|---|---|---|---|---|---|---|
| 17/09–18/09/2026 | com.nxl.aiphotocreator…texttoimage | 2.1.0 (14) | 14 | 2/2 khớp (spec SDK Widget) | 0 | [artifact](https://claude.ai/artifact/2mkNh33qpZrNk9tVgKHjia) | ~2 phút (ước tính) | 60 phút | 58 phút |
| 20/09/2026 | com.nxl.aiphotocreator…texttoimage | 2.2.0 (15) | 3 | 5/5 khớp | 0 | `out/report-…-260920-195832.html` | ~2 phút (ước tính) | 60 phút | 58 phút |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | 2.8.0 (21) | 4 | 2/2 khớp | 0 | [artifact](https://claude.ai/artifact/M3ZJ418Gruw9VucoBUfWGQ) | 2 phút (đo: 1 phút 51 giây) | 60 phút | 58 phút |

**Tổng:** 3 lần kiểm, test tay 180 phút, tool ~6 phút, tiết kiệm **~174 phút (~2,9 giờ)**.
Không tính thời gian sửa tool và flow giữa các lượt (lần đầu 17–18/09 mất 14 lượt, 4 bản sửa).

Flow lái đã có nhưng chưa còn report trên máy này: aiart, aisong, aiprofile, aibeauty,
englishtutor, aiimage (sorapix), casttotv.
