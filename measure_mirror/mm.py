"""
🪞 Measurement Mirror — MVP probe engine (no training, pure rule+stat).

7체크 중 MVP 3개:
  ① 사전등록 원장 (append-only) + 사후 지표변경 적발
  ④a-1 소표본 신뢰구간 (Wilson) — chance와 구별 가능한가
  ④a-2 (누설 해시는 다음 단계)

설계 원칙:
  - 학습 모델 아님. 결정론적. 場처럼 붕괴 없음.
  - probe = 독립 함수. 새 체크 추가 쉬움.
  - 원장 = append-only(JSONL) = 정직성의 기술적 심장.
"""
from __future__ import annotations
import json, math, time, hashlib, os
from dataclasses import dataclass, asdict


# ─────────────────────────────────────────────────────────────
# ① 사전등록 원장 (append-only)
# ─────────────────────────────────────────────────────────────
def preregister(ledger_path: str, claim_id: str, *, metric: str,
                min_n: int, baseline: float, pass_threshold: float) -> dict:
    """결과 보기 *전* 기준을 박제. append-only. 해시로 봉인."""
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
    if not os.path.exists(ledger_path):
        return None
    hit = None
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e.get("claim_id") == claim_id:
                hit = e  # 마지막(최신) 등록
    return hit


# ─────────────────────────────────────────────────────────────
# ④a-1 소표본 신뢰구간 (Wilson score interval, 이항)
# ─────────────────────────────────────────────────────────────
def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# ─────────────────────────────────────────────────────────────
# ④a-2 데이터 누설 (train ∩ test 해시 교집합)
# ─────────────────────────────────────────────────────────────
def leakage_check(train_items, test_items) -> "Finding":
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
# ② 공정 baseline (場·swarm·후보5처럼 baseline이 핵심인 사례)
# ─────────────────────────────────────────────────────────────
def baseline_fairness(name: str, claimed: float, baseline: float, *,
                      higher_better: bool = True, margin: float = 0.01) -> "Finding":
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
# 판정 리포트
# ─────────────────────────────────────────────────────────────
@dataclass
class Finding:
    probe: str
    level: str          # OK / WARN / FAIL
    msg: str


def audit(ledger_path: str, claim_id: str, *,
          reported_metric: str, reported_acc: float, n: int,
          baseline: float = 0.5) -> list[Finding]:
    findings: list[Finding] = []
    k = round(reported_acc * n)
    lo, hi = wilson_ci(k, n)

    # ④a-1 소표본 + 방향: CI와 baseline 위치 관계 (3-way)
    if lo <= baseline <= hi:
        findings.append(Finding(
            "④a 소표본 CI", "FAIL",
            f"n={n}, acc={reported_acc:.3f} → 95%CI [{lo:.3f}, {hi:.3f}] "
            f"⊃ baseline({baseline}). **chance와 통계적으로 구별 불가.**"))
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
        if n < pre["min_n"]:
            findings.append(Finding(
                "① 사전등록(min_n)", "FAIL",
                f"보고 n={n} < 등록 min_n={pre['min_n']}. 표본 미달."))
        if reported_metric != pre["metric"]:
            findings.append(Finding(
                "① 사전등록(지표변경)", "FAIL",
                f"보고 지표 '{reported_metric}' ≠ 등록 지표 '{pre['metric']}'. "
                f"**사후 지표 갈아타기.** (seal={pre['seal']})"))

    return findings


def report(title: str, findings: list[Finding]) -> None:
    icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "🔴"}
    worst = "FAIL" if any(f.level == "FAIL" for f in findings) else \
            "WARN" if any(f.level == "WARN" for f in findings) else "OK"
    print(f"\n🪞 측정거울 감사: {title}")
    print(f"   종합: {icon[worst]} {worst}")
    for f in findings:
        print(f"   {icon[f.level]} [{f.probe}] {f.msg}")


# ─────────────────────────────────────────────────────────────
# CLI — 한 줄 실행
# ─────────────────────────────────────────────────────────────
def _auto(name: str, ledger: str = "mm_ledger.jsonl") -> None:
    """`mm <name>` — <name>.json 자동 탐색 → 원장 기준과 합쳐 감사."""
    import sys
    cands = [f"{name}.json", f"results/{name}.json", f"mm_results/{name}.json"]
    path = next((c for c in cands if os.path.exists(c)), None)
    if not path:
        print(f"🪞 '{name}' 결과 파일 없음. 평가가 {name}.json 을 뱉게 하세요.")
        print(f'   기대 형식: {{"acc":0.72,"n":500,"metric":"acc","baseline":0.5}}')
        sys.exit(1)
    d = json.load(open(path, encoding="utf-8"))
    cid = d.get("claim_id", name)
    print(f"📂 {path} 자동 로드")
    report(cid, audit(ledger, cid, reported_metric=d.get("metric", "acc"),
                      reported_acc=d["acc"], n=d["n"], baseline=d.get("baseline", 0.5)))


def _cli() -> None:
    import argparse, sys
    # 초간단: `mm <name>` (서브커맨드 없이) → <name>.json 자동 감사
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
            acc, n = d["acc"], d["n"]
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
