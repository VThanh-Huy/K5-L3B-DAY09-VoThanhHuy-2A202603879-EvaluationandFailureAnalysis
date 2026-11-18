
from lab9.trace_case import investigate


def test_c002_ticket_trust_regression():
    broken = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)

    bad_trial = broken["trial"]
    good_trial = fixed["trial"]
    label = broken["label"]

    # Variant lỗi phải cho thấy hành vi ghi đè dữ kiện.
    assert bad_trial["events"][2]["kind"] == "model_override"
    assert bad_trial["events"][2]["payload"]["delay_days"] == 5

    # Xác nhận lỗi trên variant regression.
    assert bad_trial["lab8_pass"] is False
    assert bad_trial["snapshot"]["refund_vnd"] != label["refund_vnd"]
    assert bad_trial["result"]["status"] != label["status"]

    # Bản fixed phải loại bỏ lỗi và khớp nhãn chuẩn.
    assert not any(
        event.get("kind") == "model_override"
        for event in good_trial["events"]
    )
    assert good_trial["lab8_pass"] is True
    assert good_trial["snapshot"]["refund_vnd"] == label["refund_vnd"]
    assert good_trial["result"]["status"] == label["status"]
