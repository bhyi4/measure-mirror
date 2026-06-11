"""
🪞 Measurement Mirror — MCP server

Exposes all 12 probes as MCP tools via stdio transport so any
MCP-compatible AI (Claude Code, Cursor, Windsurf, …) can call them
directly mid-conversation.

Install:
    pip install "measure-mirror[mcp]"

Claude Code (.mcp.json in project root):
    {
      "mcpServers": {
        "measure-mirror": {
          "command": "python",
          "args": ["-m", "measure_mirror.mcp_server"],
          "cwd": "/path/to/measure-mirror"
        }
      }
    }

Other MCP clients: run `mm-mcp` as the stdio server command.
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from . import mm

server = Server("measure-mirror")


# ─────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="mm_register",
            description=(
                "Seal evaluation criteria BEFORE running the experiment (pre-registration). "
                "Each entry is chain-hashed to the previous one — deletions and insertions "
                "are detected by mm_verify_chain. Must be called before the experiment runs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":    {"type": "string",  "description": "Path to the JSONL ledger file"},
                    "claim_id":       {"type": "string",  "description": "Experiment / claim identifier"},
                    "metric":         {"type": "string",  "description": "Evaluation metric name (e.g. acc, f1)"},
                    "min_n":          {"type": "integer", "description": "Minimum required sample size", "default": 200},
                    "baseline":       {"type": "number",  "description": "Fair comparison baseline performance", "default": 0.5},
                    "pass_threshold": {"type": "number",  "description": "Registered passing bar", "default": 0.60},
                },
                "required": ["ledger_path", "claim_id", "metric"],
            },
        ),
        types.Tool(
            name="mm_verify_chain",
            description=(
                "① Verify the full ledger chain integrity. "
                "Checks individual SHA-256 seals AND chain links (prev_seal). "
                "Catches: tampered entries, deleted entries, inserted entries. "
                "Call after any suspicious ledger activity, or routinely in CI."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path": {"type": "string", "description": "Path to the JSONL ledger file"},
                },
                "required": ["ledger_path"],
            },
        ),
        types.Tool(
            name="mm_audit",
            description=(
                "Audit a classification/accuracy metric result with probes ①+④a. "
                "Runs: Wilson CI small-sample check, direction check, pre-registration "
                "comparison (metric-swap, min_n, pass_threshold, seal tamper). "
                "Call after the experiment has completed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":     {"type": "string"},
                    "claim_id":        {"type": "string"},
                    "reported_metric": {"type": "string", "description": "Metric name being reported"},
                    "reported_acc":    {"type": "number", "description": "Reported accuracy (0–1)"},
                    "n":               {"type": "integer", "description": "Sample size"},
                    "baseline":        {"type": "number", "description": "Baseline performance (default 0.5)"},
                },
                "required": ["ledger_path", "claim_id", "reported_metric", "reported_acc", "n"],
            },
        ),
        types.Tool(
            name="mm_continuous_audit",
            description=(
                "Audit a continuous/regression metric (MSE, Pearson r, RMSE, …). "
                "Uses direction check + optional effect-size instead of Wilson CI. "
                "Set higher_better=False for loss metrics (lower is better)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":      {"type": "string"},
                    "claim_id":         {"type": "string"},
                    "reported_metric":  {"type": "string"},
                    "reported_value":   {"type": "number"},
                    "baseline_value":   {"type": "number"},
                    "n":                {"type": "integer"},
                    "std":              {"type": "number", "description": "Std dev (optional, enables effect-size check)"},
                    "higher_better":    {"type": "boolean", "default": True},
                },
                "required": ["ledger_path", "claim_id", "reported_metric",
                             "reported_value", "baseline_value", "n"],
            },
        ),
        types.Tool(
            name="mm_full_audit",
            description=(
                "Run all probes in one call. Optional probes activate when their "
                "arguments are provided. Includes: ① pre-registration + chain check, "
                "② fair baseline, ③ gaming, ④a leakage, ⑤ multi-seed, ⑥ scope, "
                "⑦ too-good, ⑧ power (min_detectable_effect), ⑨ multiple comparisons "
                "(check_multiplicity)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":            {"type": "string"},
                    "claim_id":               {"type": "string"},
                    "reported_metric":        {"type": "string"},
                    "reported_acc":           {"type": "number"},
                    "n":                      {"type": "integer"},
                    "baseline":               {"type": "number"},
                    "competing_name":         {"type": "string",  "description": "② Competing baseline name"},
                    "competing_acc":          {"type": "number",  "description": "② Competing baseline accuracy"},
                    "reward_terms":           {"type": "array",   "items": {"type": "string"},
                                               "description": "③ Training reward/loss term names"},
                    "train_items":            {"type": "array",   "items": {},
                                               "description": "④ Train items for leakage check"},
                    "test_items":             {"type": "array",   "items": {},
                                               "description": "④ Test items for leakage check"},
                    "seed_results":           {"type": "array",   "items": {"type": "number"},
                                               "description": "⑤ Per-seed result values"},
                    "claimed_scope":          {"type": "array",   "items": {"type": "string"},
                                               "description": "⑥ Claimed generalization scope"},
                    "tested_scope":           {"type": "array",   "items": {"type": "string"},
                                               "description": "⑥ Actually tested scope"},
                    "min_detectable_effect":  {"type": "number",
                                               "description": "⑧ Activate power check (minimum Δ to detect)"},
                    "check_multiplicity":     {"type": "boolean", "default": False,
                                               "description": "⑨ Activate multiple-comparisons Bonferroni check"},
                    "check_chain":            {"type": "boolean", "default": True,
                                               "description": "① Include chain integrity check"},
                },
                "required": ["ledger_path", "claim_id", "reported_metric", "reported_acc", "n"],
            },
        ),
        types.Tool(
            name="mm_baseline_fairness",
            description="② Detect crippled / tied / reversed baseline comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":          {"type": "string"},
                    "claimed":       {"type": "number"},
                    "baseline":      {"type": "number"},
                    "higher_better": {"type": "boolean", "default": True},
                    "margin":        {"type": "number",  "default": 0.01},
                },
                "required": ["name", "claimed", "baseline"],
            },
        ),
        types.Tool(
            name="mm_gaming_check",
            description="③ Detect eval metric appearing directly in reward/loss (self-fulfilling).",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric":       {"type": "string"},
                    "reward_terms": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["metric", "reward_terms"],
            },
        ),
        types.Tool(
            name="mm_multiseed_check",
            description="⑤ Cross-seed variance alarm — unstable signal / lucky seed detection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seed_results": {"type": "array", "items": {"type": "number"}},
                    "baseline":     {"type": "number", "default": 0.5},
                    "cv_threshold": {"type": "number", "default": 0.10},
                },
                "required": ["seed_results"],
            },
        ),
        types.Tool(
            name="mm_scope_check",
            description="⑥ Detect claimed scope wider than tested evidence (over-generalization).",
            inputSchema={
                "type": "object",
                "properties": {
                    "claimed_scope": {"type": "array", "items": {"type": "string"}},
                    "tested_scope":  {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claimed_scope", "tested_scope"],
            },
        ),
        types.Tool(
            name="mm_too_good_check",
            description="⑦ Flag suspiciously large improvement before believing it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":              {"type": "string"},
                    "claimed":           {"type": "number"},
                    "baseline":          {"type": "number"},
                    "suspicious_margin": {"type": "number", "default": 0.30},
                },
                "required": ["name", "claimed", "baseline"],
            },
        ),
        types.Tool(
            name="mm_power_check",
            description=(
                "⑧ False-negative guard. Warn when n is too small to detect the "
                "minimum detectable effect at the target power level. "
                "Closes the gap between 'bidirectional' design and implementation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "n":                     {"type": "integer", "description": "Sample size"},
                    "baseline":              {"type": "number",  "description": "Baseline performance"},
                    "min_detectable_effect": {"type": "number",  "default": 0.05,
                                              "description": "Minimum Δ above baseline to detect"},
                    "alpha":                 {"type": "number",  "default": 0.05},
                    "target_power":          {"type": "number",  "default": 0.80},
                },
                "required": ["n", "baseline"],
            },
        ),
        types.Tool(
            name="mm_multiple_comparisons_check",
            description=(
                "⑨ Garden-of-forking-paths detector. Counts distinct experiments in "
                "the ledger and warns with the Bonferroni-corrected α when k>1. "
                "Running k experiments and reporting only the best inflates false-positive rate."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path": {"type": "string"},
                    "alpha":       {"type": "number", "default": 0.05},
                },
                "required": ["ledger_path"],
            },
        ),
    ]


# ─────────────────────────────────────────────────────────────
# Tool execution
# ─────────────────────────────────────────────────────────────
def _findings_to_text(findings: list[mm.Finding]) -> str:
    icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
    worst = "FAIL" if any(f.level == "FAIL" for f in findings) else \
            "WARN" if any(f.level == "WARN" for f in findings) else "OK"
    lines = [f"Overall: {icon[worst]} {worst}"]
    for f in findings:
        lines.append(f"{icon[f.level]} [{f.probe}] {f.msg}")
    return "\n".join(lines)


def _single(f: mm.Finding) -> str:
    icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
    return f"{icon[f.level]} [{f.probe}] {f.msg}"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "mm_register":
            entry = mm.preregister(
                arguments["ledger_path"],
                arguments["claim_id"],
                metric=arguments["metric"],
                min_n=arguments.get("min_n", 200),
                baseline=arguments.get("baseline", 0.5),
                pass_threshold=arguments.get("pass_threshold", 0.60),
            )
            result = (
                f"🔒 Sealed\n"
                f"claim_id: {entry['claim_id']}\n"
                f"metric: {entry['metric']}\n"
                f"min_n: {entry['min_n']}\n"
                f"baseline: {entry['baseline']}\n"
                f"pass_threshold: {entry['pass_threshold']}\n"
                f"prev_seal: {entry['prev_seal']}\n"
                f"seal: {entry['seal']}"
            )

        elif name == "mm_verify_chain":
            findings = mm.verify_chain(arguments["ledger_path"])
            result = _findings_to_text(findings)

        elif name == "mm_audit":
            findings = mm.audit(
                arguments["ledger_path"],
                arguments["claim_id"],
                reported_metric=arguments["reported_metric"],
                reported_acc=arguments["reported_acc"],
                n=arguments["n"],
                baseline=arguments.get("baseline"),
            )
            result = _findings_to_text(findings)

        elif name == "mm_continuous_audit":
            findings = mm.continuous_audit(
                arguments["ledger_path"],
                arguments["claim_id"],
                reported_metric=arguments["reported_metric"],
                reported_value=arguments["reported_value"],
                baseline_value=arguments["baseline_value"],
                n=arguments["n"],
                std=arguments.get("std"),
                higher_better=arguments.get("higher_better", True),
            )
            result = _findings_to_text(findings)

        elif name == "mm_full_audit":
            findings = mm.full_audit(
                arguments["ledger_path"],
                arguments["claim_id"],
                reported_metric=arguments["reported_metric"],
                reported_acc=arguments["reported_acc"],
                n=arguments["n"],
                baseline=arguments.get("baseline"),
                competing_name=arguments.get("competing_name"),
                competing_acc=arguments.get("competing_acc"),
                reward_terms=arguments.get("reward_terms"),
                train_items=arguments.get("train_items"),
                test_items=arguments.get("test_items"),
                seed_results=arguments.get("seed_results"),
                claimed_scope=arguments.get("claimed_scope"),
                tested_scope=arguments.get("tested_scope"),
                min_detectable_effect=arguments.get("min_detectable_effect"),
                check_chain=arguments.get("check_chain", True),
                check_multiplicity=arguments.get("check_multiplicity", False),
            )
            result = _findings_to_text(findings)

        elif name == "mm_baseline_fairness":
            result = _single(mm.baseline_fairness(
                arguments["name"],
                arguments["claimed"],
                arguments["baseline"],
                higher_better=arguments.get("higher_better", True),
                margin=arguments.get("margin", 0.01),
            ))

        elif name == "mm_gaming_check":
            result = _single(mm.gaming_check(
                arguments["metric"],
                arguments["reward_terms"],
            ))

        elif name == "mm_multiseed_check":
            result = _single(mm.multiseed_check(
                arguments["seed_results"],
                baseline=arguments.get("baseline", 0.5),
                cv_threshold=arguments.get("cv_threshold", 0.10),
            ))

        elif name == "mm_scope_check":
            result = _single(mm.scope_check(
                arguments["claimed_scope"],
                arguments["tested_scope"],
            ))

        elif name == "mm_too_good_check":
            result = _single(mm.too_good_check(
                arguments["name"],
                arguments["claimed"],
                arguments["baseline"],
                suspicious_margin=arguments.get("suspicious_margin", 0.30),
            ))

        elif name == "mm_power_check":
            result = _single(mm.power_check(
                arguments["n"],
                arguments["baseline"],
                min_detectable_effect=arguments.get("min_detectable_effect", 0.05),
                alpha=arguments.get("alpha", 0.05),
                target_power=arguments.get("target_power", 0.80),
            ))

        elif name == "mm_multiple_comparisons_check":
            result = _single(mm.multiple_comparisons_check(
                arguments["ledger_path"],
                alpha=arguments.get("alpha", 0.05),
            ))

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"❌ Error: {e}"

    return [types.TextContent(type="text", text=result)]


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
async def _main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
