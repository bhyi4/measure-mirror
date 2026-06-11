"""
🪞 Measurement Mirror — probe engine (no training, pure rule+stat).

7 checks:
  ① Pre-registration ledger (append-only, first-write wins) + metric-swap + tamper detection
  ② Fair baseline — crippled / tied / reversed baseline
  ③ Gaming boundary — metric directly in reward/loss
  ④a Small-sample Wilson CI + direction + data leakage (hash intersection)
  ⑤ Multi-seed reproduction — cross-seed variance alarm
  ⑥ Scope — claimed scope wider than tested scope (over-generalization)
  ⑦ Self-catch — suspiciously good result alarm

Design:
  - No learned model. Deterministic. Zero dependencies (Python stdlib only).
  - Each probe is an independent function. Add new checks without touching existing ones.
  - Ledger = append-only JSONL + first-write wins + SHA-256 seal = technical heart of integrity.
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
# ① Pre-registration ledger (append-only)
# ─────────────────────────────────────────────────────────────
def preregister(ledger_path: str, claim_id: str, *, metric: str,
                min_n: int, baseline: float, pass_threshold: float) -> dict:
    """Seal evaluation criteria BEFORE seeing results. Append-only. SHA-256 sealed.

    Re-registration for the same claim_id is silently ignored —
    only the first registration counts in audit().
    """
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "claim_id": claim_id,
        "metric": metric,
        "min_n": min_n,
        "baseline": baseline,
        "pass_threshold": pass_threshold,
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
                return e  # first match — return immediately
    return None


def _verify_seal(entry: dict) -> bool:
    """Recompute the SHA-256 seal and compare with stored value."""
    stored = entry.get("seal", "")
    check = {k: v for k, v in entry.items() if k != "seal"}
    expected = hashlib.sha256(
        json.dumps(check, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return stored == expected


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
            f"train∩test = {len(inter)} items ({frac:.1%} of test). "
            f"Evaluation set contaminated.")
    return Finding("④a data-leakage", "OK", "train∩test = 0. No leakage detected.")


# ─────────────────────────────────────────────────────────────
# ② Fair baseline
# ─────────────────────────────────────────────────────────────
def baseline_fairness(name: str, claimed: float, baseline: float, *,
                      higher_better: bool = True, margin: float = 0.01) -> Finding:
    diff = (claimed - baseline) if higher_better else (baseline - claimed)
    if diff <= -margin:
        return Finding("② fair-baseline", "FAIL",
            f"{name}: claimed {claimed:.3f} is WORSE than baseline {baseline:.3f}. "
            f"Baseline wins — claim invalid / gaming.")
    if abs(diff) < margin:
        return Finding("② fair-baseline", "FAIL",
            f"{name}: claimed {claimed:.3f} ≈ baseline {baseline:.3f} "
            f"(Δ{diff:+.3f} < {margin}). Tied — no genuine advantage.")
    return Finding("② fair-baseline", "OK",
        f"{name}: claimed {claimed:.3f} exceeds baseline {baseline:.3f} (Δ{diff:+.3f}).")


# ─────────────────────────────────────────────────────────────
# Shared baseline DB lookup
# ─────────────────────────────────────────────────────────────
def lookup_baseline(task: str | None, db_dir: str | None = None) -> float | None:
    """Look up a task-level fair baseline from db/baselines.json. Returns None if not found."""
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
    """Detect if the evaluation metric appears directly in the training reward/loss.

    reward_terms: list of component names in the training objective.
    """
    metric_lower = metric.lower()
    hits = [t for t in reward_terms if metric_lower in t.lower()]
    if hits:
        return Finding("③ gaming", "FAIL",
            f"Eval metric '{metric}' found in reward/loss terms {hits}. "
            f"Self-fulfilling artifact — remove or replace the term for an honest signal.")
    return Finding("③ gaming", "OK",
        f"Eval metric '{metric}' not found in reward/loss. No gaming detected.")


# ─────────────────────────────────────────────────────────────
# ⑤ Multi-seed reproduction — cross-seed variance alarm
# ─────────────────────────────────────────────────────────────
def multiseed_check(seed_results: list[float], *, baseline: float = 0.5,
                    cv_threshold: float = 0.10) -> Finding:
    """Alarm if cross-seed variance is large or if baseline falls within the result range.

    cv_threshold: coefficient-of-variation threshold (std/mean). Default 0.10 (10%).
    """
    if len(seed_results) < 2:
        return Finding("⑤ multi-seed", "WARN",
            f"Only {len(seed_results)} seed result(s) — cannot verify reproducibility. "
            f"Minimum 2 required.")
    mean = statistics.mean(seed_results)
    std = statistics.stdev(seed_results)
    cv = std / mean if mean != 0 else float("inf")
    lo, hi = min(seed_results), max(seed_results)
    if lo <= baseline <= hi:
        return Finding("⑤ multi-seed", "FAIL",
            f"Seed range [{lo:.3f}, {hi:.3f}] includes baseline({baseline}). "
            f"Result falls below baseline on some seeds — signal is unstable.")
    if cv >= cv_threshold:
        return Finding("⑤ multi-seed", "WARN",
            f"CV={cv:.2%} ≥ {cv_threshold:.0%}. "
            f"mean={mean:.3f}, std={std:.3f} — high cross-seed variance.")
    return Finding("⑤ multi-seed", "OK",
        f"{len(seed_results)} seeds: mean={mean:.3f}, std={std:.3f}, CV={cv:.2%}. Stable.")


# ─────────────────────────────────────────────────────────────
# ⑥ Scope — over-generalization
# ─────────────────────────────────────────────────────────────
def scope_check(claimed_scope, tested_scope) -> Finding:
    """Flag when the claimed scope is wider than the tested evidence."""
    tested = set(tested_scope)
    untested = [c for c in claimed_scope if c not in tested]
    if untested:
        return Finding("⑥ scope", "FAIL",
            f"Claimed scope {untested} not tested (evidence={list(tested_scope)}). "
            f"Over-generalization — narrow the claim to tested scope.")
    return Finding("⑥ scope", "OK",
        f"Claimed scope ⊆ tested scope {list(tested_scope)}. No over-generalization.")


# ─────────────────────────────────────────────────────────────
# ⑦ Self-catch — suspiciously good result alarm
# ─────────────────────────────────────────────────────────────
def too_good_check(name: str, claimed: float, baseline: float, *,
                   suspicious_margin: float = 0.30) -> Finding:
    """Warn when Δ over baseline exceeds suspicious_margin. Suspect first."""
    diff = claimed - baseline
    if diff >= suspicious_margin:
        return Finding("⑦ too-good", "WARN",
            f"{name}: claimed={claimed:.3f}, baseline={baseline:.3f}, "
            f"Δ={diff:+.3f} ≥ {suspicious_margin}. "
            f"Suspiciously large — check for measurement defects or gaming first.")
    return Finding("⑦ too-good", "OK",
        f"{name}: Δ={diff:+.3f} — within normal range.")


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
            f"reported_acc={reported_acc:.3f} must be between 0.0 and 1.0."))
        return findings
    if n < 0:
        findings.append(Finding("④a n-range", "FAIL",
            f"n={n} must be ≥ 0."))
        return findings

    k = round(reported_acc * n)
    lo, hi = wilson_ci(k, n)

    # ④a-1 small-sample CI + direction
    if lo <= baseline <= hi:
        findings.append(Finding(
            "④a small-sample CI", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → 95%CI [{lo:.3f}, {hi:.3f}] "
            f"⊃ baseline({baseline}).{db_note} "
            f"Statistically indistinguishable from chance."))
    elif hi < baseline:
        findings.append(Finding(
            "④a direction(anti-signal)", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"< baseline({baseline}). Worse than chance — anti-signal detected."))
    else:
        findings.append(Finding(
            "④a small-sample CI", "OK",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"clears baseline({baseline})."))

    # ① pre-registration check
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding(
            "① pre-registration", "WARN",
            f"No pre-registration found for '{claim_id}'. "
            f"Metric may have been defined after seeing results."))
    else:
        if not _verify_seal(pre):
            findings.append(Finding(
                "① seal-tamper", "FAIL",
                f"Seal mismatch for '{claim_id}'. "
                f"Ledger file may have been modified — pre-registration is invalid."))
        else:
            if n < pre["min_n"]:
                findings.append(Finding(
                    "① pre-registration(min_n)", "FAIL",
                    f"Reported n={n} < registered min_n={pre['min_n']}. "
                    f"Sample size requirement not met."))
            if reported_metric != pre["metric"]:
                findings.append(Finding(
                    "① pre-registration(metric-swap)", "FAIL",
                    f"Reported metric '{reported_metric}' ≠ registered '{pre['metric']}'. "
                    f"Post-hoc metric swap detected. (seal={pre['seal']})"))
            if reported_acc < pre["pass_threshold"]:
                findings.append(Finding(
                    "① pre-registration(pass-threshold)", "FAIL",
                    f"acc={reported_acc:.3f} < registered pass_threshold={pre['pass_threshold']:.3f}. "
                    f"Below pre-registered bar. (seal={pre['seal']})"))

    return findings


# ─────────────────────────────────────────────────────────────
# Continuous / regression metric audit
# ─────────────────────────────────────────────────────────────
def continuous_audit(ledger_path: str, claim_id: str, *,
                     reported_metric: str, reported_value: float,
                     baseline_value: float, n: int,
                     std: float | None = None,
                     higher_better: bool = True) -> list[Finding]:
    """Audit continuous/regression metrics (Pearson r, MSE, RMSE, …).

    Uses direction + effect-size (when std is provided) instead of Wilson CI.
    """
    findings: list[Finding] = []

    # ④a direction
    diff = (reported_value - baseline_value) if higher_better else (baseline_value - reported_value)
    if diff <= 0:
        symbol = "≤" if higher_better else "≥"
        findings.append(Finding("④a direction", "FAIL",
            f"value={reported_value:.4f} {symbol} baseline={baseline_value:.4f}. "
            f"Baseline wins — claim invalid."))
    else:
        findings.append(Finding("④a direction", "OK",
            f"Δ={diff:+.4f} — {'higher' if higher_better else 'lower'}-is-better criterion passed."))

    # ④a effect size (only when std provided)
    if std is not None and std > 0:
        z = abs(reported_value - baseline_value) / std
        if z < 1.0:
            findings.append(Finding("④a effect-size", "WARN",
                f"z={z:.2f} < 1.0 — practical significance is weak (n={n})."))
        else:
            findings.append(Finding("④a effect-size", "OK",
                f"z={z:.2f} ≥ 1.0 — practically significant."))

    # ① pre-registration
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding("① pre-registration", "WARN",
            f"No pre-registration found for '{claim_id}'."))
    else:
        if not _verify_seal(pre):
            findings.append(Finding("① seal-tamper", "FAIL",
                f"Seal mismatch for '{claim_id}'. Ledger may be tampered."))
        else:
            if reported_metric != pre["metric"]:
                findings.append(Finding("① pre-registration(metric-swap)", "FAIL",
                    f"Reported metric '{reported_metric}' ≠ registered '{pre['metric']}'. "
                    f"Post-hoc metric swap. (seal={pre['seal']})"))
            if n < pre["min_n"]:
                findings.append(Finding("① pre-registration(min_n)", "FAIL",
                    f"n={n} < registered min_n={pre['min_n']}."))

    return findings


# ─────────────────────────────────────────────────────────────
# Full audit — all 7 checks in one call
# ─────────────────────────────────────────────────────────────
def full_audit(ledger_path: str, claim_id: str, *,
               reported_metric: str, reported_acc: float, n: int,
               baseline: float | None = None, task: str | None = None,
               db_dir: str | None = None,
               competing_name: str | None = None,    # ②
               competing_acc: float | None = None,   # ②
               reward_terms: list[str] | None = None, # ③
               train_items=None, test_items=None,     # ④a-2
               seed_results: list[float] | None = None, # ⑤
               claimed_scope=None, tested_scope=None) -> list[Finding]: # ⑥
    """Run all 7 probes in a single call. Optional probes activate when args are provided."""
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
        print(f"🪞 No result file found for '{name}'. Make your evaluation write {name}.json.")
        print(f'   Expected format: {{"acc":0.72,"n":500,"metric":"acc","baseline":0.5}}')
        sys.exit(1)
    d = json.load(open(path, encoding="utf-8"))
    cid = d.get("claim_id", name)
    acc = d.get("acc")
    n = d.get("n")
    if acc is None or n is None:
        print(f"🪞 Error: {path} must contain 'acc' and 'n' keys.")
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

    r = sub.add_parser("register", help="Seal evaluation criteria BEFORE running the experiment")
    r.add_argument("claim_id")
    r.add_argument("--metric", required=True)
    r.add_argument("--min-n", type=int, default=200)
    r.add_argument("--baseline", type=float, default=0.5)
    r.add_argument("--pass", dest="pass_threshold", type=float, default=0.60)

    a = sub.add_parser("audit", help="Audit evaluation results (args or --file JSON)")
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
