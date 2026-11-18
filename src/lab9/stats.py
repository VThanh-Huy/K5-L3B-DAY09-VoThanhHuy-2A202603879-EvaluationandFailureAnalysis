"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""
from __future__ import annotations

from math import comb
import numpy as np
from typing import Sequence
from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
            raise ValueError("Human và judge phải cùng số mẫu")

    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    for h, j in zip(human, judge):
        h = h.strip().upper()
        j = j.strip().upper()

        if h not in ("PASS", "FAIL") or j not in ("PASS", "FAIL"):
            raise ValueError("Nhãn phải là PASS hoặc FAIL")

        if h == "FAIL" and j == "FAIL":
            cm["tp"] += 1
        elif h == "PASS" and j == "FAIL":
            cm["fp"] += 1
        elif h == "FAIL" and j == "PASS":
            cm["fn"] += 1
        else:
            cm["tn"] += 1

    return cm


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)

    tp = cm["tp"]
    fp = cm["fp"]
    fn = cm["fn"]

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    tp, fp = cm["tp"], cm["fp"]
    fn, tn = cm["fn"], cm["tn"]

    n = tp + fp + fn + tn
    if n == 0:
        raise ValueError("Không có dữ liệu")

    # Tỷ lệ hai bên thực sự đồng ý
    p_o = (tp + tn) / n

    # Tỷ lệ đồng ý kỳ vọng do ngẫu nhiên
    p_h = (tp + fn) / n
    p_j = (tp + fp) / n
    p_e = p_h * p_j + (1 - p_h) * (1 - p_j)

    if abs(1 - p_e) < 1e-12:
        raise ValueError("Kappa không xác định")

    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denominator = sensitivity + specificity - 1

    if abs(denominator) < 1e-12:
        raise ValueError("Không thể hiệu chỉnh tỷ lệ")

    corrected = (
        observed_rate + specificity - 1
    ) / denominator

    return max(0.0, min(1.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    from scipy.stats import bootstrap

    if len(a) != len(b) or len(a) == 0:
        raise ValueError("Hai danh sách phải cùng độ dài và không rỗng")

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    differences = a - b
    delta = float(np.mean(differences))

    # Hai phiên bản hoàn toàn giống nhau
    if np.all(differences == 0):
        return 0.0, 0.0, 0.0

    result = bootstrap(
        (a, b),
        statistic=lambda x, y: float(np.mean(x - y)),
        paired=True,
        vectorized=False,
        method="percentile",
        n_resamples=n_resamples,
        confidence_level=confidence,
        rng=np.random.default_rng(rng),
    )

    return (
        delta,
        float(result.confidence_interval.low),
        float(result.confidence_interval.high),
    )



def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    if n <= 0 or c < 0 or c > n or k < 1 or k > n:
        raise ValueError("Invalid n, c, k")

    if n - c < k:
        return 1.0

    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    if n <= 0 or c < 0 or c > n or k < 1 or k > n:
        raise ValueError("Invalid n, c, k")

    if c < k:
        return 0.0

    return comb(c, k) / comb(n, k)
