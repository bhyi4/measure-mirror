"""Docs ↔ code SSOT guard.

An anti-overclaim tool must not misstate its own probe count. The README's
"N probes" phrasing had drifted to 26 while the code (GROUPS registry) carries
27 — exactly the kind of self-contradiction the tool exists to catch. These
tests make the count derive from code so it cannot drift again.
"""
import re
from pathlib import Path

import measure_mirror as mm

REPO = Path(__file__).resolve().parents[1]


def _probe_count() -> int:
    return sum(len(v) for v in mm.GROUPS.values())


def test_readme_probe_count_matches_code():
    """Every 'N probes' claim in README.md must equal the GROUPS registry."""
    n = _probe_count()
    counts = [int(x) for x in re.findall(r"(\d+) probes", (REPO / "README.md").read_text())]
    assert counts, "no 'N probes' phrase found in README.md — did the wording change?"
    assert all(c == n for c in counts), f"README.md probe count(s) {counts} != code {n}"


def test_readme_ko_probe_count_matches_code():
    """KO total-count claim must equal code; subset-usage numbers (e.g. the
    full_audit '7종' example) are allowed only if strictly below the total."""
    n = _probe_count()
    counts = [int(x) for x in re.findall(r"(\d+)종 probe", (REPO / "README_KO.md").read_text())]
    assert counts, "no 'N종 probe' phrase found in README_KO.md"
    assert max(counts) == n, f"README_KO.md total probe count {max(counts)} != code {n}"
    assert all(c <= n for c in counts), f"a subset count exceeds the total: {counts}"
