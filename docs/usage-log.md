# Log sử dụng — check-event

Mỗi lượt chạy thật thêm một dòng. "Test tay (TB)" là thời gian tester ước tính nếu làm cùng việc bằng tay, lấy trung bình; spec dài hay ngắn thì lệch lên xuống. "Tiết kiệm" = Test tay − Thời gian tool. Thời gian tool là thời gian máy chạy; trong lúc đó tester làm việc khác được, nên con số tiết kiệm là mức thấp nhất.

Test tay (TB): **60 phút** cho một lần kiểm event của một tính năng trên một app (tester ước tính 22/10/2026).
Thời gian tool: đo từ log phiên `out/report-*.log` và giờ ghi report.

| Ngày | App | Version | Số lượt | Kết quả lượt cuối | Bug app xác nhận | Report | Thời gian tool | Test tay (TB) | Tiết kiệm |
|---|---|---|---|---|---|---|---|---|---|
| 17/09–18/09/2026 | com.nxl.aiphotocreator…texttoimage | 2.1.0 (14) | 14 | 2/2 khớp (spec SDK Widget) | 0 | [artifact](https://claude.ai/artifact/2mkNh33qpZrNk9tVgKHjia) | ~80 phút (lượt thật đầu tiên, vừa chạy vừa sửa tool) | 60 phút | −20 phút |
| 20/09/2026 | com.nxl.aiphotocreator…texttoimage | 2.2.0 (15) | 3 | 5/5 khớp | 0 | `out/report-…-260920-195832.html` | ~25 phút | 60 phút | 35 phút |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | 2.8.0 (21) | 4 | 2/2 khớp | 0 | [artifact](https://claude.ai/artifact/M3ZJ418Gruw9VucoBUfWGQ) | 11 phút (11:41–11:53, mỗi lượt ~2 phút) | 60 phút | 49 phút |

**Tổng:** 3 lần kiểm, test tay 180 phút, tool ~116 phút, tiết kiệm **~64 phút**. Bỏ lần đầu (lúc còn
đang dựng tool) thì 120 phút tay so với ~36 phút tool, tiết kiệm **84 phút**. Tool đã ổn định thì mỗi
lượt chỉ còn ~2 phút, nên lợi ích tăng theo số lần chạy lại (regression mỗi bản build).

Flow lái đã có nhưng chưa còn report trên máy này: aiart, aisong, aiprofile, aibeauty,
englishtutor, aiimage (sorapix), casttotv.
