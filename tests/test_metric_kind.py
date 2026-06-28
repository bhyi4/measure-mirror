"""P0 — metric-kind self-calibration: the proportion probes must not false-FAIL on
percentage / delta / span / unbounded metrics, and the baseline must come from a
declared `chance`, not a hardcoded 0.5.

Fixtures use the real shapes from the dogfooding ledgers (eng_improve_pct 54.1,
real_granularity +0.091, window_elastic 6.4, selection_capacity_wall ±0.09).
"""
import measure_mirror.mm as mm


def _levels(findings):
    return {f.probe: f.level for f in findings}


def _has_fail(findings, needle):
    return any(f.level == "FAIL" and needle in f.probe for f in findings)


# ── resolve_metric_kind: inference + explicit override ────────────────────────
def test_infer_proportion_default():
    lo, hi, chance, is_prop, declared = mm.resolve_metric_kind("accuracy")
    assert (lo, hi) == (0.0, 1.0) and is_prop and chance == 0.5 and not declared


def test_infer_percent():
    lo, hi, chance, is_prop, _ = mm.resolve_metric_kind("eng_improve_pct")
    assert (lo, hi) == (0.0, 100.0) and is_prop and chance == 50.0


def test_infer_delta_is_unbounded_not_proportion():
    lo, hi, chance, is_prop, _ = mm.resolve_metric_kind("real_granularity_delta")
    assert lo == float("-inf") and hi == float("inf") and not is_prop and chance is None


def test_infer_span_nonnegative_not_proportion():
    lo, hi, _, is_prop, _ = mm.resolve_metric_kind("window_elastic_span")
    assert (lo, hi) == (0.0, float("inf")) and not is_prop


def test_explicit_range_overrides_name():
    lo, hi, chance, is_prop, declared = mm.resolve_metric_kind("accuracy", metric_range=[0, 100], chance=25.0)
    assert (lo, hi) == (0.0, 100.0) and chance == 25.0 and declared


def test_unbounded_keyword():
    lo, hi, _, is_prop, _ = mm.resolve_metric_kind("anything", metric_range="unbounded")
    assert lo == float("-inf") and hi == float("inf") and not is_prop


# ── audit: no false-FAIL on non-proportion metrics (the P0 bug) ───────────────
def _audit(metric, val, n, **kw):
    return mm.audit("/tmp/_mk_none.jsonl", "c", reported_metric=metric, reported_acc=val, n=n, **kw)


def test_percent_no_false_range_fail():
    f = _audit("eng_improve_pct", 54.1, 3000)
    assert not _has_fail(f, "metric-range")              # 54.1 ∈ [0,100], not "out of [0,1]"


def test_delta_skips_grim():
    f = _audit("real_granularity_delta", 0.091, 500)     # 0.091*500=45.5 → would false-GRIM as a proportion
    assert not _has_fail(f, "GRIM")
    assert any(x.probe == "④a metric-kind" for x in f)   # explicitly noted as continuous


def test_span_no_false_fail():
    f = _audit("window_elastic_span", 6.4, 800)
    assert not any(x.level == "FAIL" for x in f)


def test_negative_delta_ok():
    f = _audit("selection_capacity_wall_delta", -0.09, 360)
    assert not any(x.level == "FAIL" for x in f)


# ── baseline-0.5 artifact removed: declared chance is used ────────────────────
def test_declared_chance_beats_half():
    # 24-way task: real chance ≈ 0.042. acc=0.10 is well above it.
    default = _audit("selection_acc", 0.10, 3000)                 # baseline defaults to 0.5
    declared = _audit("selection_acc", 0.10, 3000, chance=0.042)  # real chance
    assert _has_fail(default, "direction")                        # 0.10 < 0.5 → "worse than chance" (the artifact)
    assert _levels(declared).get("④a small-sample CI") == "OK"    # 0.10 ≫ 0.042 → real signal


# ── GRIM still catches a genuine impossibility (no over-correction) ───────────
def test_grim_still_catches_impossible_proportion():
    assert _has_fail(_audit("acc", 0.52, 30), "GRIM")   # 0.52*30 = 15.6, not achievable


def test_percent_grim_runs_on_normalised_value():
    # 54.1% with n=3000 IS achievable (1623/3000); must not GRIM-FAIL.
    assert not _has_fail(_audit("eng_improve_pct", 54.1, 3000), "GRIM")


# ── error message guides the fix ──────────────────────────────────────────────
def test_out_of_range_message_guides():
    f = _audit("mystery_score", 42.0, 100)               # 42 ∉ [0,1] default, undeclared
    msg = next(x.msg for x in f if x.level == "FAIL")
    assert "metric_range" in msg and "mm_preregister" in msg


# ── declared range/chance round-trips through a sealed prereg ─────────────────
def test_prereg_seals_and_audit_reads_metric_kind(tmp_path):
    led = str(tmp_path / "l.jsonl")
    entry = mm.preregister(led, "pctclaim", metric="eng_improve_pct", min_n=100,
                           baseline=50.0, pass_threshold=50.0, metric_range=[0, 100], chance=50.0)
    assert entry["metric_range"] == [0, 100] and entry["chance"] == 50.0
    assert mm._verify_seal(entry)                        # fields are inside the seal
    # audit with NO explicit kind args → must read them from the sealed prereg
    f = mm.audit(led, "pctclaim", reported_metric="eng_improve_pct", reported_acc=54.1, n=3000)
    assert not _has_fail(f, "metric-range")
