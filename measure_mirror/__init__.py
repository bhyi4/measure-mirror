"""🪞 Measurement Mirror — 평가 주장 자동 감사 (훈련0·결정론적·의존성0).

AI의 "X 달성" 주장이 진짜 신호인지 측정 착시(거짓양성/거짓음성)인지 자동 적발.
규율 원문: Chrysalis/agent_chat/MEASUREMENT_MIRROR.md (7체크).
"""
from .mm import (
    # ledger + utilities
    preregister, verify_chain, retract, anchor, calibrate, witness,
    # audits
    audit, continuous_audit, full_audit,
    # probes
    baseline_fairness, gaming_check, leakage_check, multiseed_check,
    scope_check, too_good_check, power_check, multiple_comparisons_check,
    grim_check, falsifiability_check, cascade_check, negative_audit,
    judge_consistency_check, judge_bias_check, inter_rater_agreement,
    judge_score_sanity,
    # helpers
    wilson_ci, lookup_baseline, report, Finding,
)

__all__ = [
    "preregister", "verify_chain", "retract", "anchor", "calibrate", "witness",
    "audit", "continuous_audit", "full_audit",
    "baseline_fairness", "gaming_check", "leakage_check", "multiseed_check",
    "scope_check", "too_good_check", "power_check", "multiple_comparisons_check",
    "grim_check", "falsifiability_check", "cascade_check", "negative_audit",
    "judge_consistency_check", "judge_bias_check", "inter_rater_agreement",
    "judge_score_sanity",
    "wilson_ci", "lookup_baseline", "report", "Finding",
]
__version__ = "0.10.0"
