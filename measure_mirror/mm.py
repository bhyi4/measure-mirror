"""
🪞 Measurement Mirror — probe engine (no training, pure rule+stat).

9 probes:
  ① Pre-registration ledger — append-only chain-hash, first-write wins,
      metric-swap detection, tamper detection, re-registration detection
  ② Fair baseline — crippled / tied / reversed baseline
  ③ Gaming boundary — metric directly in reward/loss
  ④a Small-sample Wilson CI + direction + data leakage (hash intersection)
      + effect-size (continuous metrics)
  ⑤ Multi-seed reproduction — cross-seed variance alarm
  ⑥ Scope — claimed scope wider than tested scope
  ⑦ Too-good — suspiciously large improvement alarm
  ⑧ Power — false-negative guard (n vs. minimum detectable effect)
  ⑨ Multiple comparisons — Bonferroni alarm for k>1 experiments in ledger

Design:
  - Zero dependencies (Python stdlib only). Deterministic. No trained model.
  - Each probe is an independent function. Add without touching existing ones.
  - Ledger = append-only JSONL + chain hash + first-write wins + SHA-256 seal.
"""
from __future__ import annotations
import json, math, time, hashlib, os, statistics
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────
@dataclass
class Finding:
    probe: str
    level: str   # OK / WARN / FAIL
    msg: str


# ─────────────────────────────────────────────────────────────
# ① Pre-registration ledger (append-only, chain-hashed)
# ─────────────────────────────────────────────────────────────
def _get_last_seal(ledger_path: str) -> str:
    """Return the seal of the last entry in the ledger, or 'genesis'."""
    if not os.path.exists(ledger_path):
        return "genesis"
    last_seal = "genesis"
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if "seal" in e:
                    last_seal = e["seal"]
            except json.JSONDecodeError:
                continue
    return last_seal


def preregister(ledger_path: str, claim_id: str, *, metric: str,
                min_n: int, baseline: float, pass_threshold: float) -> dict:
    """Seal evaluation criteria BEFORE seeing results.

    Each entry is cryptographically linked to the previous one (chain hash).
    Re-registration for the same claim_id is silently ignored — only the
    first registration counts in audit().

    Chain link: deleting or inserting entries breaks the chain and is
    detected by verify_chain(). Complete ledger replacement is NOT caught
    here — use git commit anchoring for that guarantee.
    """
    prev_seal = _get_last_seal(ledger_path)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "claim_id": claim_id,
        "metric": metric,
        "min_n": min_n,
        "baseline": baseline,
        "pass_threshold": pass_threshold,
        "prev_seal": prev_seal,
    }
    entry["seal"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _load_prereg(ledger_path: str, claim_id: str) -> dict | None:
    """Return the FIRST registration only. Later entries are ignored."""
    if not os.path.exists(ledger_path):
        return None
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("claim_id") == claim_id:
                return e
    return None


def _verify_seal(entry: dict) -> bool:
    """Recompute SHA-256 seal. Works for legacy (no prev_seal) and chained entries."""
    stored = entry.get("seal", "")
    check = {k: v for k, v in entry.items() if k != "seal"}
    expected = hashlib.sha256(
        json.dumps(check, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return stored == expected


def verify_chain(ledger_path: str) -> list[Finding]:
    """Verify full ledger integrity: individual seals + chain links.

    Catches: tampered entries, deleted entries, inserted entries.
    Does NOT catch: complete ledger file deletion + fresh re-registration
    (use git commit anchoring for that guarantee).
    """
    if not os.path.exists(ledger_path):
        return [Finding("① chain-integrity", "OK", "Empty ledger.")]

    entries = []
    bad_lines = []
    with open(ledger_path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                bad_lines.append(i)

    if bad_lines:
        return [Finding("① chain-integrity", "FAIL",
            f"Malformed JSON at line(s) {bad_lines}. Ledger corrupted.")]

    if not entries:
        return [Finding("① chain-integrity", "OK", "Empty ledger.")]

    findings = []
    prev_seal = "genesis"

    for i, entry in enumerate(entries):
        cid = entry.get("claim_id", "?")

        if not _verify_seal(entry):
            findings.append(Finding("① chain-integrity", "FAIL",
                f"Seal mismatch at entry {i + 1} (claim_id={cid}). Entry was tampered."))
            prev_seal = entry.get("seal", "")
            continue

        # Chain link — only for entries that carry prev_seal (new format).
        # Legacy entries without prev_seal are skipped gracefully.
        entry_prev = entry.get("prev_seal")
        if entry_prev is not None and entry_prev != prev_seal:
            findings.append(Finding("① chain-integrity", "FAIL",
                f"Chain break before entry {i + 1} (claim_id={cid}). "
                f"Expected prev={prev_seal[:8]}…, got {entry_prev[:8]}…. "
                f"An entry was deleted or inserted before this point."))

        prev_seal = entry.get("seal", "")

    if not findings:
        return [Finding("① chain-integrity", "OK",
            f"Chain intact — {len(entries)} entries verified.")]
    return findings


# ─────────────────────────────────────────────────────────────
# ④a-1 Small-sample confidence interval (Wilson score, binomial)
# ─────────────────────────────────────────────────────────────
def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = max(0.0, min(1.0, k / n))
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# ─────────────────────────────────────────────────────────────
# ④a-2 Data leakage (train ∩ test hash intersection)
# ─────────────────────────────────────────────────────────────
def leakage_check(train_items, test_items) -> Finding:
    def H(xs):
        return {hashlib.sha256(str(x).encode()).hexdigest() for x in xs}
    th, eh = H(train_items), H(test_items)
    inter = th & eh
    if inter:
        frac = len(inter) / max(1, len(eh))
        return Finding("④a data-leakage", "FAIL",
            f"train∩test = {len(inter)} items ({frac:.1%} of test). Contaminated.")
    return Finding("④a data-leakage", "OK", "train∩test = 0. No leakage.")


# ─────────────────────────────────────────────────────────────
# ② Fair baseline
# ─────────────────────────────────────────────────────────────
def baseline_fairness(name: str, claimed: float, baseline: float, *,
                      higher_better: bool = True, margin: float = 0.01) -> Finding:
    diff = (claimed - baseline) if higher_better else (baseline - claimed)
    if diff <= -margin:
        return Finding("② fair-baseline", "FAIL",
            f"{name}: claimed {claimed:.3f} is WORSE than baseline {baseline:.3f}. "
            f"Baseline wins — claim invalid.")
    if abs(diff) < margin:
        return Finding("② fair-baseline", "FAIL",
            f"{name}: claimed {claimed:.3f} ≈ baseline {baseline:.3f} "
            f"(Δ{diff:+.3f} < {margin}). Tied — no genuine advantage.")
    return Finding("② fair-baseline", "OK",
        f"{name}: claimed {claimed:.3f} beats baseline {baseline:.3f} (Δ{diff:+.3f}).")


# ─────────────────────────────────────────────────────────────
# Shared baseline DB lookup
# ─────────────────────────────────────────────────────────────
def lookup_baseline(task: str | None, db_dir: str | None = None) -> float | None:
    if not task:
        return None
    p = os.path.join(db_dir or "db", "baselines.json")
    if not os.path.exists(p):
        return None
    try:
        db = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    e = db.get(task)
    return e.get("baseline") if isinstance(e, dict) else None


# ─────────────────────────────────────────────────────────────
# ③ Gaming boundary — metric directly in reward/loss
# ─────────────────────────────────────────────────────────────
def gaming_check(metric: str, reward_terms: list[str]) -> Finding:
    metric_lower = metric.lower()
    hits = [t for t in reward_terms if metric_lower in t.lower()]
    if hits:
        return Finding("③ gaming", "FAIL",
            f"Eval metric '{metric}' found in reward/loss terms {hits}. Self-fulfilling.")
    return Finding("③ gaming", "OK",
        f"Eval metric '{metric}' not in reward/loss. No gaming detected.")


# ─────────────────────────────────────────────────────────────
# ⑤ Multi-seed reproduction
# ─────────────────────────────────────────────────────────────
def multiseed_check(seed_results: list[float], *, baseline: float = 0.5,
                    cv_threshold: float = 0.10) -> Finding:
    if len(seed_results) < 2:
        return Finding("⑤ multi-seed", "WARN",
            f"Only {len(seed_results)} seed result(s) — cannot verify reproducibility.")
    mean = statistics.mean(seed_results)
    std = statistics.stdev(seed_results)
    cv = std / mean if mean != 0 else float("inf")
    lo, hi = min(seed_results), max(seed_results)
    if lo <= baseline <= hi:
        return Finding("⑤ multi-seed", "FAIL",
            f"Seed range [{lo:.3f}, {hi:.3f}] includes baseline({baseline}). Unstable.")
    if cv >= cv_threshold:
        return Finding("⑤ multi-seed", "WARN",
            f"CV={cv:.2%} ≥ {cv_threshold:.0%}. mean={mean:.3f}, std={std:.3f}.")
    return Finding("⑤ multi-seed", "OK",
        f"{len(seed_results)} seeds: mean={mean:.3f}, std={std:.3f}, CV={cv:.2%}. Stable.")


# ─────────────────────────────────────────────────────────────
# ⑥ Scope — over-generalization
# ─────────────────────────────────────────────────────────────
def scope_check(claimed_scope, tested_scope) -> Finding:
    tested = set(tested_scope)
    untested = [c for c in claimed_scope if c not in tested]
    if untested:
        return Finding("⑥ scope", "FAIL",
            f"Claimed {untested} not tested (evidence={list(tested_scope)}). "
            f"Over-generalization.")
    return Finding("⑥ scope", "OK",
        f"Claimed scope ⊆ tested scope {list(tested_scope)}.")


# ─────────────────────────────────────────────────────────────
# ⑦ Too-good — suspiciously large improvement
# ─────────────────────────────────────────────────────────────
def too_good_check(name: str, claimed: float, baseline: float, *,
                   suspicious_margin: float = 0.30) -> Finding:
    diff = claimed - baseline
    if diff >= suspicious_margin:
        return Finding("⑦ too-good", "WARN",
            f"{name}: Δ={diff:+.3f} ≥ {suspicious_margin}. "
            f"Suspiciously large — check for measurement defects first.")
    return Finding("⑦ too-good", "OK", f"{name}: Δ={diff:+.3f} — within normal range.")


# ─────────────────────────────────────────────────────────────
# ⑧ Power — false-negative guard
# ─────────────────────────────────────────────────────────────
def power_check(n: int, baseline: float, *,
                min_detectable_effect: float = 0.05,
                alpha: float = 0.05,
                target_power: float = 0.80) -> Finding:
    """Warn when n is too small to detect the minimum detectable effect.

    Closes the gap between "bidirectional" (false positive AND negative)
    and the actual implementation — false negatives are silently missed
    without this probe.

    Uses a two-sample z-test approximation for binary proportion metrics.
    Defaults: alpha=0.05 (two-sided 95% CI), target_power=0.80.
    """
    z_alpha2 = 1.96   # two-sided alpha = 0.05
    z_beta = 0.842    # 80% power
    p1 = min(1.0, baseline + min_detectable_effect)
    var = (baseline * (1 - baseline) + p1 * (1 - p1)) / 2  # pooled under H1
    n_required = math.ceil(
        ((z_alpha2 + z_beta) ** 2 * var) / (min_detectable_effect ** 2)
    )
    if n < n_required:
        return Finding("⑧ power", "WARN",
            f"n={n} insufficient to detect Δ={min_detectable_effect:+.2f} above "
            f"baseline={baseline} at {target_power:.0%} power (need n≥{n_required}). "
            f"High false-negative risk — a true effect may go undetected.")
    return Finding("⑧ power", "OK",
        f"n={n} ≥ {n_required} — sufficient for Δ={min_detectable_effect:+.2f} "
        f"at {target_power:.0%} power.")


# ─────────────────────────────────────────────────────────────
# ⑨ Multiple comparisons — garden-of-forking-paths
# ─────────────────────────────────────────────────────────────
def multiple_comparisons_check(ledger_path: str, *, alpha: float = 0.05) -> Finding:
    """Detect k>1 distinct experiments in the same ledger (Bonferroni alarm).

    Running k experiments and reporting only the best inflates the
    false-positive rate. Shows the Bonferroni-corrected alpha = alpha/k.

    Best practice: use separate ledgers per independent project, or
    pre-register all k hypotheses before running any of them.
    """
    if not os.path.exists(ledger_path):
        return Finding("⑨ multiple-comparisons", "OK",
            "No ledger — single experiment assumed.")

    unique_claims: set[str] = set()
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                cid = e.get("claim_id")
                if cid:
                    unique_claims.add(cid)
            except json.JSONDecodeError:
                continue

    k = len(unique_claims)
    if k <= 1:
        return Finding("⑨ multiple-comparisons", "OK",
            f"k={k} — single experiment, no correction needed.")

    corrected = alpha / k
    return Finding("⑨ multiple-comparisons", "WARN",
        f"k={k} distinct experiments in ledger → "
        f"Bonferroni α={corrected:.4f} (not {alpha}). "
        f"95% CI threshold is too lenient. "
        f"Use separate ledgers per project, or pre-register all k hypotheses.")


# ─────────────────────────────────────────────────────────────
# Binary / classification metric audit
# ─────────────────────────────────────────────────────────────
def audit(ledger_path: str, claim_id: str, *,
          reported_metric: str, reported_acc: float, n: int,
          baseline: float | None = None, task: str | None = None,
          db_dir: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    db_note = ""
    if baseline is None:
        b = lookup_baseline(task, db_dir)
        if b is not None:
            baseline, db_note = b, f"  ← DB lookup (task={task})"
        else:
            baseline = 0.5
    if not (0.0 <= reported_acc <= 1.0):
        findings.append(Finding("④a acc-range", "FAIL",
            f"reported_acc={reported_acc:.3f} out of [0, 1]."))
        return findings
    if n < 0:
        findings.append(Finding("④a n-range", "FAIL", f"n={n} must be ≥ 0."))
        return findings

    k = round(reported_acc * n)
    lo, hi = wilson_ci(k, n)

    if lo <= baseline <= hi:
        findings.append(Finding("④a small-sample CI", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → 95%CI [{lo:.3f}, {hi:.3f}] "
            f"⊃ baseline({baseline}).{db_note} Indistinguishable from chance."))
    elif hi < baseline:
        findings.append(Finding("④a direction(anti-signal)", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"< baseline({baseline}). Worse than chance."))
    else:
        findings.append(Finding("④a small-sample CI", "OK",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"clears baseline({baseline})."))

    # ① pre-registration
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding("① pre-registration", "WARN",
            f"No pre-registration found for '{claim_id}'."))
    else:
        if not _verify_seal(pre):
            findings.append(Finding("① seal-tamper", "FAIL",
                f"Seal mismatch for '{claim_id}'. Ledger modified."))
        else:
            if n < pre["min_n"]:
                findings.append(Finding("① pre-registration(min_n)", "FAIL",
                    f"n={n} < registered min_n={pre['min_n']}."))
            if reported_metric != pre["metric"]:
                findings.append(Finding("① pre-registration(metric-swap)", "FAIL",
                    f"Reported metric '{reported_metric}' ≠ registered '{pre['metric']}'. "
                    f"Post-hoc swap. (seal={pre['seal']})"))
            if reported_acc < pre["pass_threshold"]:
                findings.append(Finding("① pre-registration(pass-threshold)", "FAIL",
                    f"acc={reported_acc:.3f} < registered pass_threshold="
                    f"{pre['pass_threshold']:.3f}. (seal={pre['seal']})"))

    return findings


# ─────────────────────────────────────────────────────────────
# Continuous / regression metric audit
# ─────────────────────────────────────────────────────────────
def continuous_audit(ledger_path: str, claim_id: str, *,
                     reported_metric: str, reported_value: float,
                     baseline_value: float, n: int,
                     std: float | None = None,
                     higher_better: bool = True) -> list[Finding]:
    """Audit continuous/regression metrics (Pearson r, MSE, RMSE, …)."""
    findings: list[Finding] = []

    diff = (reported_value - baseline_value) if higher_better else (baseline_value - reported_value)
    if diff <= 0:
        symbol = "≤" if higher_better else "≥"
        findings.append(Finding("④a direction", "FAIL",
            f"value={reported_value:.4f} {symbol} baseline={baseline_value:.4f}. Baseline wins."))
    else:
        findings.append(Finding("④a direction", "OK",
            f"Δ={diff:+.4f} — {'higher' if higher_better else 'lower'}-is-better met."))

    if std is not None and std > 0:
        z = abs(reported_value - baseline_value) / std
        if z < 1.0:
            findings.append(Finding("④a effect-size", "WARN",
                f"z={z:.2f} < 1.0 — weak practical significance (n={n})."))
        else:
            findings.append(Finding("④a effect-size", "OK", f"z={z:.2f} ≥ 1.0."))

    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding("① pre-registration", "WARN",
            f"No pre-registration for '{claim_id}'."))
    else:
        if not _verify_seal(pre):
            findings.append(Finding("① seal-tamper", "FAIL",
                f"Seal mismatch for '{claim_id}'."))
        else:
            if reported_metric != pre["metric"]:
                findings.append(Finding("① pre-registration(metric-swap)", "FAIL",
                    f"'{reported_metric}' ≠ registered '{pre['metric']}'. "
                    f"(seal={pre['seal']})"))
            if n < pre["min_n"]:
                findings.append(Finding("① pre-registration(min_n)", "FAIL",
                    f"n={n} < registered min_n={pre['min_n']}."))

    return findings


# ─────────────────────────────────────────────────────────────
# Full audit — all probes in one call
# ─────────────────────────────────────────────────────────────
def full_audit(ledger_path: str, claim_id: str, *,
               reported_metric: str, reported_acc: float, n: int,
               baseline: float | None = None, task: str | None = None,
               db_dir: str | None = None,
               competing_name: str | None = None,          # ②
               competing_acc: float | None = None,         # ②
               reward_terms: list[str] | None = None,      # ③
               train_items=None, test_items=None,           # ④a-2
               seed_results: list[float] | None = None,    # ⑤
               claimed_scope=None, tested_scope=None,      # ⑥
               min_detectable_effect: float | None = None, # ⑧
               check_chain: bool = True,                   # ① chain
               check_multiplicity: bool = False) -> list[Finding]:  # ⑨
    """Run all probes in one call. Optional probes activate when args are provided."""
    _baseline = baseline
    if _baseline is None:
        b = lookup_baseline(task, db_dir)
        _baseline = b if b is not None else 0.5

    findings: list[Finding] = []

    # ① + ④a-1
    findings.extend(audit(ledger_path, claim_id,
                          reported_metric=reported_metric,
                          reported_acc=reported_acc, n=n,
                          baseline=_baseline, task=task, db_dir=db_dir))
    # ① chain integrity (only failures — OK is implied by absence)
    if check_chain:
        for f in verify_chain(ledger_path):
            if f.level != "OK":
                findings.append(f)
    # ②
    if competing_name is not None and competing_acc is not None:
        findings.append(baseline_fairness(competing_name, reported_acc, competing_acc))
    # ③
    if reward_terms is not None:
        findings.append(gaming_check(reported_metric, reward_terms))
    # ④a-2
    if train_items is not None and test_items is not None:
        findings.append(leakage_check(train_items, test_items))
    # ⑤
    if seed_results is not None:
        findings.append(multiseed_check(seed_results, baseline=_baseline))
    # ⑥
    if claimed_scope is not None and tested_scope is not None:
        findings.append(scope_check(claimed_scope, tested_scope))
    # ⑦ always
    findings.append(too_good_check(claim_id, reported_acc, _baseline))
    # ⑧ power (optional)
    if min_detectable_effect is not None:
        findings.append(power_check(n, _baseline,
                                    min_detectable_effect=min_detectable_effect))
    # ⑨ multiple comparisons (optional)
    if check_multiplicity:
        findings.append(multiple_comparisons_check(ledger_path))

    return findings


# ─────────────────────────────────────────────────────────────
# Report printer
# ─────────────────────────────────────────────────────────────
def report(title: str, findings: list[Finding]) -> None:
    icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "🔴"}
    worst = "FAIL" if any(f.level == "FAIL" for f in findings) else \
            "WARN" if any(f.level == "WARN" for f in findings) else "OK"
    print(f"\n🪞 Audit: {title}")
    print(f"   Overall: {icon[worst]} {worst}")
    for f in findings:
        print(f"   {icon[f.level]} [{f.probe}] {f.msg}")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def _auto(name: str, ledger: str = "mm_ledger.jsonl") -> None:
    import sys
    cands = [f"{name}.json", f"results/{name}.json", f"mm_results/{name}.json"]
    path = next((c for c in cands if os.path.exists(c)), None)
    if not path:
        print(f"🪞 No result file found for '{name}'. "
              f"Write your evaluation result to {name}.json.")
        print(f'   Expected format: {{"acc":0.72,"n":500,"metric":"acc","baseline":0.5}}')
        sys.exit(1)
    d = json.load(open(path, encoding="utf-8"))
    cid = d.get("claim_id", name)
    acc, n = d.get("acc"), d.get("n")
    if acc is None or n is None:
        print(f"🪞 Error: {path} must contain 'acc' and 'n'.")
        sys.exit(1)
    print(f"📂 Loaded {path}")
    report(cid, audit(ledger, cid, reported_metric=d.get("metric", "acc"),
                      reported_acc=acc, n=n, baseline=d.get("baseline", 0.5)))


def _cli() -> None:
    import argparse, sys
    if len(sys.argv) == 2 and sys.argv[1] not in {"register", "audit"} \
            and not sys.argv[1].startswith("-"):
        _auto(sys.argv[1]); return
    p = argparse.ArgumentParser(
        prog="mm",
        description="🪞 Measurement Mirror — audit AI evaluation claims")
    p.add_argument("--ledger", default="mm_ledger.jsonl",
                   help="Ledger path (default: ./mm_ledger.jsonl)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("register",
                       help="Seal evaluation criteria BEFORE running the experiment")
    r.add_argument("claim_id")
    r.add_argument("--metric", required=True)
    r.add_argument("--min-n", type=int, default=200)
    r.add_argument("--baseline", type=float, default=0.5)
    r.add_argument("--pass", dest="pass_threshold", type=float, default=0.60)

    a = sub.add_parser("audit", help="Audit evaluation results")
    a.add_argument("claim_id", nargs="?")
    a.add_argument("--acc", type=float)
    a.add_argument("--n", type=int)
    a.add_argument("--metric", default="acc")
    a.add_argument("--baseline", type=float, default=0.5)
    a.add_argument("--file", help="Result JSON: {claim_id, metric, acc, n, baseline}")

    args = p.parse_args()
    if args.cmd == "register":
        e = preregister(args.ledger, args.claim_id, metric=args.metric,
                        min_n=args.min_n, baseline=args.baseline,
                        pass_threshold=args.pass_threshold)
        print(f"🔒 Sealed: {args.claim_id}  metric={args.metric} "
              f"min_n={args.min_n} baseline={args.baseline}  seal={e['seal']}")
    elif args.cmd == "audit":
        if args.file:
            d = json.load(open(args.file, encoding="utf-8"))
            cid = d.get("claim_id", "?")
            acc, n = d.get("acc"), d.get("n")
            metric, baseline = d.get("metric", "acc"), d.get("baseline", 0.5)
        else:
            cid, acc, n = args.claim_id, args.acc, args.n
            metric, baseline = args.metric, args.baseline
        if acc is None or n is None:
            p.error("audit requires --acc and --n (or --file)")
        report(cid, audit(args.ledger, cid, reported_metric=metric,
                          reported_acc=acc, n=n, baseline=baseline))


if __name__ == "__main__":
    _cli()
