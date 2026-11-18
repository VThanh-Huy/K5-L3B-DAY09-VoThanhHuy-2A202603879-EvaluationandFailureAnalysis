"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import math

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    from lab9.graders import GRADERS

    problems = []

    # 1. Metric values must be finite.
    for name, value in pr.get("metrics", {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                problems.append(f"non-finite metric: {name}")

    # 2. Evaluator crashes must never be ignored.
    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures is not empty")

    # 3. Check row counts, duplicate pairs and manifest.
    for label, report in (("PR", pr), ("baseline", base)):
        manifest = report["manifest"]
        rows = report["rows"]
        seeds = manifest["seeds"]
        expected = manifest["items"] * len(seeds)

        if len(rows) != expected:
            problems.append(
                f"{label} row count: {len(rows)} != {expected}"
            )

        pairs = [(r["item_id"], r["seed"]) for r in rows]
        if len(pairs) != len(set(pairs)):
            problems.append(f"{label} has duplicate item/seed pairs")

        if len(set(seeds)) != len(seeds):
            problems.append(f"{label} has duplicate manifest seeds")

        item_ids = {r["item_id"] for r in rows}
        if len(item_ids) != manifest["items"]:
            problems.append(f"{label} item count mismatch")

        expected_pairs = {
            (item_id, seed)
            for item_id in item_ids
            for seed in seeds
        }
        if set(pairs) != expected_pairs:
            problems.append(f"{label} incomplete item/seed grid")

    # 4. No cherry-picked items or seeds.
    if pr["manifest"]["items"] != base["manifest"]["items"]:
        problems.append("manifest item count differs")

    if set(pr["manifest"]["seeds"]) != set(base["manifest"]["seeds"]):
        problems.append("manifest seed set differs")

    base_rows = {
        (r["item_id"], r["seed"]): r for r in base["rows"]
    }
    pr_rows = {
        (r["item_id"], r["seed"]): r for r in pr["rows"]
    }

    if set(pr_rows) != set(base_rows):
        problems.append("PR item/seed pairs differ from baseline")

    # 5. Slice tags must not be altered.
    for pair in set(pr_rows) & set(base_rows):
        pr_tags = set(pr_rows[pair].get("slices") or [])
        base_tags = set(base_rows[pair].get("slices") or [])
        if pr_tags != base_tags:
            problems.append(f"slice tags changed for {pair}")
            break

    # 6. Every graded result must have a value.
    graded_ids = {
        m["id"] for m in spec.get("metrics", [])
        if m["id"] in GRADERS
    }

    for index, row in enumerate(pr["rows"]):
        for metric in graded_ids:
            if row.get(metric) is None:
                problems.append(
                    f"missing grader result: row {index}, {metric}"
                )
                break

    # 7. Ratchet: thresholds cannot become weaker.
    if (
        base_spec is not None
        and spec.get("eval_set_version") == base_spec.get("eval_set_version")
    ):
        def compare_rules(old_rules, new_rules, key_field, category):
            old_map = {
                (r["name"], r.get("metric")) if key_field == "name"
                else r["id"]: r
                for r in old_rules
            }
            new_map = {
                (r["name"], r.get("metric")) if key_field == "name"
                else r["id"]: r
                for r in new_rules
            }
            for key, old in old_map.items():
                if key not in new_map:
                    problems.append(f"{category} removed: {key}")
                    continue

                new = new_map[key]

                if old.get("blocking", False) and not new.get("blocking", False):
                    problems.append(f"{category} blocking disabled: {key}")

                old_th = old.get("threshold", old)
                new_th = new.get("threshold", new)

                for field in ("min", "max", "max_increase"):
                    if field not in old_th:
                        continue

                    if field not in new_th:
                        problems.append(f"{category} threshold removed: {key}/{field}")
                    elif field == "min" and new_th[field] < old_th[field]:
                        problems.append(f"{category} min loosened: {key}")
                    elif field != "min" and new_th[field] > old_th[field]:
                        problems.append(f"{category} max loosened: {key}")

                if old_th.get("no_significant_drop") and not new_th.get(
                    "no_significant_drop"
                ):
                    problems.append(
                        f"{category} no_significant_drop removed: {key}"
                    )

        compare_rules(
            base_spec.get("metrics", []),
            spec.get("metrics", []),
            "id",
            "metric",
        )
        compare_rules(
            base_spec.get("slices", []),
            spec.get("slices", []),
            "name",
            "slice",
        )

    return problems

def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5: kiem tra chat luong cua tung slice."""
    blocked = []
    lines = []
    bs = spec.get("bootstrap", {})

    for s in spec.get("slices", []):
        name = s["name"]
        metric = s["metric"]
        sid = f"slice:{name}/{metric}"

        # Gom ket qua theo item, lay trung binh qua cac seed.
        pr_items = per_item(pr, metric, slice_name=name)
        base_items = per_item(base, metric, slice_name=name)

        verdict = "ok"
        note = ""
        value = None

        if not pr_items or set(pr_items) != set(base_items):
            verdict = "missing"
            note = "missing or mismatched slice items"
        else:
            keys = sorted(pr_items)

            value = sum(pr_items[k] for k in keys) / len(keys)

            # Dieu kien 1: khong duoc thap hon nguong.
            if "min" in s and value < s["min"]:
                verdict = "fail"

            # Dieu kien 2: khong duoc suy giam co y nghia.
            if s.get("no_significant_drop"):
                d, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"delta {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"

                if hi < 0:
                    verdict = "fail"

        if verdict != "ok" and s.get("blocking", False):
            blocked.append(sid)

        if verdict == "ok":
            status = "ok"
        elif s.get("blocking", False):
            status = "BLOCK"
        else:
            status = "warn"

        lines.append(
            f"  {sid:<38} "
            f"value={value if value is not None else 'N/A'} "
            f"min={s.get('min', 'N/A')} "
            f"{note} {status}"
        )

    return blocked, lines



def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
