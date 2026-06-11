"""
🪞 Measurement Mirror MCP 서버

AI가 측정거울 도구를 직접 호출할 수 있게 MCP 프로토콜로 노출.
stdio 방식 — Claude Code .claude/settings.json 에 등록해서 사용.

설치:
    pip install measure-mirror[mcp]

Claude Code 등록 (.claude/settings.json):
    {
      "mcpServers": {
        "measure-mirror": {
          "command": "python",
          "args": ["-m", "measure_mirror.mcp_server"]
        }
      }
    }
"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from . import mm

server = Server("measure-mirror")


# ─────────────────────────────────────────────────────────────
# 도구 목록
# ─────────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="mm_register",
            description=(
                "실험 결과를 보기 *전* 기준을 봉인 등록 (사전등록). "
                "해시로 봉인돼 나중에 변조하면 감사 때 탐지됨. "
                "반드시 실험 실행 전에 호출해야 함."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path": {"type": "string", "description": "원장 파일 경로 (JSONL)"},
                    "claim_id":    {"type": "string", "description": "실험/주장 식별자"},
                    "metric":      {"type": "string", "description": "평가 지표 이름 (예: acc, f1)"},
                    "min_n":       {"type": "integer", "description": "최소 표본 수", "default": 200},
                    "baseline":    {"type": "number",  "description": "비교 기준 성능", "default": 0.5},
                    "pass_threshold": {"type": "number", "description": "합격 기준 성능", "default": 0.60},
                },
                "required": ["ledger_path", "claim_id", "metric"],
            },
        ),
        types.Tool(
            name="mm_audit",
            description=(
                "분류/정확도 지표 실험 결과를 7체크로 감사. "
                "소표본 CI·사전등록 대조·봉인 위변조·pass_threshold 등 자동 적발. "
                "결과를 보고 난 후 호출."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":     {"type": "string", "description": "원장 파일 경로"},
                    "claim_id":        {"type": "string", "description": "실험 식별자"},
                    "reported_metric": {"type": "string", "description": "보고하는 지표 이름"},
                    "reported_acc":    {"type": "number", "description": "보고하는 정확도 (0~1)"},
                    "n":               {"type": "integer", "description": "표본 수"},
                    "baseline":        {"type": "number", "description": "baseline 성능 (미지정 시 0.5)"},
                },
                "required": ["ledger_path", "claim_id", "reported_metric", "reported_acc", "n"],
            },
        ),
        types.Tool(
            name="mm_continuous_audit",
            description=(
                "회귀·연속 지표(MSE, Pearson r, RMSE 등) 실험 감사. "
                "Wilson CI 대신 방향·효과크기·사전등록 체크."
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
                    "std":              {"type": "number", "description": "표준편차 (선택, 효과크기 계산용)"},
                    "higher_better":    {"type": "boolean", "default": True},
                },
                "required": ["ledger_path", "claim_id", "reported_metric",
                             "reported_value", "baseline_value", "n"],
            },
        ),
        types.Tool(
            name="mm_full_audit",
            description=(
                "7체크 전체를 한 번에 실행하는 통합 감사. "
                "선택 probe(누설·게이밍·다시드·scope)는 인자를 제공할 때만 활성화."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ledger_path":     {"type": "string"},
                    "claim_id":        {"type": "string"},
                    "reported_metric": {"type": "string"},
                    "reported_acc":    {"type": "number"},
                    "n":               {"type": "integer"},
                    "baseline":        {"type": "number"},
                    "competing_name":  {"type": "string",  "description": "② 경쟁 baseline 이름"},
                    "competing_acc":   {"type": "number",  "description": "② 경쟁 baseline 성능"},
                    "reward_terms":    {"type": "array", "items": {"type": "string"},
                                        "description": "③ reward/loss 항목 목록"},
                    "train_items":     {"type": "array", "items": {},
                                        "description": "④ train 데이터 항목 (누설 검사용)"},
                    "test_items":      {"type": "array", "items": {},
                                        "description": "④ test 데이터 항목 (누설 검사용)"},
                    "seed_results":    {"type": "array", "items": {"type": "number"},
                                        "description": "⑤ 시드별 결과 목록"},
                    "claimed_scope":   {"type": "array", "items": {"type": "string"},
                                        "description": "⑥ 주장하는 적용 범위"},
                    "tested_scope":    {"type": "array", "items": {"type": "string"},
                                        "description": "⑥ 실제 시험한 범위"},
                },
                "required": ["ledger_path", "claim_id", "reported_metric", "reported_acc", "n"],
            },
        ),
        types.Tool(
            name="mm_baseline_fairness",
            description="② 경쟁 baseline 대비 동률·역전 적발.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":          {"type": "string"},
                    "claimed":       {"type": "number"},
                    "baseline":      {"type": "number"},
                    "higher_better": {"type": "boolean", "default": True},
                    "margin":        {"type": "number", "default": 0.01},
                },
                "required": ["name", "claimed", "baseline"],
            },
        ),
        types.Tool(
            name="mm_gaming_check",
            description="③ reward/loss 항목에 평가 지표가 직접 포함됐는지 적발.",
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
            description="⑤ 여러 시드 결과의 분산·baseline 교차 경보.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seed_results":   {"type": "array", "items": {"type": "number"}},
                    "baseline":       {"type": "number", "default": 0.5},
                    "cv_threshold":   {"type": "number", "default": 0.10},
                },
                "required": ["seed_results"],
            },
        ),
        types.Tool(
            name="mm_scope_check",
            description="⑥ 주장이 증거 범위를 넘는 과대일반화 적발.",
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
            description="⑦ baseline 대비 너무 좋은 결과 선제 의심 경보.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name":               {"type": "string"},
                    "claimed":            {"type": "number"},
                    "baseline":           {"type": "number"},
                    "suspicious_margin":  {"type": "number", "default": 0.30},
                },
                "required": ["name", "claimed", "baseline"],
            },
        ),
    ]


# ─────────────────────────────────────────────────────────────
# 도구 실행
# ─────────────────────────────────────────────────────────────
def _findings_to_text(findings: list[mm.Finding]) -> str:
    icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
    worst = "FAIL" if any(f.level == "FAIL" for f in findings) else \
            "WARN" if any(f.level == "WARN" for f in findings) else "OK"
    lines = [f"종합: {icon[worst]} {worst}"]
    for f in findings:
        lines.append(f"{icon[f.level]} [{f.probe}] {f.msg}")
    return "\n".join(lines)


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
            result = f"🔒 봉인 완료\nclaim_id: {entry['claim_id']}\nmetric: {entry['metric']}\nmin_n: {entry['min_n']}\nbaseline: {entry['baseline']}\npass_threshold: {entry['pass_threshold']}\nseal: {entry['seal']}"

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
            )
            result = _findings_to_text(findings)

        elif name == "mm_baseline_fairness":
            f = mm.baseline_fairness(
                arguments["name"],
                arguments["claimed"],
                arguments["baseline"],
                higher_better=arguments.get("higher_better", True),
                margin=arguments.get("margin", 0.01),
            )
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
            result = f"{icon[f.level]} [{f.probe}] {f.msg}"

        elif name == "mm_gaming_check":
            f = mm.gaming_check(arguments["metric"], arguments["reward_terms"])
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
            result = f"{icon[f.level]} [{f.probe}] {f.msg}"

        elif name == "mm_multiseed_check":
            f = mm.multiseed_check(
                arguments["seed_results"],
                baseline=arguments.get("baseline", 0.5),
                cv_threshold=arguments.get("cv_threshold", 0.10),
            )
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
            result = f"{icon[f.level]} [{f.probe}] {f.msg}"

        elif name == "mm_scope_check":
            f = mm.scope_check(arguments["claimed_scope"], arguments["tested_scope"])
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
            result = f"{icon[f.level]} [{f.probe}] {f.msg}"

        elif name == "mm_too_good_check":
            f = mm.too_good_check(
                arguments["name"],
                arguments["claimed"],
                arguments["baseline"],
                suspicious_margin=arguments.get("suspicious_margin", 0.30),
            )
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "🔴"}
            result = f"{icon[f.level]} [{f.probe}] {f.msg}"

        else:
            result = f"알 수 없는 도구: {name}"

    except Exception as e:
        result = f"❌ 오류: {e}"

    return [types.TextContent(type="text", text=result)]


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
async def _main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
