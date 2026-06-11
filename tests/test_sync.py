"""
Sync gate: verifies that every probe in mm.py is wired up in all downstream files.

When you add a new probe to mm.py, this test fails immediately if you forget to:
  - Register it as an MCP tool in mcp_server.py
  - Write at least one test in test_mm.py
  - Mention it in README.md

Run:  pytest tests/test_sync.py -v
"""
import ast
import pathlib

ROOT = pathlib.Path(__file__).parent.parent


# ─────────────────────────────────────────────────────────────
# Source of truth: public probe functions in mm.py
# ─────────────────────────────────────────────────────────────
def _probe_functions() -> list[str]:
    """Return all public functions in mm.py that return Finding or list[Finding]."""
    src = (ROOT / "measure_mirror" / "mm.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    probes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith("_"):
            continue
        # Check return annotation contains "Finding"
        ann = ast.unparse(node.returns) if node.returns else ""
        if "Finding" in ann:
            probes.append(node.name)
    return probes


PROBES = _probe_functions()

# MCP tools that intentionally don't map to a Finding-returning probe function.
# "mm_register" wraps preregister() → dict.
# "mm_witness" wraps witness() → dict (records a run, not an audit Finding).
_MCP_UTILITY_TOOLS = {"register", "anchor", "witness", "retract"}


def test_probe_list_nonempty():
    """Sanity: probe list must not be empty."""
    assert len(PROBES) >= 10, f"Expected ≥10 probes, found {len(PROBES)}: {PROBES}"


# ─────────────────────────────────────────────────────────────
# Gate 1: every probe → MCP tool
# ─────────────────────────────────────────────────────────────
def test_all_probes_in_mcp_server():
    """Every probe function must have a corresponding mm_<name> tool in mcp_server.py."""
    mcp_src = (ROOT / "measure_mirror" / "mcp_server.py").read_text(encoding="utf-8")
    missing = []
    for probe in PROBES:
        tool_name = f'"mm_{probe}"'
        if tool_name not in mcp_src:
            missing.append(f"{probe} → missing tool 'mm_{probe}' in mcp_server.py")
    assert not missing, "MCP sync gaps:\n" + "\n".join(f"  ✗ {m}" for m in missing)


# ─────────────────────────────────────────────────────────────
# Gate 2: every probe → at least one test
# ─────────────────────────────────────────────────────────────
def test_all_probes_have_tests():
    """Every probe function must appear at least once in test_mm.py."""
    test_src = (ROOT / "tests" / "test_mm.py").read_text(encoding="utf-8")
    missing = []
    for probe in PROBES:
        if probe not in test_src:
            missing.append(f"{probe} → not referenced in tests/test_mm.py")
    assert not missing, "Test coverage gaps:\n" + "\n".join(f"  ✗ {m}" for m in missing)


# ─────────────────────────────────────────────────────────────
# Gate 3: every probe → mentioned in README.md
# ─────────────────────────────────────────────────────────────
def test_all_probes_in_readme():
    """Every probe function must be mentioned in README.md."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = []
    for probe in PROBES:
        if probe not in readme:
            missing.append(f"{probe} → not mentioned in README.md")
    assert not missing, "README sync gaps:\n" + "\n".join(f"  ✗ {m}" for m in missing)


# ─────────────────────────────────────────────────────────────
# Gate 4: MCP tool names are consistent (no typos / orphans)
# ─────────────────────────────────────────────────────────────
def test_mcp_tools_have_matching_probes():
    """Every mm_<name> tool in mcp_server.py must correspond to a real probe in mm.py."""
    import re
    mcp_src = (ROOT / "measure_mirror" / "mcp_server.py").read_text(encoding="utf-8")
    # Extract all tool names from name="mm_..." strings
    tool_names = re.findall(r'name="mm_([^"]+)"', mcp_src)
    orphans = [t for t in tool_names if t not in PROBES and t not in _MCP_UTILITY_TOOLS]
    assert not orphans, (
        "Orphan MCP tools (no matching probe in mm.py):\n"
        + "\n".join(f"  ✗ mm_{t}" for t in orphans)
    )


# ─────────────────────────────────────────────────────────────
# Gate 5: every probe is exported from the package top level
# ─────────────────────────────────────────────────────────────
def test_all_probes_exported_from_package():
    """Every probe must be importable as `from measure_mirror import <probe>`."""
    import measure_mirror
    missing = [p for p in PROBES if not hasattr(measure_mirror, p)]
    assert not missing, (
        "__init__.py export gaps:\n"
        + "\n".join(f"  ✗ {p} → not exported from measure_mirror/__init__.py"
                    for p in missing)
    )


# ─────────────────────────────────────────────────────────────
# Gate 6: __version__ matches pyproject.toml
# ─────────────────────────────────────────────────────────────
def test_version_matches_pyproject():
    """measure_mirror.__version__ must equal the version in pyproject.toml."""
    import re
    import measure_mirror
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', toml, re.MULTILINE)
    assert m, "version not found in pyproject.toml"
    assert measure_mirror.__version__ == m.group(1), (
        f"Version drift: __init__.py has {measure_mirror.__version__!r}, "
        f"pyproject.toml has {m.group(1)!r}"
    )
