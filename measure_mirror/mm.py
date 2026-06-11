"""
🪞 Measurement Mirror — MVP probe engine (no training, pure rule+stat).

7체크:
  ① 사전등록 원장 (append-only, 첫 등록 고정) + 사후 지표변경 적발 + 봉인 위변조 탐지
  ② 공정 baseline — crippled/동률/역전 적발
  ③ 게이밍 분계선 — reward에 지표 직접 포함 여부
  ④a 소표본 CI (Wilson) + 방향 + 데이터 누설 해시 교집합
  ⑤ 다시드 재현 — 시드 간 분산 경보
  ⑥ scope — 주장이 증거 범위 넘는 과대일반화
  ⑦ 자가 적발 — 너무 좋은 결과 이상값 경보

설계 원칙:
  - 학습 모델 아님. 결정론적. 의존성 0 (Python 표준 라이브러리만).
  - probe = 독립 함수. 새 체크 추가 쉬움.
  - 원장 = append-only(JSONL) + 첫 등록 고정 + 해시 봉인 = 정직성의 기술적 심장.
"""
from __future__ import annotations
import json, math, time, hashlib, os, statistics
from dataclasses import dataclass, asdict


# ─────────────────────────────────────────────────────────────
# 판정 결과
# ─────────────────────────────────────────────────────────────
@dataclass
class Finding:
    probe: str
    level: str   # OK / WARN / FAIL
    msg: str


# ─────────────────────────────────────────────────────────────
# ① 사전등록 원장 (append-only)
# ─────────────────────────────────────────────────────────────
def preregister(ledger_path: str, claim_id: str, *, metric: str,
                min_n: int, baseline: float, pass_threshold: float) -> dict:
    """결과 보기 *전* 기준을 박제. append-only. 해시로 봉인.

    같은 claim_id가 이미 등록돼 있어도 덮어쓰지 않는다 — audit에서 첫 등록만 유효.
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
    """첫 번째 등록만 반환. 나중 등록은 무시 — append-only 봉인 보장."""
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
                return e  # 첫 번째 등록 즉시 반환
    return None


def _verify_seal(entry: dict) -> bool:
    """등록 당시 해시를 재계산해 봉인 무결성 확인."""
    stored = entry.get("seal", "")
    check = {k: v for k, v in entry.items() if k != "seal"}
    expected = hashlib.sha256(
        json.dumps(check, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return stored == expected


# ─────────────────────────────────────────────────────────────
# ④a-1 소표본 신뢰구간 (Wilson score interval, 이항)
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
# ④a-2 데이터 누설 (train ∩ test 해시 교집합)
# ─────────────────────────────────────────────────────────────
def leakage_check(train_items, test_items) -> Finding:
    def H(xs):
        return {hashlib.sha256(str(x).encode()).hexdigest() for x in xs}
    th, eh = H(train_items), H(test_items)
    inter = th & eh
    if inter:
        frac = len(inter) / max(1, len(eh))
        return Finding("④a 데이터누설", "FAIL",
            f"train∩test = {len(inter)}건 ({frac:.1%} of test). **평가셋 오염.**")
    return Finding("④a 데이터누설", "OK", "train∩test = 0. 누설 없음.")


# ─────────────────────────────────────────────────────────────
# ② 공정 baseline
# ─────────────────────────────────────────────────────────────
def baseline_fairness(name: str, claimed: float, baseline: float, *,
                      higher_better: bool = True, margin: float = 0.01) -> Finding:
    diff = (claimed - baseline) if higher_better else (baseline - claimed)
    if diff <= -margin:
        return Finding("② 공정 baseline", "FAIL",
            f"{name}: 주장 {claimed:.3f} 이 baseline {baseline:.3f} *보다 나쁨*. "
            f"baseline 우수 — 주장 무효/게이밍.")
    if abs(diff) < margin:
        return Finding("② 공정 baseline", "FAIL",
            f"{name}: 주장 {claimed:.3f} ≈ baseline {baseline:.3f} (Δ{diff:+.3f} < {margin}). "
            f"**동률 — 고유 우위 없음.**")
    return Finding("② 공정 baseline", "OK",
        f"{name}: 주장 {claimed:.3f} 이 baseline {baseline:.3f} 능가 (Δ{diff:+.3f}).")


# ─────────────────────────────────────────────────────────────
# 공유 DB 조회
# ─────────────────────────────────────────────────────────────
def lookup_baseline(task: str | None, db_dir: str | None = None) -> float | None:
    """db/baselines.json 에서 과제 baseline 조회 — 없으면 None."""
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
# ③ 게이밍 분계선 — reward에 지표 직접 포함 여부
# ─────────────────────────────────────────────────────────────
def gaming_check(metric: str, reward_terms: list[str]) -> Finding:
    """③ reward/loss 구성에 평가 지표가 직접 들어있으면 자기충족 artifact 적발.

    reward_terms: 학습 loss/reward 식에 포함된 항목 이름 목록.
    """
    metric_lower = metric.lower()
    hits = [t for t in reward_terms if metric_lower in t.lower()]
    if hits:
        return Finding("③ 게이밍 분계선", "FAIL",
            f"평가 지표 '{metric}' 가 reward/loss 항목 {hits} 에 직접 포함. "
            f"**자기충족 artifact — 빼기/교체로만 정직한 신호.**")
    return Finding("③ 게이밍 분계선", "OK",
        f"평가 지표 '{metric}' 가 reward/loss에 미포함. 게이밍 없음.")


# ─────────────────────────────────────────────────────────────
# ⑤ 다시드 재현 — 시드 간 분산 경보
# ─────────────────────────────────────────────────────────────
def multiseed_check(seed_results: list[float], *, baseline: float = 0.5,
                    cv_threshold: float = 0.10) -> Finding:
    """⑤ 여러 시드 결과의 분산이 크면 신호가 불안정함을 경보.

    cv_threshold: 변동계수(std/mean) 기준. 기본 0.10 (10%).
    """
    if len(seed_results) < 2:
        return Finding("⑤ 다시드 재현", "WARN",
            f"시드 결과 {len(seed_results)}개 — 재현 확인 불가. 최소 2개 필요.")
    mean = statistics.mean(seed_results)
    std = statistics.stdev(seed_results)
    cv = std / mean if mean != 0 else float("inf")
    lo, hi = min(seed_results), max(seed_results)
    # baseline이 결과 범위에 걸치는지
    if lo <= baseline <= hi:
        return Finding("⑤ 다시드 재현", "FAIL",
            f"시드 범위 [{lo:.3f}, {hi:.3f}] 가 baseline({baseline}) 포함. "
            f"**결과가 시드에 따라 baseline 아래로 내려감 — 신호 불안정.**")
    if cv >= cv_threshold:
        return Finding("⑤ 다시드 재현", "WARN",
            f"변동계수 CV={cv:.2%} ≥ {cv_threshold:.0%}. "
            f"mean={mean:.3f}, std={std:.3f} — 시드 간 분산 큼.")
    return Finding("⑤ 다시드 재현", "OK",
        f"시드 {len(seed_results)}개: mean={mean:.3f}, std={std:.3f}, CV={cv:.2%}. 안정.")


# ─────────────────────────────────────────────────────────────
# ⑥ scope — 과대일반화 적발
# ─────────────────────────────────────────────────────────────
def scope_check(claimed_scope, tested_scope) -> Finding:
    """주장이 증거보다 넓은 범위를 일반화하면 과대해석으로 적발."""
    tested = set(tested_scope)
    untested = [c for c in claimed_scope if c not in tested]
    if untested:
        return Finding("⑥ scope", "FAIL",
            f"주장 범위 중 {untested} 는 미시험 (증거={list(tested_scope)}). "
            f"**과대일반화 — 시험된 범위로 한정해야.**")
    return Finding("⑥ scope", "OK",
        f"주장 범위 ⊆ 증거 범위 {list(tested_scope)}. 과대일반화 없음.")


# ─────────────────────────────────────────────────────────────
# ⑦ 자가 적발 — 너무 좋은 결과 이상값 경보
# ─────────────────────────────────────────────────────────────
def too_good_check(name: str, claimed: float, baseline: float, *,
                   suspicious_margin: float = 0.30) -> Finding:
    """⑦ baseline 대비 차이가 suspicious_margin 이상이면 선제 의심 경보."""
    diff = claimed - baseline
    if diff >= suspicious_margin:
        return Finding("⑦ 자가적발(이상값)", "WARN",
            f"{name}: claimed={claimed:.3f}, baseline={baseline:.3f}, "
            f"Δ={diff:+.3f} ≥ {suspicious_margin}. "
            f"**너무 좋은 결과 — 측정 결함·게이밍 먼저 의심.**")
    return Finding("⑦ 자가적발(이상값)", "OK",
        f"{name}: Δ={diff:+.3f} — 이상값 수준 아님.")


# ─────────────────────────────────────────────────────────────
# 이항 감사 (분류·정확도 지표)
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
            baseline, db_note = b, f"  ⟵ DB 자동조회(task={task})"
        else:
            baseline = 0.5
    if not (0.0 <= reported_acc <= 1.0):
        findings.append(Finding("④a acc 범위", "FAIL",
            f"reported_acc={reported_acc:.3f} 는 0.0과 1.0 사이여야 합니다."))
        return findings
    if n < 0:
        findings.append(Finding("④a n 범위", "FAIL",
            f"n={n} 은 0 이상이어야 합니다."))
        return findings

    k = round(reported_acc * n)
    lo, hi = wilson_ci(k, n)

    # ④a-1 소표본 + 방향
    if lo <= baseline <= hi:
        findings.append(Finding(
            "④a 소표본 CI", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → 95%CI [{lo:.3f}, {hi:.3f}] "
            f"⊃ baseline({baseline}).{db_note} **chance와 통계적으로 구별 불가.**"))
    elif hi < baseline:
        findings.append(Finding(
            "④a 방향(anti-signal)", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"< baseline({baseline}). **chance보다 *나쁨* — anti-signal/투영붕괴 의심.**"))
    else:
        findings.append(Finding(
            "④a 소표본 CI", "OK",
            f"n={n}, acc={reported_acc:.3f} → CI [{lo:.3f}, {hi:.3f}] "
            f"baseline({baseline}) *초과* 배제."))

    # ① 사전등록 대조
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding(
            "① 사전등록", "WARN",
            f"claim_id='{claim_id}' 사전등록 없음 — 사후 정의된 지표일 위험."))
    else:
        # 봉인 위변조 탐지
        if not _verify_seal(pre):
            findings.append(Finding(
                "① 봉인 위변조", "FAIL",
                f"claim_id='{claim_id}' 원장 봉인 불일치. "
                f"**원장 파일이 변조됐을 수 있음 — 사전등록 무효.**"))
        else:
            if n < pre["min_n"]:
                findings.append(Finding(
                    "① 사전등록(min_n)", "FAIL",
                    f"보고 n={n} < 등록 min_n={pre['min_n']}. 표본 미달."))
            if reported_metric != pre["metric"]:
                findings.append(Finding(
                    "① 사전등록(지표변경)", "FAIL",
                    f"보고 지표 '{reported_metric}' ≠ 등록 지표 '{pre['metric']}'. "
                    f"**사후 지표 갈아타기.** (seal={pre['seal']})"))
            if reported_acc < pre["pass_threshold"]:
                findings.append(Finding(
                    "① 사전등록(pass_threshold)", "FAIL",
                    f"acc={reported_acc:.3f} < 등록 pass_threshold={pre['pass_threshold']:.3f}. "
                    f"**기준 미달.** (seal={pre['seal']})"))

    return findings


# ─────────────────────────────────────────────────────────────
# 연속 지표 감사 (회귀·상관 등)
# ─────────────────────────────────────────────────────────────
def continuous_audit(ledger_path: str, claim_id: str, *,
                     reported_metric: str, reported_value: float,
                     baseline_value: float, n: int,
                     std: float | None = None,
                     higher_better: bool = True) -> list[Finding]:
    """회귀·연속 지표용 감사 (Pearson r, MSE, RMSE 등).

    Wilson CI 대신 방향 + 효과크기(std 제공 시) + 사전등록 체크.
    """
    findings: list[Finding] = []

    # ④a 방향
    diff = (reported_value - baseline_value) if higher_better else (baseline_value - reported_value)
    if diff <= 0:
        symbol = "≤" if higher_better else "≥"
        findings.append(Finding("④a 방향", "FAIL",
            f"값={reported_value:.4f} {symbol} baseline={baseline_value:.4f}. "
            f"baseline 우수 — 주장 무효."))
    else:
        findings.append(Finding("④a 방향", "OK",
            f"Δ={diff:+.4f} — {'높을수록' if higher_better else '낮을수록'} 좋음 기준 통과."))

    # ④a 효과크기 (std 있을 때만)
    if std is not None and std > 0:
        z = abs(reported_value - baseline_value) / std
        if z < 1.0:
            findings.append(Finding("④a 효과크기", "WARN",
                f"z={z:.2f} < 1.0 — 실용적 유의성 약함 (n={n})."))
        else:
            findings.append(Finding("④a 효과크기", "OK",
                f"z={z:.2f} ≥ 1.0 — 실용적 유의성 있음."))

    # ① 사전등록
    pre = _load_prereg(ledger_path, claim_id)
    if pre is None:
        findings.append(Finding("① 사전등록", "WARN",
            f"claim_id='{claim_id}' 사전등록 없음."))
    else:
        if not _verify_seal(pre):
            findings.append(Finding("① 봉인 위변조", "FAIL",
                f"claim_id='{claim_id}' 원장 봉인 불일치."))
        else:
            if reported_metric != pre["metric"]:
                findings.append(Finding("① 사전등록(지표변경)", "FAIL",
                    f"보고 지표 '{reported_metric}' ≠ 등록 지표 '{pre['metric']}'. "
                    f"사후 지표 갈아타기. (seal={pre['seal']})"))
            if n < pre["min_n"]:
                findings.append(Finding("① 사전등록(min_n)", "FAIL",
                    f"n={n} < 등록 min_n={pre['min_n']}."))

    return findings


# ─────────────────────────────────────────────────────────────
# 통합 감사 (7체크 한 번에)
# ─────────────────────────────────────────────────────────────
def full_audit(ledger_path: str, claim_id: str, *,
               reported_metric: str, reported_acc: float, n: int,
               baseline: float | None = None, task: str | None = None,
               db_dir: str | None = None,
               # ② 경쟁 baseline
               competing_name: str | None = None,
               competing_acc: float | None = None,
               # ③ 게이밍
               reward_terms: list[str] | None = None,
               # ④a-2 누설
               train_items=None, test_items=None,
               # ⑤ 다시드
               seed_results: list[float] | None = None,
               # ⑥ scope
               claimed_scope=None, tested_scope=None) -> list[Finding]:
    """7체크 전체를 한 번에 실행하는 통합 감사."""
    # baseline 결정 (이후 probes에서 재사용)
    _baseline = baseline
    if _baseline is None:
        b = lookup_baseline(task, db_dir)
        _baseline = b if b is not None else 0.5

    findings: list[Finding] = []

    # ① + ④a-1 (기본 audit)
    findings.extend(audit(ledger_path, claim_id,
                          reported_metric=reported_metric,
                          reported_acc=reported_acc, n=n,
                          baseline=_baseline, task=task, db_dir=db_dir))

    # ② 경쟁 baseline
    if competing_name is not None and competing_acc is not None:
        findings.append(baseline_fairness(competing_name, reported_acc, competing_acc))

    # ③ 게이밍
    if reward_terms is not None:
        findings.append(gaming_check(reported_metric, reward_terms))

    # ④a-2 누설
    if train_items is not None and test_items is not None:
        findings.append(leakage_check(train_items, test_items))

    # ⑤ 다시드
    if seed_results is not None:
        findings.append(multiseed_check(seed_results, baseline=_baseline))

    # ⑥ scope
    if claimed_scope is not None and tested_scope is not None:
        findings.append(scope_check(claimed_scope, tested_scope))

    # ⑦ 자가 적발 (항상)
    findings.append(too_good_check(claim_id, reported_acc, _baseline))

    return findings


# ─────────────────────────────────────────────────────────────
# 판정 리포트
# ─────────────────────────────────────────────────────────────
def report(title: str, findings: list[Finding]) -> None:
    icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "🔴"}
    worst = "FAIL" if any(f.level == "FAIL" for f in findings) else \
            "WARN" if any(f.level == "WARN" for f in findings) else "OK"
    print(f"\n🪞 측정거울 감사: {title}")
    print(f"   종합: {icon[worst]} {worst}")
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
        print(f"🪞 '{name}' 결과 파일 없음. 평가가 {name}.json 을 뱉게 하세요.")
        print(f'   기대 형식: {{"acc":0.72,"n":500,"metric":"acc","baseline":0.5}}')
        sys.exit(1)
    d = json.load(open(path, encoding="utf-8"))
    cid = d.get("claim_id", name)
    acc = d.get("acc")
    n = d.get("n")
    if acc is None or n is None:
        print(f"🪞 에러: {path} 파일 내에 'acc' 와 'n' 키가 필요합니다.")
        sys.exit(1)
    print(f"📂 {path} 자동 로드")
    report(cid, audit(ledger, cid, reported_metric=d.get("metric", "acc"),
                      reported_acc=acc, n=n, baseline=d.get("baseline", 0.5)))


def _cli() -> None:
    import argparse, sys
    if len(sys.argv) == 2 and sys.argv[1] not in {"register", "audit"} \
            and not sys.argv[1].startswith("-"):
        _auto(sys.argv[1]); return
    p = argparse.ArgumentParser(prog="mm", description="🪞 측정거울 — 평가 주장 자동 감사")
    p.add_argument("--ledger", default="mm_ledger.jsonl", help="원장 경로(기본 ./mm_ledger.jsonl)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("register", help="실험 *전* 기준 박제")
    r.add_argument("claim_id")
    r.add_argument("--metric", required=True)
    r.add_argument("--min-n", type=int, default=200)
    r.add_argument("--baseline", type=float, default=0.5)
    r.add_argument("--pass", dest="pass_threshold", type=float, default=0.60)

    a = sub.add_parser("audit", help="평가 결과 감사 (인자 또는 --file JSON)")
    a.add_argument("claim_id", nargs="?")
    a.add_argument("--acc", type=float)
    a.add_argument("--n", type=int)
    a.add_argument("--metric", default="acc")
    a.add_argument("--baseline", type=float, default=0.5)
    a.add_argument("--file", help="결과 JSON: {claim_id,metric,acc,n,baseline}")

    args = p.parse_args()
    if args.cmd == "register":
        e = preregister(args.ledger, args.claim_id, metric=args.metric,
                        min_n=args.min_n, baseline=args.baseline,
                        pass_threshold=args.pass_threshold)
        print(f"🔒 봉인: {args.claim_id}  metric={args.metric} "
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
            p.error("audit: --acc 와 --n (또는 --file) 필요")
        report(cid, audit(args.ledger, cid, reported_metric=metric,
                          reported_acc=acc, n=n, baseline=baseline))


if __name__ == "__main__":
    _cli()
