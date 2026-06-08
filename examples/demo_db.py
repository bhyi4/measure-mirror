"""공유 DB 기여가 도구를 강하게 하는지 실증 —
사용자는 musr의 baseline(0.5)을 *몰라도*, DB에 누가 등록해뒀으면 자동 적발."""
from measure_mirror import mm

print("▶ 사용자가 baseline을 모른 채 task='musr'만 줌 (DB가 채움):")
mm.report("ZERO '55.6%' (task=musr, baseline 자동조회)",
          mm.audit("/dev/null", "x", reported_metric="acc",
                   reported_acc=0.556, n=9, task="musr", db_dir="db"))

print("\n▶ DB에 없는 task면 그냥 0.5 fallback (도구는 여전히 동작):")
mm.report("미등록 task (fallback 0.5)",
          mm.audit("/dev/null", "x", reported_metric="acc",
                   reported_acc=0.556, n=9, task="unknown_task", db_dir="db"))

print("\n🪞 누가 'musr=0.5'를 DB에 *기여*해두면 → 다음 사용자는 baseline 몰라도 적발 ↑")
