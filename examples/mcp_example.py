"""
Measurement Mirror — MCP Server Usage Reference

This file shows what the MCP tools look like and how to test them
without a full MCP client. Run: python examples/mcp_example.py

For actual MCP integration, configure your client:
  Claude Code (.mcp.json):
    {
      "mcpServers": {
        "measure-mirror": {
          "command": "python",
          "args": ["-m", "measure_mirror.mcp_server"],
          "cwd": "/path/to/measure-mirror"
        }
      }
    }

  Other clients: run `mm-mcp` as the stdio server command.
"""
import asyncio
import os
from measure_mirror.mcp_server import call_tool

LEDGER = "/tmp/mm_mcp_example.jsonl"
if os.path.exists(LEDGER):
    os.remove(LEDGER)


async def main():
    print("=" * 60)
    print("🪞 Measurement Mirror — MCP Tool Reference")
    print("=" * 60)
    print("(Simulating MCP tool calls directly)\n")

    # ── mm_register ──────────────────────────────────────────
    print("[mm_register] Seal criteria before experiment")
    result = await call_tool("mm_register", {
        "ledger_path": LEDGER,
        "claim_id": "gpt_eval",
        "metric": "acc",
        "min_n": 200,
        "baseline": 0.5,
        "pass_threshold": 0.70,
    })
    print(result[0].text, "\n")

    # ── mm_audit ─────────────────────────────────────────────
    print("[mm_audit] Standard classification audit")
    result = await call_tool("mm_audit", {
        "ledger_path": LEDGER,
        "claim_id": "gpt_eval",
        "reported_metric": "acc",
        "reported_acc": 0.75,
        "n": 500,
        "baseline": 0.5,
    })
    print(result[0].text, "\n")

    # ── mm_full_audit ─────────────────────────────────────────
    print("[mm_full_audit] All probes at once")
    result = await call_tool("mm_full_audit", {
        "ledger_path": LEDGER,
        "claim_id": "gpt_eval",
        "reported_metric": "acc",
        "reported_acc": 0.75,
        "n": 500,
        "baseline": 0.5,
        "competing_name": "bert_baseline",
        "competing_acc": 0.72,
        "reward_terms": ["cross_entropy"],
        "seed_results": [0.73, 0.75, 0.76],
        "claimed_scope": ["qa_task"],
        "tested_scope": ["qa_task"],
    })
    print(result[0].text, "\n")

    # ── mm_continuous_audit ───────────────────────────────────
    print("[mm_continuous_audit] Regression metric (MSE)")
    result = await call_tool("mm_continuous_audit", {
        "ledger_path": "/dev/null",
        "claim_id": "regression_model",
        "reported_metric": "mse",
        "reported_value": 0.10,
        "baseline_value": 0.15,
        "n": 500,
        "higher_better": False,
        "std": 0.02,
    })
    print(result[0].text, "\n")

    # ── mm_gaming_check ───────────────────────────────────────
    print("[mm_gaming_check] Detect metric in reward")
    result = await call_tool("mm_gaming_check", {
        "metric": "acc",
        "reward_terms": ["acc_loss", "entropy"],
    })
    print(result[0].text, "\n")

    # ── mm_multiseed_check ────────────────────────────────────
    print("[mm_multiseed_check] Cross-seed variance")
    result = await call_tool("mm_multiseed_check", {
        "seed_results": [0.70, 0.72, 0.74],
        "baseline": 0.5,
    })
    print(result[0].text, "\n")

    # ── mm_scope_check ────────────────────────────────────────
    print("[mm_scope_check] Scope over-generalization")
    result = await call_tool("mm_scope_check", {
        "claimed_scope": ["general_reasoning", "math"],
        "tested_scope": ["musr_task_a"],
    })
    print(result[0].text, "\n")

    # ── mm_too_good_check ─────────────────────────────────────
    print("[mm_too_good_check] Suspiciously large improvement")
    result = await call_tool("mm_too_good_check", {
        "name": "miracle_model",
        "claimed": 0.95,
        "baseline": 0.5,
    })
    print(result[0].text)


asyncio.run(main())
