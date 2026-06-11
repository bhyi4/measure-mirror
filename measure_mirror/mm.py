"""
🪞 Measurement Mirror — probe engine (no training, pure rule+stat).

12 probes:
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
  ⑩ GRIM — arithmetic consistency (acc × n must be a whole-number count)
  ⑪ Falsifiability — Popper gate (kill-condition registered? triggered?)
  ⑫ Retraction cascade — claim or transitive dependency retracted?
  ⑬ Negative-claim audit — angle-count gate + scope for Resolved-Negative closures

Utilities:
  calibrate() — self-test: run 5 synthetic known-good/known-bad cases
  anchor()    — tamper-evident ledger snapshot for external archival
  witness()   — execute a command and seal a tamper-evident run record
  retract()   — append a chain-linked retraction entry to the ledger

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
                min_n: int, baseline: float, pass_threshold: float,
                kill_condition: str | None = None,
                kill_threshold: dict | None = None,
                depends_on: list[str] | None = None) -> dict:
    """Seal evaluation criteria BEFORE seeing results.

    Each entry is cryptographically linked to the previous one (chain hash).
    Re-registration for the same claim_id is silently ignored — only the
    first registration counts in audit().

    kill_condition: human-readable description of what would falsify the claim,
        e.g. "accuracy drops below 0.55 on held-out test".
    kill_threshold: structured auto-evaluable form:
        {"metric": "acc", "threshold": 0.55, "direction": "below"}
        direction "below": FAIL when reported_acc < threshold.
        direction "above": FAIL when reported_acc > threshold (error metrics).
        Both can be provided together. Claims with neither are flagged
        "unfalsifiable" by falsifiability_check() at audit time.
    depends_on: list of claim_ids this claim builds on. If any of those claims
        is later retracted, this claim is flagged STALE by cascade_check().

    Chain link: deleting or inserting entries breaks the chain and is
    detected by verify_chain(). Complete ledger replacement is NOT caught
    here — use git commit anchoring for that guarantee.
    """
    prev_seal = _get_last_seal(ledger_path)
    entry: dict = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "claim_id": claim_id,
        "metric": metric,
        "min_n": min_n,
        "baseline": baseline,
        "pass_threshold": pass_threshold,
        "prev_seal": prev_seal,
    }
    if kill_condition is not None:
        entry["kill_condition"] = kill_condition
    if kill_threshold is not None:
        entry["kill_threshold"] = kill_threshold
    if depends_on:
        entry["depends_on"] = depends_on
    entry["seal"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _load_prereg(ledger_path: str, claim_id: str) -> dict | None:
    """Return the FIRST preregister entry for claim_id (skips witness/anchor entries)."""
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
            # Only preregister entries — witness/anchor have explicit _type
            if e.get("claim_id") == claim_id and "_type" not in e:
                return e
    return None


def _falsifiability_eval(pre: dict, reported_acc: float | None) -> Finding:
    """Internal: evaluate kill-condition from an already-loaded pre-registration entry."""
    kill_cond  = pre.get("kill_condition")
    kill_thresh = pre.get("kill_threshold")

    if kill_cond is None and kill_thresh is None:
        return Finding("⑪ falsifiability", "WARN",
                       f"Unfalsifiable: '{pre['claim_id']}' has no kill-condition. "
                       "Add kill_condition= or kill_threshold= to preregister().")

    if kill_thresh is not None:
        if reported_acc is None:
            return Finding("⑪ falsifiability", "WARN",
                           "Kill threshold registered but result not yet provided "
                           "— cannot evaluate kill condition.")
        metric    = kill_thresh.get("metric", pre.get("metric", "?"))
        thr       = float(kill_thresh["threshold"])
        direction = kill_thresh.get("direction", "below")
        triggered = (
            (direction == "below" and reported_acc < thr) or
            (direction == "above" and reported_acc > thr)
        )
        text = f" [{kill_cond}]" if kill_cond else ""
        if triggered:
            op = "<" if direction == "below" else ">"
            return Finding("⑪ falsifiability", "FAIL",
                           f"Kill condition triggered{text}: "
                           f"{metric}={reported_acc} {op} {thr}. "
                           f"Claim '{pre['claim_id']}' is falsified by its own "
                           "pre-registered criterion.")
        op = "≥" if direction == "below" else "≤"
        return Finding("⑪ falsifiability", "OK",
                       f"Kill condition not triggered{text}: "
                       f"{metric}={reported_acc} {op} {thr}.")

    # kill_condition text-only (no structured threshold)
    return Finding("⑪ falsifiability", "OK",
                   f"Falsifiable (text-only): '{kill_cond}'. "
                   "Add kill_threshold= for automatic evaluation.")


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
# ⑩ GRIM — arithmetic consistency check
# ─────────────────────────────────────────────────────────────
def _infer_decimals(x: float) -> int:
    """Infer reported decimal places from Python's float repr (strips trailing zeros)."""
    s = str(x)
    if "." in s:
        frac = s.split(".")[1].rstrip("0")
        return len(frac) if frac else 0
    return 0


def grim_check(reported_acc: float, n: int, *,
               n_decimals: int | None = None) -> Finding:
    """⑩ GRIM test: verify that acc × n is arithmetically possible.

    For a proportion reported as k/n (then rounded to d decimal places),
    there must exist an integer k such that round(k/n, d) == reported_acc.
    If no such k exists, the number was fabricated or n was mis-reported.

    Current audit() silently does round(acc × n) and hides this signal —
    this probe makes it explicit.

    n_decimals: decimal places in the reported value. Auto-detected from the
    float if not provided (works for typical reporting like 0.72, 0.715).
    """
    if n <= 0:
        return Finding("⑩ GRIM", "WARN", f"n={n} ≤ 0 — cannot run GRIM check.")

    d = n_decimals if n_decimals is not None else _infer_decimals(reported_acc)
    d = max(d, 1)  # at minimum 1 decimal place

    k_lo = math.floor(reported_acc * n)
    k_hi = k_lo + 1
    target = round(reported_acc, d)

    for k in (k_lo, k_hi):
        if 0 <= k <= n and round(k / n, d) == target:
            return Finding("⑩ GRIM", "OK",
                f"acc={reported_acc} consistent with n={n} "
                f"(k={k}, {k}/{n}={k/n:.{d+2}f} → {round(k/n, d)}).")

    return Finding("⑩ GRIM", "FAIL",
        f"acc={reported_acc} is arithmetically impossible for n={n}. "
        f"No integer k satisfies round(k/{n}, {d}) = {target}. "
        f"(candidates: k={k_lo} → {round(k_lo/n, d)}, "
        f"k={k_hi} → {round(k_hi/n, d)}). "
        f"Fabricated value or mis-reported n.")


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
# ⑪ Falsifiability — Popper gate
# ─────────────────────────────────────────────────────────────
def falsifiability_check(ledger_path: str, claim_id: str, *,
                          reported_acc: float | None = None) -> Finding:
    """⑪ Popper gate: verify a kill-condition was registered; auto-evaluate it.

    Checks the pre-registration for kill_condition / kill_threshold.

    Levels:
      FAIL — kill_threshold is registered AND reported_acc triggers it
             (the claim falsified itself by its own pre-registered criterion)
      WARN — no kill-condition at all (unfalsifiable), or kill_threshold
             registered but reported_acc not yet provided
      OK   — kill threshold not triggered, or text-only condition registered

    Call standalone before publishing, or it runs automatically inside audit().
    """
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        return Finding("⑪ falsifiability", "WARN",
                       f"No pre-registration for '{claim_id}' — "
                       "kill-condition unknown.")
    return _falsifiability_eval(pre, reported_acc)


# ─────────────────────────────────────────────────────────────
# ⑫ Retraction cascade
# ─────────────────────────────────────────────────────────────
def _load_dependency_graph(ledger_path: str) -> tuple[dict[str, list[str]], set[str]]:
    """Return (deps, retracted) by scanning the entire ledger.

    deps:      claim_id → list of claim_ids it depends on (from first preregister)
    retracted: set of claim_ids that have at least one retraction entry
    """
    deps: dict[str, list[str]] = {}
    retracted: set[str] = set()

    if not os.path.exists(ledger_path):
        return deps, retracted

    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = e.get("claim_id")
            if not cid:
                continue
            if e.get("_type") == "retraction":
                retracted.add(cid)
            elif "_type" not in e:
                # preregister entry — record first occurrence only (first-write wins)
                if cid not in deps:
                    do = e.get("depends_on")
                    deps[cid] = do if isinstance(do, list) else []

    return deps, retracted


def retract(ledger_path: str, claim_id: str, reason: str) -> dict:
    """Append a chain-linked retraction entry to the ledger.

    Marks claim_id as retracted. Any claim that depends (directly or transitively)
    on a retracted claim will be flagged STALE by cascade_check(). Every call
    appends a new entry; the entry is chain-linked via prev_seal so retraction
    records cannot be silently deleted from the ledger.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    entry: dict = {
        "_type":    "retraction",
        "ts":       ts,
        "claim_id": claim_id,
        "reason":   reason,
    }
    prev_seal = _get_last_seal(ledger_path)
    entry["prev_seal"] = prev_seal
    entry["seal"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def cascade_check(ledger_path: str, claim_id: str) -> Finding:
    """⑫ Retraction cascade: check if claim or any transitive dependency was retracted.

    Levels:
      FAIL — claim_id itself has a retraction entry in the ledger
      WARN — claim is STALE: a transitive dependency has been retracted
      OK   — no retraction risk found

    Policy: retraction propagates regardless of publication order. A claim
    built on a retracted foundation is automatically stale.
    Call standalone, or it runs automatically inside audit() (WARN/FAIL only).
    """
    deps, retracted = _load_dependency_graph(ledger_path)

    if claim_id in retracted:
        return Finding("⑫ retraction-cascade", "FAIL",
                       f"Claim '{claim_id}' has been retracted.")

    # BFS over dependency graph to find stale transitive dependencies
    visited: set[str] = set()
    queue: list[str] = list(deps.get(claim_id, []))
    stale: list[str] = []

    while queue:
        dep = queue.pop(0)
        if dep in visited:
            continue
        visited.add(dep)
        if dep in retracted:
            stale.append(dep)
        else:
            queue.extend(d for d in deps.get(dep, []) if d not in visited)

    if stale:
        return Finding("⑫ retraction-cascade", "WARN",
                       f"Claim '{claim_id}' is STALE: depends (transitively) on "
                       "retracted claim(s): "
                       + ", ".join(f"'{s}'" for s in stale))

    return Finding("⑫ retraction-cascade", "OK",
                   f"No retraction risk for '{claim_id}'.")


# ─────────────────────────────────────────────────────────────
# ⑬ Negative-claim audit — angle-count gate
# ─────────────────────────────────────────────────────────────
def negative_audit(ledger_path: str, *,
                   angles: list[str],
                   min_angles: int = 3,
                   conclusion_scope: list[str] | None = None,
                   tested_scope: list[str] | None = None) -> Finding:
    """⑬ Gate a Resolved-Negative conclusion: angle-count + optional scope check.

    A negative conclusion ("X does not work") is only trustworthy when multiple
    independent pre-registered experiments have all converged on the same result.
    Too few angles = premature closure (single failure may reflect a frame flaw,
    not a universal wall).

    Checks (in priority order):
      1. len(angles) >= min_angles (default 3) — angle-count gate
      2. Each angle has a preregister entry in the ledger — unregistered angles
         cannot be trusted as independent evidence
      3. No angle is retracted (WARN — weakened case, not outright FAIL)
      4. If conclusion_scope and tested_scope provided:
         conclusion must not be broader than tested scope (FAIL if over-claimed)

    Levels:
      FAIL — fewer angles than min_angles, unregistered angle(s), or scope overshoot
      WARN — all FAIL checks pass but at least one angle is retracted
      OK   — all checks pass
    """
    fails: list[str] = []
    warns: list[str] = []

    # Check 1: angle-count gate
    if len(angles) < min_angles:
        fails.append(
            f"only {len(angles)} angle(s) provided (need ≥{min_angles}) — "
            "premature closure risk")

    # Check 2+3: load ledger once for registration + retraction status
    deps, retracted_set = _load_dependency_graph(ledger_path)
    unregistered = [a for a in angles if a not in deps]
    if unregistered:
        fails.append(
            "unregistered angle(s): "
            + ", ".join(f"'{u}'" for u in unregistered))

    retracted_angles = [a for a in angles if a in retracted_set]
    if retracted_angles:
        warns.append(
            "retracted angle(s) weaken the case: "
            + ", ".join(f"'{r}'" for r in retracted_angles))

    # Check 4: scope (optional)
    if conclusion_scope is not None and tested_scope is not None:
        over = [s for s in conclusion_scope if s not in tested_scope]
        if over:
            fails.append(
                "conclusion scope includes untested domain(s): "
                + str(over))

    if fails:
        return Finding("⑬ negative-audit", "FAIL", "; ".join(fails) + ".")
    if warns:
        return Finding("⑬ negative-audit", "WARN", "; ".join(warns) + ".")
    n = len(angles)
    return Finding("⑬ negative-audit", "OK",
                   f"{n}/{n} independent pre-registered angle(s) verified — "
                   "negative conclusion is supported.")


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

    # ⑩ GRIM — runs before CI; only appended when FAIL to keep OK output clean
    grim = grim_check(reported_acc, n)
    if grim.level != "OK":
        findings.append(grim)

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
            # ⑪ falsifiability — only when seal is valid (no double-load)
            findings.append(_falsifiability_eval(pre, reported_acc))

    # ⑫ cascade — retraction check (runs regardless of pre-registration)
    casc = cascade_check(ledger_path, claim_id)
    if casc.level != "OK":
        findings.append(casc)

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
               check_multiplicity: bool = False,           # ⑨
               angles: list[str] | None = None,            # ⑬
               min_angles: int = 3) -> list[Finding]:      # ⑬
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
    # ⑬ negative audit (optional)
    if angles is not None:
        findings.append(negative_audit(ledger_path, angles=angles,
                                       min_angles=min_angles))

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
# ⚙ Calibration + Witness run
# ─────────────────────────────────────────────────────────────
def calibrate() -> list[Finding]:
    """Self-test: run synthetic known-good/known-bad cases through key probes.

    Returns [OK] when all 5 cases produce expected outcomes — confirms the
    mirror itself has no regressions.  Returns [FAIL] if any case breaks.
    Run before witness() or in CI to confirm the tool is working correctly.
    """
    errors: list[str] = []

    # Case 1: tiny sample must trigger small-sample FAIL
    f = audit("/dev/null", "_calibrate",
              reported_metric="acc", reported_acc=0.556, n=9)
    if not any(x.level == "FAIL" for x in f):
        errors.append("n=9 small-sample probe should FAIL")

    # Case 2: honest large sample must not FAIL
    f = audit("/dev/null", "_calibrate",
              reported_metric="acc", reported_acc=0.78, n=1000)
    if any(x.level == "FAIL" for x in f):
        errors.append("n=1000 honest result should not produce FAIL")

    # Case 3: GRIM-impossible value must FAIL
    g = grim_check(0.33, 10)
    if g.level != "FAIL":
        errors.append("GRIM(0.33, n=10) should be FAIL")

    # Case 4: GRIM-possible value must be OK
    g = grim_check(0.70, 10)
    if g.level != "OK":
        errors.append("GRIM(0.70, n=10) should be OK")

    # Case 5: baseline inversion must FAIL
    b = baseline_fairness("competitor", 0.60, 0.80)
    if b.level != "FAIL":
        errors.append("Inverted baseline (our=0.60 < competitor=0.80) should FAIL")

    if errors:
        return [Finding("⚙ calibrate", "FAIL",
                        "Mirror is miscalibrated: " + "; ".join(errors))]
    return [Finding("⚙ calibrate", "OK",
                    "5/5 synthetic cases correct — mirror is calibrated.")]


def anchor(ledger_path: str) -> dict:
    """Compute a tamper-evident snapshot of the ledger's current state.

    Outputs a compact dict suitable for piping to any external storage:
      ts:           ISO timestamp
      entry_count:  number of entries currently in the ledger
      head_seal:    seal of the last entry ('empty' if ledger is missing/empty)
      anchor_hash:  SHA-256 of the entire ledger file bytes — changes on any
                    modification (add, edit, delete, replace)
      chain_ok:     True if verify_chain() found no failures

    This is the recommended defence against complete ledger replacement, which
    chain hashes alone cannot detect.  Pipe to wherever you trust:

        mm anchor >> ~/Dropbox/mm_anchors.jsonl
        mm anchor | gh gist create -
        mm anchor | aws s3 cp - s3://bucket/mm_anchor.json

    The receiver has an independent timestamp proof of what the ledger contained.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not os.path.exists(ledger_path):
        return {
            "_type":        "anchor",
            "ts":           ts,
            "ledger_path":  ledger_path,
            "entry_count":  0,
            "head_seal":    "empty",
            "anchor_hash":  "empty",
            "chain_ok":     True,
        }

    with open(ledger_path, "rb") as f:
        raw = f.read()

    anchor_hash = hashlib.sha256(raw).hexdigest()
    entry_count = sum(
        1 for line in raw.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    )
    head_seal = _get_last_seal(ledger_path)
    chain_ok = not any(
        f.level == "FAIL" for f in verify_chain(ledger_path)
    )
    return {
        "_type":        "anchor",
        "ts":           ts,
        "ledger_path":  ledger_path,
        "entry_count":  entry_count,
        "head_seal":    head_seal,
        "anchor_hash":  anchor_hash,
        "chain_ok":     chain_ok,
    }


def witness(ledger_path: str, claim_id: str, command: list[str], *,
            timeout: int | None = None) -> dict:
    """Execute command and seal a tamper-evident witness record in the ledger.

    Runs the command as a subprocess, captures stdout/stderr/returncode, hashes
    the output, and appends a chain-linked entry (with _type='witness') to the
    ledger file.  The sealed record proves: which command ran, when, and what
    it produced — output_hash changes if anything in stdout/stderr/returncode
    changes.

    Returns the witness entry dict (keys: seal, output_hash, returncode, …).
    Does NOT silently ignore re-runs — every call appends a new entry.
    """
    import subprocess

    ts_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=timeout)
        stdout, stderr = proc.stdout, proc.stderr
        returncode = proc.returncode
        run_status = "ok"
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") \
                 if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") \
                 if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        returncode, run_status = -1, "timeout"
    except Exception as exc:
        stdout, stderr = "", str(exc)
        returncode, run_status = -1, "error"

    ts_end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output_hash = hashlib.sha256(
        f"{returncode}\n{stdout}\n{stderr}".encode()
    ).hexdigest()[:16]

    entry: dict = {
        "_type":       "witness",
        "ts_start":    ts_start,
        "ts_end":      ts_end,
        "claim_id":    claim_id,
        "command":     command,
        "returncode":  returncode,
        "run_status":  run_status,
        "output_hash": output_hash,
    }
    prev_seal = _get_last_seal(ledger_path)
    entry["prev_seal"] = prev_seal
    entry["seal"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


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
    _SUBCMDS = {"register", "audit", "calibrate", "run", "anchor", "retract", "negative"}
    if len(sys.argv) == 2 and sys.argv[1] not in _SUBCMDS \
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
    r.add_argument("--kill", dest="kill_condition", default=None,
                   help='Human-readable kill condition, e.g. "acc < 0.55 on held-out"')
    r.add_argument("--kill-threshold", type=float, default=None,
                   help="Numeric kill threshold for automatic evaluation")
    r.add_argument("--kill-direction", choices=["below", "above"], default="below",
                   help="Fail when reported value is below/above threshold (default: below)")
    r.add_argument("--depends-on", dest="depends_on", nargs="+", default=None,
                   help="Claim IDs this claim depends on (space-separated)")

    a = sub.add_parser("audit", help="Audit evaluation results")
    a.add_argument("claim_id", nargs="?")
    a.add_argument("--acc", type=float)
    a.add_argument("--n", type=int)
    a.add_argument("--metric", default="acc")
    a.add_argument("--baseline", type=float, default=0.5)
    a.add_argument("--file", help="Result JSON: {claim_id, metric, acc, n, baseline}")

    sub.add_parser("calibrate",
                   help="Self-test: verify the mirror's probes return expected outcomes")

    an = sub.add_parser("anchor",
                        help="Print tamper-evident ledger snapshot to stdout for external archival")
    an.add_argument("--pretty", action="store_true",
                    help="Pretty-print JSON (default: compact single line for piping)")

    rt = sub.add_parser("retract",
                        help="Retract a claim; cascades STALE to all dependent claims")
    rt.add_argument("claim_id", help="Claim ID to retract")
    rt.add_argument("--reason", required=True,
                    help="Reason for retraction (e.g. 'data labelling error discovered')")

    ng = sub.add_parser("negative",
                        help="Gate a Resolved-Negative conclusion: angle-count + scope check")
    ng.add_argument("--angles", nargs="+", required=True,
                    help="Claim IDs of independent test angles (space-separated)")
    ng.add_argument("--min-angles", type=int, default=3,
                    help="Minimum required angles (default: 3)")

    rn = sub.add_parser("run",
                        help="Calibrate + witness-execute a command, sealing the run record")
    rn.add_argument("claim_id", help="Experiment / claim identifier")
    rn.add_argument("command", nargs=argparse.REMAINDER,
                    help="Command to execute (prefix with -- to separate mm flags)")
    rn.add_argument("--timeout", type=int, default=None,
                    help="Subprocess timeout in seconds (default: none)")
    rn.add_argument("--no-calibrate", dest="no_calibrate", action="store_true",
                    help="Skip self-calibration before running the command")

    args = p.parse_args()
    if args.cmd == "register":
        kill_thresh = None
        if args.kill_threshold is not None:
            kill_thresh = {
                "metric": args.metric,
                "threshold": args.kill_threshold,
                "direction": args.kill_direction,
            }
        e = preregister(args.ledger, args.claim_id, metric=args.metric,
                        min_n=args.min_n, baseline=args.baseline,
                        pass_threshold=args.pass_threshold,
                        kill_condition=args.kill_condition,
                        kill_threshold=kill_thresh,
                        depends_on=args.depends_on)
        kill_note = ""
        if kill_thresh:
            op = "<" if args.kill_direction == "below" else ">"
            kill_note = (f"  kill={args.metric} {op} {args.kill_threshold}")
        elif args.kill_condition:
            kill_note = f"  kill(text)={args.kill_condition!r}"
        print(f"🔒 Sealed: {args.claim_id}  metric={args.metric} "
              f"min_n={args.min_n} baseline={args.baseline}{kill_note}  seal={e['seal']}")
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
    elif args.cmd == "calibrate":
        report("Mirror Calibration", calibrate())
    elif args.cmd == "anchor":
        a = anchor(args.ledger)
        if args.pretty:
            print(json.dumps(a, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(a, ensure_ascii=False))
    elif args.cmd == "retract":
        e = retract(args.ledger, args.claim_id, args.reason)
        print(f"🚫 Retracted: {args.claim_id}  reason={args.reason!r}  seal={e['seal']}")
    elif args.cmd == "negative":
        report("Negative-claim audit",
               [negative_audit(args.ledger, angles=args.angles,
                               min_angles=args.min_angles)])
    elif args.cmd == "run":
        cmd = [c for c in (args.command or []) if c != "--"]
        if not cmd:
            p.error("run requires a command: mm run <claim_id> [--] <command...>")
        if not args.no_calibrate:
            cal = calibrate()
            report("Self-calibration", cal)
            if any(f.level == "FAIL" for f in cal):
                print("⚠️  Calibration failed — "
                      "witness run continues but verify your installation.")
        w = witness(args.ledger, args.claim_id, cmd, timeout=args.timeout)
        print(f"\n🎬 Witnessed: {args.claim_id}")
        print(f"   Command:     {' '.join(w['command'])}")
        print(f"   Started:     {w['ts_start']}")
        print(f"   Ended:       {w['ts_end']}")
        print(f"   Exit code:   {w['returncode']}  ({w['run_status']})")
        print(f"   Output hash: {w['output_hash']}")
        print(f"   Prev seal:   {w['prev_seal']}")
        print(f"   Seal:        {w['seal']}")


if __name__ == "__main__":
    _cli()
