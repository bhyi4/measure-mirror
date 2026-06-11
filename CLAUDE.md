# CLAUDE.md — Agent Rules for measure-mirror

Rules for any AI agent (Claude Code or equivalent) working in this repository.

## Mandatory: test before commit

```bash
cd /data/seara/measure_mirror_poc   # or wherever the repo is checked out
python -m pytest tests/ -v
```

**All 51+ tests must pass. Never commit with failing tests.**

The test suite includes a structural sync gate (`tests/test_sync.py`) that
checks every probe in `mm.py` is wired up in all downstream files. It will
fail immediately if you forget to update a connected file.

## When you add or modify a probe in mm.py

Adding a new probe means adding a function that returns `Finding` or
`list[Finding]`. The sync gate (`pytest tests/test_sync.py`) will fail if
any of these are missing:

| File | What to add |
|---|---|
| `measure_mirror/mm.py` | The probe function itself |
| `measure_mirror/mcp_server.py` | `mm_<probe_name>` tool in `list_tools()` + handler in `call_tool()` |
| `tests/test_mm.py` | At least one test that calls the probe |
| `README.md` | Row in the probe table + usage example if non-trivial |
| `README_KO.md` | Same update in Korean |
| `CHANGELOG.md` | Entry under the current version |
| `pyproject.toml` | Bump version (patch → minor for new probes) |

Run `pytest tests/test_sync.py -v` to get a specific list of what's missing.

## File roles (don't confuse them)

| File | Role |
|---|---|
| `measure_mirror/mm.py` | Core probe engine. Zero dependencies. |
| `measure_mirror/mcp_server.py` | MCP server exposing all probes as tools. Requires `mcp` package. |
| `measure_mirror/pytest_plugin.py` | `assert_clean()` for CI integration. |
| `tests/test_mm.py` | Unit + integration tests for probes. |
| `tests/test_sync.py` | Structural sync gate (mm.py ↔ mcp ↔ tests ↔ README). |
| `db/baselines.json` | Shared baseline database (git-based, no server). |
| `examples/` | Runnable demos. Keep them working. |

## Key invariants — do not break

1. **Zero dependencies for core** — `mm.py` uses Python stdlib only. Never
   add an import that isn't in stdlib. MCP extras go in `mcp_server.py`.

2. **First-write wins** — `_load_prereg()` returns the FIRST matching entry.
   Do not change this to last-write.

3. **Chain hash backward compatibility** — `_verify_seal()` must work for
   both legacy entries (no `prev_seal`) and new chained entries.

4. **Probe independence** — each probe function must be callable standalone
   without depending on another probe's state.

5. **English output** — all `Finding.probe` names and messages are in English.
   Korean content lives only in `README_KO.md`.

## Version bumping

- New probe or new feature → minor bump (0.3.0 → 0.4.0)
- Bug fix only → patch bump (0.3.0 → 0.3.1)
- Update `pyproject.toml` version and add a `CHANGELOG.md` entry.

## Running examples to verify

```bash
cd /data/seara/measure_mirror_poc
PYTHONPATH=. python examples/quickstart.py
```
