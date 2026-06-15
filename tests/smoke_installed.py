#!/usr/bin/env python3
"""Smoke-test the INSTALLED measure-mirror wheel — NOT the source tree.

Run this from outside the repo (e.g. `cd /tmp && python .../tests/smoke_installed.py`)
so `import measure_mirror` resolves to the pip-installed package. Catches the
classic "works in the repo, broken on `pip install`" class (missing modules,
data files, import errors). Exits non-zero on any failure.
"""
import sys

import measure_mirror as mm

print("measure_mirror loaded from:", mm.__file__)
print("version:", mm.__version__)

# every public name in __all__ must actually be importable from the wheel
missing = [n for n in mm.__all__ if not hasattr(mm, n)]
assert not missing, f"__all__ names missing from installed package: {missing}"

# core deterministic probes work
lo, hi = mm.wilson_ci(5, 9)
assert 0.0 <= lo <= hi <= 1.0, (lo, hi)
assert mm.grim_check(0.55, 9).level == "FAIL"          # 0.55 impossible at n=9
assert mm.grim_check(0.556, 9).level == "OK"           # 5/9 reachable
assert mm.baseline_fairness("x", 0.62, 0.60, n=20).level == "FAIL"   # tied at n=20
assert mm.baseline_fairness("x", 0.80, 0.60).level == "OK"
assert mm.leakage_check(["a", "b"], ["b", "c"]).level == "FAIL"      # exact overlap
assert mm.leakage_check(["a"], ["x"]).level == "OK"
assert mm.power_check(20, 0.5).level == "WARN"

# audit() runs end to end
findings = mm.audit("/tmp/_mm_smoke_none.jsonl", "c",
                    reported_metric="acc", reported_acc=0.6, n=9, baseline=0.5)
assert findings and all(hasattr(f, "level") for f in findings)

# db is repo-local: when absent, lookups degrade gracefully (None / []), no crash
assert mm.lookup_baseline("nonexistent_task") is None
assert mm.lookup_reproduction("nonexistent_task") == []

print("SMOKE OK — installed package imports and core probes work; db degrades gracefully.")
sys.exit(0)
