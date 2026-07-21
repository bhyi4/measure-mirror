"""Tests for 🦋 catalog/draft_specimen.py — the no-fabrication auto-collector.

The tool must (1) transcribe real provenance verbatim from a sealed retraction,
(2) never fill interpretive fields (leave them TODO), (3) suggest a plausible
category, and (4) refuse when there is no sealed retraction to cite.
"""
import importlib.util
import json
from pathlib import Path

import pytest

# Load the script as a module (it lives in catalog/, not the package).
_SPEC = importlib.util.spec_from_file_location(
    "draft_specimen",
    Path(__file__).resolve().parent.parent / "catalog" / "draft_specimen.py")
ds = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ds)


def _ledger(tmp_path, entries):
    p = tmp_path / "l.jsonl"
    p.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
                 encoding="utf-8")
    return p


def _prereg(cid, **kw):
    return {"claim_id": cid, "metric": "acc", "seal": "seal_pre_" + cid, **kw}


def _retract(cid, reason, seal="seal_ret"):
    return {"_type": "retraction", "claim_id": cid, "reason": reason, "seal": seal}


def test_transcribes_real_provenance(tmp_path):
    led = _ledger(tmp_path, [
        _prereg("c1"),
        _retract("c1", "KILL per sealed criterion — clamp deaths 2/12.", seal="ret_abc"),
    ])
    d = ds.draft(led, claim_id="c1")
    assert d is not None
    assert "claim_id=c1" in d["provenance"]
    assert "ret_abc" in d["provenance"]          # retraction seal cited
    assert "seal_pre_c1" in d["provenance"]      # sealed criterion cited
    assert "clamp deaths 2/12" in d["body"]      # reason transcribed verbatim


def test_leaves_interpretive_fields_as_todo(tmp_path):
    led = _ledger(tmp_path, [_prereg("c1"), _retract("c1", "KILL — something.")])
    body = ds.draft(led, claim_id="c1")["body"]
    # every interpretive field is an explicit TODO — nothing fabricated
    for field in ("증상", "기전", "탐지법", "오적용"):
        assert f"**{field}" in body
    assert body.count("TODO") >= 4
    assert "DRAFT auto-generated" in body


@pytest.mark.parametrize("reason,expected", [
    ("train∩test 오염으로 무효", "contamination"),
    ("빈공간 다수클래스 자명 baseline 산물 (trivial)", "gaming"),
    ("거짓음성 — 구현 결함(implementation flaw)이 음성을 만듦", "fn-guard"),
    ("too good — self-caught 오귀속 착시", "self-catch"),
    ("plain KILL with no category keywords", "self-catch"),  # honest-KILL default
])
def test_category_suggestion(tmp_path, reason, expected):
    led = _ledger(tmp_path, [_prereg("c1"), _retract("c1", reason)])
    assert ds.draft(led, claim_id="c1")["category_dir"] == expected


def test_latest_picks_newest_retraction(tmp_path):
    led = _ledger(tmp_path, [
        _prereg("c1"), _retract("c1", "first KILL"),
        _prereg("c2"), _retract("c2", "second KILL", seal="ret2"),
    ])
    d = ds.draft(led, latest=True)
    assert d["claim_id"] == "c2" and "ret2" in d["provenance"]


def test_refuses_when_no_retraction(tmp_path):
    led = _ledger(tmp_path, [_prereg("c1")])  # sealed but never retracted
    assert ds.draft(led, claim_id="c1") is None
    assert ds.draft(led, latest=True) is None


def test_slug_is_filename_safe(tmp_path):
    led = _ledger(tmp_path, [
        _prereg("Weird ID/v2_20260720"),
        _retract("Weird ID/v2_20260720", "KILL"),
    ])
    slug = ds.draft(led, claim_id="Weird ID/v2_20260720")["slug"]
    assert "/" not in slug and " " not in slug and slug == "weird-idv2-20260720"


def test_write_creates_draft_file_and_refuses_overwrite(tmp_path):
    led = _ledger(tmp_path, [_prereg("c1"), _retract("c1", "too good — self-caught")])
    out = tmp_path / "spec.DRAFT.md"
    assert ds.main(["--ledger", str(led), "--claim", "c1", "--out", str(out)]) == 0
    assert out.exists() and "self-caught" in out.read_text(encoding="utf-8")
    # second write to the same path must refuse (never clobber a human-edited draft)
    assert ds.main(["--ledger", str(led), "--claim", "c1", "--out", str(out)]) == 3


def test_cli_missing_retraction_exit_1(tmp_path):
    led = _ledger(tmp_path, [_prereg("c1")])
    assert ds.main(["--ledger", str(led), "--claim", "c1"]) == 1
