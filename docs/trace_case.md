# Trace case: từ trace tới quyết định sai đầu tiên

## Case được chọn

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
```
| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261118-ca79` |
| Triệu chứng | Lab 8 grader FAIL (`status resolved != denied`). Agent hoàn 20.000 VNĐ, trong khi ledger kỳ vọng 0 VNĐ; status đúng là `denied`. |
| Bước sai đầu tiên | Step 3 — `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước đầu tiên | Step 1 `handoff` giao nhiệm vụ kiểm tra policy. Step 2 `investigator` tra cứu đơn O-202. Dữ liệu đơn hàng cho thấy trễ 2 ngày. Step 3 ghi đè thành 5 ngày, khiến quyết định tiếp theo dùng dữ kiện sai. |
| Failure mode | FM-03 — `ticket_trust`: tin dữ liệu ticket thay vì DB có thẩm quyền. |
| Đối chứng | `fixed C-002@11`, cùng seed 11, không có `model_override`. Step 3 `quote` trả `amount_vnd=0`, `reason=no_entitlement`; reply từ chối hoàn tiền. Ledger=0, status=`denied`, Lab 8 grader PASS. |
| Regression test | `src/tests/test_lab9_trace_regression.py::test_c002_ticket_trust_regression`. Kiểm tra sự kiện `model_override`, nhãn, trạng thái và ledger giữa hai variant. Cần chạy pytest để xác nhận test mới. |
| Chưa chắc chắn | Trace chứng minh dữ kiện bị ghi đè và kết quả hoàn tiền sai; chưa chứng minh mức độ phổ biến của lỗi trên dữ liệu ngoài Eval Set. |

## Bằng chứng ledger

| Trường | Seeded regression | Fixed | Label |
|---|---:|---:|---:|
| refund_vnd | 20.000 | 0 | 0 |
| refund_count | 1 | 0 | 0 |
| status | resolved | denied | denied |
| Lab 8 grader | FAIL | PASS | — |

## Kết luận

Bước sai đầu tiên là step 3 `model_override`, không phải step 6 `reply`. Reply và khoản hoàn tiền sai là hậu quả của việc dùng số ngày trễ không đúng với dữ liệu đơn hàng.

Phòng tránh: Agent không được ghi đè dữ kiện đã xác minh bằng thông tin từ ticket. Cần Code Grader kiểm tra `model_override` và quyết định nghiệp vụ dựa trên DB.