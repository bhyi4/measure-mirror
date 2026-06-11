"""
Measurement Mirror — Quickstart

Honest researcher happy path: pre-register → experiment → audit.
Run: python examples/quickstart.py
"""
import os
from measure_mirror import mm

LEDGER = "/tmp/mm_quickstart_ledger.jsonl"
if os.path.exists(LEDGER):
    os.remove(LEDGER)

print("=" * 60)
print("🪞 Measurement Mirror — Quickstart")
print("=" * 60)

# ─── Step 1: BEFORE the experiment — seal the criteria ───────
print("\n[Step 1] Pre-registration: seal criteria before running experiment")
entry = mm.preregister(LEDGER, "my_classifier",
                       metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60)
print(f"  ✅ Sealed — claim_id=my_classifier  metric=acc  "
      f"min_n=200  baseline=0.5  seal={entry['seal']}")

# ─── Step 2: Run the experiment (simulated here) ─────────────
print("\n[Step 2] Run experiment... (simulated)")
result_acc, result_n = 0.72, 500
print(f"  → result: acc={result_acc}, n={result_n}")

# ─── Step 3: Audit ───────────────────────────────────────────
print("\n[Step 3] Audit")
mm.report("Honest result: acc=0.72, n=500",
          mm.audit(LEDGER, "my_classifier",
                   reported_metric="acc", reported_acc=0.72, n=500))

# ─── Show what the mirror catches ────────────────────────────
print("\n" + "─" * 60)
print("What the mirror catches (illusion examples):")
print("─" * 60)

mm.report("Illusion ①: small sample cherry-pick (acc=0.85, n=12)",
          mm.audit(LEDGER, "my_classifier",
                   reported_metric="acc", reported_acc=0.85, n=12))

mm.report("Illusion ②: post-hoc metric swap (f1 instead of acc)",
          mm.audit(LEDGER, "my_classifier",
                   reported_metric="f1_weighted", reported_acc=0.91, n=500))

mm.report("Illusion ③: crippled baseline (tied within margin)",
          [mm.baseline_fairness("vs random baseline", 0.502, 0.500)])

mm.report("Illusion ④: data leakage (50% test overlap)",
          [mm.leakage_check(list(range(100)), list(range(50, 150)))])

mm.report("Illusion ⑤: unstable seeds (baseline crosses range)",
          [mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5)])

mm.report("Illusion ⑥: scope overreach",
          [mm.scope_check(["general_reasoning", "math"], ["musr_task_a"])])

mm.report("Illusion ⑦: too-good result (Δ=+0.45)",
          [mm.too_good_check("suspiciously_good", 0.95, 0.5)])

# ─── Full audit in one call ───────────────────────────────────
print("\n" + "─" * 60)
print("Full 7-probe audit (mm.full_audit):")
print("─" * 60)

LEDGER2 = "/tmp/mm_quickstart_ledger2.jsonl"
if os.path.exists(LEDGER2):
    os.remove(LEDGER2)
mm.preregister(LEDGER2, "full_test", metric="acc", min_n=50,
               baseline=0.5, pass_threshold=0.65)

findings = mm.full_audit(
    LEDGER2, "full_test",
    reported_metric="acc", reported_acc=0.72, n=200,
    baseline=0.5,
    competing_name="strong_baseline", competing_acc=0.68,
    reward_terms=["cross_entropy", "kl_div"],
    train_items=list(range(100)), test_items=list(range(100, 200)),
    seed_results=[0.70, 0.72, 0.74],
    claimed_scope=["task_a"], tested_scope=["task_a"],
)
mm.report("full_audit result", findings)
