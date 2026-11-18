# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | PASS — đạt cả 3 ngưỡng | Dùng |
| helpful | 100 | 0.375 | 1.000 | 0.300 | FAIL — không đạt κ và Recall | Loại |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | Câu trả lời sử dụng cách xưng hô "em", "nha" quá suồng sã trong giao tiếp CSKH. Judge đánh giá nhầm sự thân thiện thành phù hợp. Cần bổ sung quy tắc về cách xưng hô chuyên nghiệp. |
| 2 | H-017 | PASS | FAIL | Người | Cách xưng hô "bạn ơi", "nha" không phù hợp với ngữ cảnh khách hàng lớn tuổi. Judge chưa xét đầy đủ đối tượng giao tiếp. Cần đánh giá giọng điệu theo ngữ cảnh. |
| 3 | H-029 | PASS | FAIL | Người | Câu "không cần nhắn thêm" mang tính ra lệnh, thiếu sự tôn trọng khách hàng. Judge chỉ chú ý các từ lịch sự như "Dạ", "vui lòng". Cần đánh giá toàn bộ nội dung phản hồi. |
| 4 | H-042 | FAIL | PASS | Người | Phản hồi ngắn nhưng lịch sự, cung cấp đủ số tiền và thời gian nhận tiền. Judge phạt vì thiếu lời xin lỗi. Rubric không nên bắt buộc xin lỗi trong mọi trường hợp. |
| 5 | H-051 | FAIL | PASS | Người | Judge đánh FAIL vì sử dụng từ tiếng Anh "refund", nhưng thuật ngữ này được CS LogiX cho phép. Cần bổ sung danh sách thuật ngữ được chấp nhận. |
| 6 | HL-015 | PASS | FAIL | Người | Agent thông báo hoàn 55.000đ nhưng ledger chỉ ghi 40.000đ. Judge bỏ sót lỗi số tiền. Cần dùng code để so sánh số tiền trong reply với ledger. |
| 7 | HL-016 | PASS | FAIL | Người | Agent thông báo hoàn 55.000đ nhưng ledger ghi 35.000đ. Judge có thể bị ảnh hưởng bởi lời xin lỗi dài và lịch sự. Cần ưu tiên kiểm tra tính chính xác nghiệp vụ. |
| 8 | HL-020 | PASS | FAIL | Người | Agent thông báo hoàn 90.000đ nhưng ledger ghi 120.000đ. Nội dung không đúng dù câu trả lời lịch sự. Cần kiểm tra số tiền dựa trên dữ liệu có thẩm quyền. |
| 9 | HL-028 | PASS | FAIL | Người | Agent thông báo hoàn 50.000đ nhưng ledger ghi 35.000đ. Lời xin lỗi dài không thể bù đắp cho lỗi nghiệp vụ. Cần tách tiêu chí tone và độ chính xác. |
| 10 | HL-035 | PASS | FAIL | Người | Agent thông báo hoàn 50.000đ nhưng ledger ghi 35.000đ. Judge bỏ sót lỗi do quá chú trọng cách diễn đạt tích cực. Cần kết hợp code grader và AI Judge. |

## Kết luận
- **Tone Judge được sử dụng:** Đạt cả ba ngưỡng với κ = 0.757, Precision = 0.857 và Recall = 0.800. Ma trận nhầm lẫn: TP = 24, FP = 4, FN = 6, TN = 66. Tuy nhiên, Judge vẫn có thể nhầm giữa giọng điệu thân thiện và thiếu chuyên nghiệp, hoặc đánh giá quá nghiêm những phản hồi ngắn.

- **Helpful Judge bị loại:** Không đạt ngưỡng κ và Recall. Ma trận nhầm lẫn: TP = 9, FP = 0, FN = 21, TN = 70. Dù Precision = 1.000, Judge chỉ phát hiện 9/30 trường hợp lỗi thật và bỏ sót 21 trường hợp, tương ứng Recall = 0.300. Vì vậy không được dùng Helpful Judge làm điều kiện chặn (gate) khi đánh giá Agent.

- **Nguyên nhân:** Helpful Judge thường đánh PASS những phản hồi có giọng điệu lịch sự nhưng thông báo sai số tiền hoàn. Điều này cho thấy Judge chưa kiểm tra đầy đủ độ chính xác nghiệp vụ.

- **Đề xuất cải thiện:** Với Tone Judge, bổ sung hướng dẫn về xưng hô, ngữ cảnh khách hàng và thuật ngữ được phép sử dụng. Với Helpful Judge, cần tách việc đánh giá cách diễn đạt khỏi kiểm tra nội dung; các thông tin về số tiền và approval phải được kiểm chứng bằng code grader và dữ liệu có thẩm quyền.

- **Rủi ro còn lại:** Judge mới được kiểm tra trên dữ liệu replay đã công khai. Kết quả có thể chưa phản ánh chính xác hiệu năng trên dữ liệu mới. Cần thu thập nhãn người độc lập trên một tập held-out thật, sau đó chạy lại calibration trước khi sử dụng Judge trong môi trường thực tế.
