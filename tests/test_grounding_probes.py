"""Grounding probes (㉑㉒㉓) — mutual-grounding arc sealed defense laws.

These are the wiring/behavior tests. The FP/FN self-calibration that earns
"mm flagged" language lives separately in eval/self_fpfn/.
"""
import tempfile

from measure_mirror import (
    anchor_basis_check, threshold_provenance_check, content_delta_check,
    anchor_line_source_check, anchor_cell_check,
    verify, GROUPS,
)


# ㉑ anchor basis ---------------------------------------------------------
def test_anchor_basis_dynamics_ok():
    f = anchor_basis_check("dynamics-measured")
    assert f.level == "OK" and f.probe.startswith("㉑")


def test_anchor_basis_structural_warns():
    f = anchor_basis_check("structural-argument")
    assert f.level == "WARN"
    assert "structural" in f.msg.lower()


def test_anchor_basis_unknown_warns():
    assert anchor_basis_check("whatever").level == "WARN"


# ㉒ threshold provenance -------------------------------------------------
def test_threshold_external_ok():
    assert threshold_provenance_check("external-fixed").level == "OK"


def test_threshold_observed_warns():
    f = threshold_provenance_check("observed-distribution")
    assert f.level == "WARN"
    assert "self-calibrating" in f.msg.lower()


# ㉓ content delta -------------------------------------------------------
def test_content_delta_match_only_warns():
    f = content_delta_check(["match", "agreement"])
    assert f.level == "WARN"
    assert "rubber-stamp" in f.msg.lower()


def test_content_delta_with_content_ok():
    assert content_delta_check(["match", "incompressibility"]).level == "OK"


def test_content_delta_accepts_str():
    assert content_delta_check("match").level == "WARN"


# registry + verify wiring ----------------------------------------------
def test_probes_registered_in_design_group():
    for name in ("anchor_basis_check", "threshold_provenance_check",
                 "content_delta_check"):
        assert name in GROUPS["design"]


def test_verify_runs_grounding_probes_by_key():
    led = tempfile.mktemp(suffix=".jsonl")
    data = {"anchor_basis": "structural-argument",
            "threshold_source": "observed-distribution",
            "judgment_basis": ["match"]}
    findings = verify(led, data)
    probes = {f.probe[:1] for f in findings}
    assert {"㉑", "㉒", "㉓"} <= probes
    assert all(f.level == "WARN" for f in findings
               if f.probe[:1] in {"㉑", "㉒", "㉓"})


def test_verify_group_restrict_excludes_grounding():
    led = tempfile.mktemp(suffix=".jsonl")
    data = {"anchor_basis": "structural-argument"}
    findings = verify(led, data, groups=["judge"])
    assert not any(f.probe.startswith("㉑") for f in findings)


# preregister → audit round-trip (SPEC amendment A1) ----------------------
def test_preregister_grounding_fields_flow_to_audit():
    import os
    from measure_mirror import preregister, audit
    led = os.path.join(tempfile.mkdtemp(), "led.jsonl")
    preregister(led, "c1", metric="acc", min_n=10, baseline=0.5,
                pass_threshold=0.6, kill_condition="acc < 0.5 on held-out",
                anchor_basis="structural-argument",
                threshold_source="observed-distribution")
    findings = audit(led, "c1", reported_metric="acc", reported_acc=0.9, n=50,
                     db_dir=tempfile.mkdtemp())
    by_symbol = {f.probe[:1]: f.level for f in findings}
    assert by_symbol.get("㉑") == "WARN"
    assert by_symbol.get("㉒") == "WARN"


def test_audit_without_grounding_fields_stays_silent():
    import os
    from measure_mirror import preregister, audit
    led = os.path.join(tempfile.mkdtemp(), "led.jsonl")
    preregister(led, "c2", metric="acc", min_n=10, baseline=0.5,
                pass_threshold=0.6, kill_condition="acc < 0.5 on held-out")
    findings = audit(led, "c2", reported_metric="acc", reported_acc=0.9, n=50,
                     db_dir=tempfile.mkdtemp())
    assert not any(f.probe[:1] in {"㉑", "㉒"} for f in findings)


# ㉔ anchor line source (SPEC amendment A2) -----------------------------
def test_anchor_line_aligned_ok():
    assert anchor_line_source_check("separator-aligned").level == "OK"


def test_anchor_line_copied_warns():
    f = anchor_line_source_check("copied-from-other-cell")
    assert f.level == "WARN" and f.probe.startswith("㉔")
    assert "copied" in f.msg.lower()


def test_anchor_line_unknown_warns():
    assert anchor_line_source_check("whatever").level == "WARN"


# ㉕ anchor cell (SPEC amendment A2) ------------------------------------
def test_anchor_cell_deep_ok():
    assert anchor_cell_check("deep-regime").level == "OK"


def test_anchor_cell_threshold_warns():
    f = anchor_cell_check("threshold-cell")
    assert f.level == "WARN" and f.probe.startswith("㉕")
    assert "threshold" in f.msg.lower() or "boundary" in f.msg.lower()


def test_anchor_cell_unknown_warns():
    assert anchor_cell_check("whatever").level == "WARN"


# registry + verify wiring for ㉔㉕ -------------------------------------
def test_a2_probes_registered_in_design_group():
    for name in ("anchor_line_source_check", "anchor_cell_check"):
        assert name in GROUPS["design"]


def test_verify_runs_a2_probes_by_key():
    led = tempfile.mktemp(suffix=".jsonl")
    data = {"anchor_line_source": "copied-from-other-cell",
            "anchor_cell": "threshold-cell"}
    findings = verify(led, data)
    symbols = {f.probe[:1] for f in findings}
    assert {"㉔", "㉕"} <= symbols
    assert all(f.level == "WARN" for f in findings if f.probe[:1] in {"㉔", "㉕"})


# preregister → audit round-trip for A2 (fields + known_confounds INFO) --
def test_a2_fields_and_confounds_flow_to_audit():
    import os
    from measure_mirror import preregister, audit
    led = os.path.join(tempfile.mkdtemp(), "led.jsonl")
    preregister(led, "c3", metric="acc", min_n=10, baseline=0.5,
                pass_threshold=0.6, kill_condition="acc < 0.5 held-out",
                anchor_cell="threshold-cell",
                anchor_line_source="copied-from-other-cell",
                known_confounds=["batch order mixed with self-direction"])
    findings = audit(led, "c3", reported_metric="acc", reported_acc=0.9, n=50,
                     db_dir=tempfile.mkdtemp())
    by_symbol = {f.probe[:1]: f for f in findings}
    assert by_symbol["㉔"].level == "WARN"
    assert by_symbol["㉕"].level == "WARN"
    assert by_symbol["㉖"].level == "INFO"       # known_confounds surfaced
    assert "1 confound" in by_symbol["㉖"].msg


def test_audit_without_a2_fields_silent():
    import os
    from measure_mirror import preregister, audit
    led = os.path.join(tempfile.mkdtemp(), "led.jsonl")
    preregister(led, "c4", metric="acc", min_n=10, baseline=0.5,
                pass_threshold=0.6, kill_condition="acc < 0.5 held-out")
    findings = audit(led, "c4", reported_metric="acc", reported_acc=0.9, n=50,
                     db_dir=tempfile.mkdtemp())
    assert not any(f.probe[:1] in {"㉔", "㉕", "㉖"} for f in findings)
