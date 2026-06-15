"""Property-based tests (Hypothesis) for the deterministic probes.

Hand-written tests check the cases we thought of; these check the cases we
didn't — random inputs across the whole domain, asserting invariants that must
ALWAYS hold. For a measurement-integrity tool the worst failure is a crash or a
silently wrong verdict on an input nobody happened to test.
"""
import math

from hypothesis import given, strategies as st

import measure_mirror as mm

LEVELS = {"OK", "WARN", "FAIL"}


# ── wilson_ci ────────────────────────────────────────────────────────────────
@given(n=st.integers(min_value=1, max_value=10_000),
       frac=st.floats(min_value=0.0, max_value=1.0))
def test_wilson_ci_is_a_valid_subinterval_of_unit(n, frac):
    k = round(frac * n)
    lo, hi = mm.wilson_ci(k, n)
    assert 0.0 <= lo <= hi <= 1.0          # always a valid interval in [0,1]
    assert math.isfinite(lo) and math.isfinite(hi)


@given(n=st.integers(min_value=1, max_value=5000))
def test_wilson_ci_widens_toward_small_n(n):
    # at the same proportion, a smaller n must not give a TIGHTER interval
    lo_small, hi_small = mm.wilson_ci(round(0.6 * n), n)
    lo_big, hi_big = mm.wilson_ci(round(0.6 * n * 4), n * 4)
    assert (hi_small - lo_small) >= (hi_big - lo_big) - 1e-9


def test_wilson_ci_degenerate_n_zero():
    assert mm.wilson_ci(0, 0) == (0.0, 1.0)   # no data → maximal uncertainty


# ── grim_check ───────────────────────────────────────────────────────────────
@given(acc=st.floats(min_value=0.0, max_value=1.0),
       n=st.integers(min_value=1, max_value=2000))
def test_grim_never_crashes_and_returns_a_level(acc, n):
    f = mm.grim_check(round(acc, 3), n)
    assert f.level in LEVELS


@given(n=st.integers(min_value=1, max_value=500), k=st.integers(min_value=0))
def test_grim_accepts_every_reachable_proportion(n, k):
    k = k % (n + 1)                         # 0 <= k <= n
    acc = round(k / n, 3)
    # a proportion that IS exactly k/n must never be flagged impossible
    assert mm.grim_check(acc, n).level == "OK"


# ── baseline_fairness ────────────────────────────────────────────────────────
@given(claimed=st.floats(min_value=0.0, max_value=1.0),
       baseline=st.floats(min_value=0.0, max_value=1.0),
       n=st.one_of(st.none(), st.integers(min_value=1, max_value=10_000)))
def test_baseline_fairness_never_crashes(claimed, baseline, n):
    assert mm.baseline_fairness("x", claimed, baseline, n=n).level in LEVELS


@given(baseline=st.floats(min_value=0.05, max_value=0.9),
       gap=st.floats(min_value=0.0, max_value=0.05))
def test_baseline_worse_than_baseline_always_fails(baseline, gap):
    # claimed strictly worse than baseline must always FAIL (n-agnostic)
    assert mm.baseline_fairness("x", baseline - gap - 0.02, baseline).level == "FAIL"


# ── leakage_check ────────────────────────────────────────────────────────────
@given(train=st.lists(st.text(), max_size=20), test=st.lists(st.text(), max_size=20))
def test_leakage_never_crashes_and_is_consistent(train, test):
    f = mm.leakage_check(train, test)
    assert f.level in LEVELS
    # any exact shared item must be caught (FAIL); fuzzy only adds WARNs
    if set(train) & set(test) and any(train):
        assert f.level == "FAIL"


@given(items=st.lists(st.text(min_size=1), min_size=1, max_size=10))
def test_identical_train_test_is_always_leakage(items):
    assert mm.leakage_check(items, items).level == "FAIL"


# ── power / multiseed / scope / too_good / gaming ────────────────────────────
@given(n=st.integers(min_value=1, max_value=100_000),
       baseline=st.floats(min_value=0.01, max_value=0.99))
def test_power_check_never_crashes(n, baseline):
    assert mm.power_check(n, baseline).level in LEVELS


@given(seeds=st.lists(st.floats(min_value=0.0, max_value=1.0), max_size=20))
def test_multiseed_never_crashes(seeds):
    assert mm.multiseed_check(seeds).level in LEVELS


@given(claimed=st.lists(st.text(), max_size=10), tested=st.lists(st.text(), max_size=10))
def test_scope_check_never_crashes(claimed, tested):
    f = mm.scope_check(claimed, tested)
    assert f.level in LEVELS
    if set(claimed) - set(tested):          # something claimed but untested
        assert f.level == "FAIL"
