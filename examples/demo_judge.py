"""
🪞 Demo: LLM-as-a-Judge auditing — probes ⑭⑮⑯⑰⑱ (no API key needed).

Three mock judges show the three failure modes the mirror catches:

  1. content_judge      — reads the responses; survives every probe
  2. content_blind_judge — deterministic but never reads the responses:
                           passes ⑭ (consistent), ⑮ (balanced), ⑰ (varied)
                           — ONLY the ⑱ swap test exposes it
  3. lazy_judge          — returns the same rating for everything; caught by ⑰

Run:  python examples/demo_judge.py
"""
import os
import tempfile

from measure_mirror import mm
from measure_mirror.judge import judge_run

LEDGER = os.path.join(tempfile.gettempdir(), "mm_demo_judge_ledger.jsonl")
if os.path.exists(LEDGER):
    os.remove(LEDGER)

# 20 pairwise items: response quality encoded as length (longer = better).
# Half the items have the better response in slot A, half in slot B.
items = []
for i in range(20):
    good, bad = "x" * 50, "x" * 10
    if i % 2 == 0:
        items.append({"prompt": f"q{i}", "a": good, "b": bad})   # A is better
    else:
        items.append({"prompt": f"q{i}", "a": bad, "b": good})   # B is better


def content_judge(item):
    """Honest judge: picks the longer (better) response."""
    return 0 if len(item["a"]) >= len(item["b"]) else 1


def content_blind_judge(item):
    """The hardest case: deterministic, balanced — and never reads a response.
    Verdict depends only on the prompt, so it is perfectly consistent (⑭ OK),
    unbiased on aggregate (⑮ OK ≈50%), and varied (⑰ OK).  But swap A and B
    and the verdict stays with the slot: the ⑱ swap test is the ONLY probe
    that exposes it."""
    return hash(item["prompt"]) % 2


def lazy_judge(item):
    """Degenerate judge: same rating for everything."""
    return 8


def show(title, result):
    print(f"\n{'─' * 60}\n🪞 {title}")
    icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "🔴"}
    for f in result["findings"]:
        print(f"   {icon[f.level]} [{f.probe}] {f.msg}")


# 1) Honest judge — everything passes, including the swap test
r = judge_run(LEDGER, "demo_content_judge",
              judge_fn=content_judge, items=items,
              runs=2, pairwise=True, swap_positions=True)
show("content_judge (honest)", r)

# 2) Content-blind judge — passes ⑭⑮⑯⑰, ONLY ⑱ catches it
r = judge_run(LEDGER, "demo_content_blind_judge",
              judge_fn=content_blind_judge, items=items,
              runs=2, pairwise=True, swap_positions=True)
show("content_blind_judge (deterministic, never reads responses)", r)

# 3) Degenerate judge — rating mode, ⑰ catches the flat distribution
rating_items = [{"prompt": f"q{i}", "response": "x" * (i + 1)} for i in range(20)]
r = judge_run(LEDGER, "demo_lazy_judge",
              judge_fn=lazy_judge, items=rating_items,
              runs=2, pairwise=False)
show("lazy_judge (rating mode, always 8)", r)

# Ledger is chain-linked — verify and certify
print(f"\n{'─' * 60}")
mm.report("judge ledger integrity", mm.verify_chain(LEDGER))
print(f"\n📜 Certificate for demo_content_judge:")
import json
print(json.dumps(mm.certificate(LEDGER, "demo_content_judge"), indent=2))
print(f"\n(ledger: {LEDGER})")
