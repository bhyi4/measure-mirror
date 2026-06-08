"""🪞 Measurement Mirror — 평가 주장 자동 감사 (훈련0·결정론적·의존성0).

AI의 "X 달성" 주장이 진짜 신호인지 측정 착시(거짓양성/거짓음성)인지 자동 적발.
규율 원문: Chrysalis/agent_chat/MEASUREMENT_MIRROR.md (7체크).
"""
from .mm import (
    preregister, audit, wilson_ci, leakage_check,
    baseline_fairness, report, Finding,
)

__all__ = [
    "preregister", "audit", "wilson_ci", "leakage_check",
    "baseline_fairness", "report", "Finding",
]
__version__ = "0.1.0"
