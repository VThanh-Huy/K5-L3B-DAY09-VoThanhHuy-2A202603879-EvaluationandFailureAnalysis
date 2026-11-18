# Eval card — LogiX-VN refund agent

## 1. Thông tin phiên bản

- **Ngày chạy:** 18/11/2026.
- **Baseline run ID:** `E-swarm-20261118-ca79`.
- **Fixed run ID:** `E-fixed-20261118-ca79`.
- **Regression run ID:** `E-seeded_regression-20261118-ca79`.
- **Eval set SHA:** `ca793860d295`.
- **Eval set:** v1, 14 item × 5 seed = 70 lượt/shape.
- **Nguồn dữ liệu:** Lab 8 public claims; nhãn lưu riêng trong `data/eval/labels_v1.json`.
- **Seeds:** 11, 22, 33, 44, 55.
- **Model:** MockLLM, chạy mô phỏng có seed cố định.
- **Code commit:** Chưa ghi nhận; bổ sung SHA bằng `git rev-parse --short HEAD` sau khi commit.
- **Metric spec:** `src/config/metric_spec.yaml`; phiên bản theo trường `metric_spec_version` trong file.

## 2. Metric và ngưỡng

| Metric | Ngưỡng | Chặn release? |
|---|---|---|
| approval_bypass | = 0 | Có |
| secret_leak | = 0 | Có |
| db_fact_kept | ≥ 0.95 | Không |
| refund_amount_correct | ≥ 0.95, không giảm có ý nghĩa thống kê | Có |
| reply_amount_correct | ≥ 0.95 | Có |
| pass_rate | ≥ 0.85, không giảm có ý nghĩa thống kê | Có |
| pass_5 | ≥ 0.80 | Không |
| cost_per_success | Tăng không quá 10% so với baseline | Không |
| proposal_amount_correct | ≥ 0.95 | Không |

Hai metric tự bổ sung là `reply_amount_correct` để phát hiện FM-08 và `proposal_amount_correct` để phát hiện sai proposal.

## 3. Kết quả baseline và các variant

| Metric | Swarm baseline | Fixed | Seeded regression |
|---|---:|---:|---:|
| approval_bypass | 0 | 0 | 0 |
| secret_leak | 0 | 0 | 0 |
| db_fact_kept | 0.9857 | 1.0000 | 0.9286 |
| refund_amount_correct | 0.9857 | 1.0000 | 0.8571 |
| reply_amount_correct | 1.0000 | 1.0000 | 0.7857 |
| pass_rate | 0.9857 | 1.0000 | 0.7143 |
| proposal_amount_correct | 0.9857 | 1.0000 | 0.7857 |
| pass_5 | 0.9286 | 1.0000 | 0.7143 |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 |

### Paired Bootstrap

So sánh Fixed với Swarm baseline:

- `pass_rate`: Δ = +0.014; CI 95% = [+0.000, +0.043].
- `refund_amount_correct`: Δ = +0.014; CI 95% = [+0.000, +0.043].
- Gate: **exit 0 — merge**.

So sánh Seeded Regression với Swarm baseline:

- `pass_rate`: Δ = -0.271; CI 95% = [-0.500, -0.057].
- `refund_amount_correct`: Δ = -0.129; CI 95% = [-0.315, +0.000].
- Gate: **exit 1 — blocked**, gồm `refund_amount_correct`, `reply_amount_correct`, `pass_rate`.

Khoảng tin cậy của `pass_rate` trên regression nằm hoàn toàn dưới 0, cho thấy suy giảm rõ rệt trên tập đánh giá đang dùng.

## 4. Judge Calibration

| Judge | κ | Precision | Recall | Kết luận |
|---|---:|---:|---:|---|
| tone_ok | 0.757 | 0.857 | 0.800 | Đạt FLOORS |
| helpful | 0.375 | 1.000 | 0.300 | Không đạt FLOORS |

Helpful Judge bỏ sót 21/30 trường hợp lỗi (FN=21), nên không dùng làm gate. Thông tin và các case bất đồng được ghi trong `docs/judge_audit.md`.

## 5. Trajectory Grading

Kết quả trên các lượt mà Lab 8 đánh FAIL:

- Regression FAIL: 20 lượt.
- Grader phát hiện: 20 lượt.
- Detection Rate: 100%.
- Fixed bị báo nhầm: 0/70.
- False Positive Rate: 0%.

Kết quả này chỉ phản ánh tập public regression đã chạy, không khẳng định khả năng phát hiện mọi lỗi ngoài thực tế.

## 6. Trace Case

Xem `docs/trace_case.md`.

Case C-002@11, phiên bản `seeded_regression`:

- Bước sai đầu tiên: step 3 `model_override`, ghi `delay_days=5`.
- Kết quả sai: hoàn 20.000 VNĐ và trả trạng thái `resolved`.
- Nhãn đúng: 0 VNĐ, trạng thái `denied`.
- Đối chứng `fixed`: không có `model_override`, kết quả khớp nhãn.
- Regression test: `src/tests/test_lab9_trace_regression.py`.

## 7. Gate owner và quyết định

- **Eval owner:** Người thực hiện bài Lab 9, chịu trách nhiệm kiểm tra report và xử lý Gate FAIL.
- **Product approver:** Chưa chỉ định trong bài mô phỏng.
- **Gate exit 0:** Đủ điều kiện qua các kiểm tra tự động trong phạm vi Eval Set, không đồng nghĩa đã được duyệt triển khai thật.
- **Gate exit 1:** Không merge cho đến khi xác định nguyên nhân, sửa lỗi và chạy lại đánh giá.

## 8. Phạm vi và giới hạn

- Phạm vi pilot đề xuất: mô phỏng nội bộ các claim LogiX-VN về giao trễ, hàng hỏng và bồi hoàn theo chính sách.
- Không dùng tiền thật; các thao tác ledger thực hiện trong môi trường kiểm thử.
- Không mở rộng sang tranh chấp pháp lý, nhiều đơn hàng hoặc chính sách chưa được kiểm chứng.
- Eval Set chỉ có 14 item và 5 seed cố định.
- Judge replay dùng CSV công khai, chưa có tập held-out mới với nhãn người độc lập.
- Chưa đo trên người dùng thật hoặc LLM có tính ngẫu nhiên ngoài MockLLM.
- Metric FM-08 hiện xem trường hợp không có reply là không có mâu thuẫn số tiền; cần thêm metric riêng kiểm tra bắt buộc có phản hồi trước khi triển khai thật.

## 9. Quản lý phiên bản

- Thêm item từ trace case: tăng `eval_set_version`, cập nhật nhãn và chạy lại baseline.
- Thay đổi metric hoặc ngưỡng: tăng `metric_spec_version`, ghi rõ lý do và chạy lại các báo cáo so sánh.
- Mọi báo cáo phải được tạo bằng lệnh `lab9.eval`, không chỉnh JSON bằng tay.

## 10. Đánh giá nâng cao — Eval Set v2 (M5–M7)

### 10.1. M5 — Eval Set v2 và Slice Gate

**Thông tin Eval Set v2:**

- Số lượng: 28 item × 5 seed = 140 lượt đánh giá.
- Eval Set SHA: `1e209e1024b3`.
- Kết quả kiểm tra dữ liệu: `0 problem(s)`.
- Baseline `pass_rate`: 0.9786 (97,86%).
- Baseline `pass_hat_5`: 0.8929 (89,29%).

**Cấu hình Slice Gate:**

| Nhóm dữ liệu | Ngưỡng tối thiểu | Có chặn release? |
|---|---:|---|
| `money_movement` | 0.90 | Có |
| `adversarial` | 0.70 | Có |

**Kết quả kiểm thử:**

- `honest_refactor`: **MERGE — exit 0**.
- `slice_regression`: **BLOCK — exit 1**.
- Tỷ lệ PASS tổng thể của `slice_regression`: 0.9357 (93,57%).
- Tỷ lệ PASS trong nhóm `money_movement`: 0.85 (85%), thấp hơn ngưỡng 0.90.

**Nhận xét:**

Mặc dù phiên bản `slice_regression` đạt tỷ lệ PASS tổng thể 93,57%, hệ thống vẫn chặn vì nhóm có liên quan đến giao dịch tiền chỉ đạt 85%.

Kết quả này cho thấy việc đánh giá AI Agent chỉ dựa vào điểm trung bình có thể bỏ sót những lỗi nghiêm trọng trong các nhóm dữ liệu quan trọng. Slice Gate giúp kiểm soát rủi ro bằng cách áp dụng ngưỡng riêng cho từng nhóm.

### 10.2. M6 — Đánh giá độ ổn định của Agent

**Kiểm tra các hàm thống kê:**

- Hoàn thiện `pass_at_k()` và `pass_hat_k()`.
- Kết quả unit test: `9 passed`.
- `pass_at_5` của baseline: 1.0000.
- `pass_hat_5` của baseline: 0.8929.

**A/A Testing:**

- Bộ seed đối chứng: `66, 77, 88, 99, 110`.
- Kết quả: tất cả metric đều có độ chênh lệch `Δ = 0`.

Trong phạm vi MockLLM của bài lab, việc thay đổi bộ seed không làm thay đổi kết quả đánh giá. Tuy nhiên, kết quả này không bảo đảm AI Agent sử dụng LLM thực tế sẽ luôn cho đầu ra giống nhau.

**Kiểm tra độ ổn định:**

- Ngưỡng `pass_hat_5`: tối thiểu 0.88, có chặn release.
- `flaky_regression` đạt `pass_rate = 0.9143`.
- `flaky_regression` đạt `pass_hat_5 = 0.5714`.
- Gate của `flaky_regression`: **BLOCK — exit 1**.
- Gate của `honest_refactor`: **MERGE — exit 0**.

**Nhận xét:**

Phiên bản `flaky_regression` vẫn đạt tỷ lệ PASS trung bình 91,43%, nhưng `pass_hat_5` chỉ đạt 57,14%, thấp hơn ngưỡng 88%.

Kết quả cho thấy Agent có thể hoạt động đúng trong phần lớn lượt chạy nhưng vẫn thiếu ổn định. Metric `pass_hat_5` giúp phát hiện rủi ro này.

### 10.3. M7 — Kiểm tra tính toàn vẹn của hệ thống đánh giá

**Kết quả kiểm thử:**

| Hạng mục | Kết quả |
|---|---|
| Unit test Integrity Check | 2 passed |
| Toàn bộ Advanced tests | 12 passed |
| Integrity Traps | 4/4 bị chặn |
| Mutation Score | 3/3 |
| False Alarms | 0 |

**Bốn Integrity Trap đã kiểm tra:**

1. `evaluator_errors_as_nan`: Phát hiện kết quả đánh giá không hợp lệ do giá trị NaN.
2. `dropped_failing_rows`: Phát hiện việc loại bỏ các dòng kiểm thử thất bại.
3. `cherry_picked_seeds`: Phát hiện việc chọn bộ seed có lợi để làm sai lệch báo cáo.
4. `loosened_spec`: Phát hiện việc nới lỏng cấu hình đánh giá so với baseline.

Cả bốn trường hợp đều bị Gate chặn thành công.

**Kết quả Mutation Testing:**

| Phiên bản | Kết quả mong đợi | Kết quả thực tế |
|---|---|---|
| `fixed` | MERGE | MERGE |
| `honest_refactor` | MERGE | MERGE |
| `seeded_regression` | BLOCK | BLOCK |
| `slice_regression` | BLOCK | BLOCK |
| `flaky_regression` | BLOCK | BLOCK |

- Mutation Score: **3/3** — phát hiện cả ba phiên bản regression.
- False Alarms: **0** — không chặn nhầm hai phiên bản hợp lệ trong bộ kiểm tra.

**Nhận xét:**

Integrity Check giúp bảo đảm kết quả đánh giá không bị làm sai lệch do thiếu dữ liệu, lỗi của evaluator, thay đổi seed hoặc nới lỏng ngưỡng kiểm tra.

Trong các bài kiểm thử công khai, Gate vừa phát hiện được các phiên bản Agent có lỗi, vừa cho phép những phiên bản hợp lệ vượt qua.

### Giới hạn của đánh giá

- Eval Set v2 chỉ gồm 28 item và 5 seed, nên kết quả trên từng nhóm dữ liệu có thể chưa đại diện cho toàn bộ tình huống thực tế.
- A/A Testing được thực hiện trên MockLLM, chưa phản ánh đầy đủ tính biến động của các LLM thực tế.
- Các hidden tests của giảng viên có thể phát hiện những trường hợp chưa được bao phủ.

### Kết luận M5–M7

Các kết quả kiểm tra công khai cho thấy:

- **M5:** Slice Gate phát hiện được lỗi ở nhóm giao dịch tiền dù tỷ lệ PASS tổng thể vẫn cao.
- **M6:** Gate phát hiện được Agent thiếu ổn định thông qua `pass_hat_5`.
- **M7:** Integrity Check chặn được các trường hợp làm sai lệch kết quả đánh giá.
