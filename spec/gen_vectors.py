#!/usr/bin/env python3
"""Generate MIRROR-SPEC v1 conformance vectors (Phase 1c).

Valid vectors are built with the seal algorithm from SPEC §4 (reimplemented
here independently, then cross-checked against measure_mirror.linkage_check).
Invalid vectors are deliberate corruptions of valid ones.
"""
import hashlib, json, os, shutil, sys

OUT = "/data/seara/measure_mirror_poc/spec/vectors"

def seal_of(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k not in ("seal", "sig")}
    s = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def chain(entries):
    prev = "genesis"
    out = []
    for e in entries:
        e = dict(e)
        e["prev_seal"] = prev
        e["seal"] = seal_of(e)
        prev = e["seal"]
        out.append(e)
    return out

def write(name, entries_or_text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(entries_or_text, str):
            f.write(entries_or_text)
        else:
            for e in entries_or_text:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path

os.makedirs(OUT, exist_ok=True)
expected = {}

# ---------- valid ----------
# v01: minimal — preregister (no _type, legacy-normative) + retraction
v01 = chain([
    {"ts": "2026-07-02T00:00:00Z", "claim_id": "demo_claim", "metric": "acc",
     "min_n": 30, "baseline": 0.5, "pass_threshold": 0.7,
     "kill_condition": "acc below 0.55 on held-out set",
     "kill_threshold": {"metric": "acc", "threshold": 0.55, "direction": "below"}},
    {"_type": "retraction", "ts": "2026-07-02T01:00:00Z",
     "claim_id": "demo_claim", "reason": "kill condition triggered: acc=0.51"},
])
write("valid_01_minimal.jsonl", v01)
expected["valid_01_minimal.jsonl"] = {"L1": "OK", "L1_seal_recompute": "OK"}

# v02: legacy variances — uppercase GENESIS, no-Z timestamp, non-ASCII, amendment
v02_first = {"ts": "2026-06-19T11:03:11", "claim_id": "레거시_주장", "metric": "held_out_accuracy",
             "min_n": 120, "baseline": 0.2, "pass_threshold": 0.8,
             "kill_condition": "정확도 0.8 미만이면 KILL"}
v02_first["prev_seal"] = "GENESIS"  # case-insensitive per §5.1
v02_first["seal"] = seal_of(v02_first)
v02_amend = {"ts": "2026-06-19T15:19:20", "claim_id": "레거시_주장",
             "metric": "[AMENDMENT to seal %s] held_out_accuracy" % v02_first["seal"],
             "min_n": 120, "baseline": 0.2, "pass_threshold": 0.8,
             "amends_seal": v02_first["seal"],
             "kill_threshold": {"amends_seal": v02_first["seal"], "change": "sampler swap"},
             "prev_seal": v02_first["seal"]}
v02_amend["seal"] = seal_of(v02_amend)
write("valid_02_legacy.jsonl", [v02_first, v02_amend])
expected["valid_02_legacy.jsonl"] = {"L1": "OK", "L1_seal_recompute": "OK"}

# v03: action ledger + witnessing ledger (L2 pair)
v03_peer = chain([
    {"_type": "action", "ts": "2026-07-02T02:00:00Z", "agent": "demo_agent",
     "action": "measure", "target": "demo_claim", "payload": {"n": 30, "acc": 0.51}},
    {"_type": "action", "ts": "2026-07-02T02:10:00Z", "agent": "demo_agent",
     "action": "report", "target": "demo_claim"},
])
write("valid_03_peer.jsonl", v03_peer)
peer_bytes = open(os.path.join(OUT, "valid_03_peer.jsonl"), "rb").read()
v03_wit = chain([
    {"_type": "peer_witness", "ts": "2026-07-02T02:20:00Z", "peer": "demo_agent",
     "peer_entries": 2, "peer_head_seal": v03_peer[-1]["seal"],
     "peer_anchor": hashlib.sha256(peer_bytes).hexdigest()[:16]},
])
write("valid_03_witness.jsonl", v03_wit)
expected["valid_03_peer.jsonl"] = {"L1": "OK", "L1_seal_recompute": "OK"}
expected["valid_03_witness.jsonl"] = {"L1": "OK", "L1_seal_recompute": "OK",
                                      "L2_vs_valid_03_peer.jsonl": "OK"}

# v04: pins SPEC §4.1 canonical JSON byte-exactly — floats (shortest repr),
# int vs float, recursive key sorting, unicode, booleans, null.
# An implementation whose seals match these has the canonicalization right.
v04 = chain([
    {"_type": "action", "ts": "2026-07-02T03:00:00Z", "agent": "canon-check",
     "action": "measure", "target": "numbers_claim",
     "payload": {"zebra": 0.5, "alpha": {"nested_b": 1, "nested_a": 1.0},
                 "half": 0.25, "big": 120, "flag": True, "nothing": None,
                 "text": "정규화 テスト ✓"}},
    {"ts": "2026-07-02T03:10:00Z", "claim_id": "numbers_claim", "metric": "acc",
     "min_n": 30, "baseline": 0.3333333333333333, "pass_threshold": 0.7,
     "kill_condition": "acc < 0.55", "chance": 0.1},
])
write("valid_04_numbers.jsonl", v04)
expected["valid_04_numbers.jsonl"] = {"L1": "OK", "L1_seal_recompute": "OK"}

# ---------- invalid ----------
# i01: linkage broken (middle entry's prev_seal wrong)
bad = [dict(e) for e in v01]
bad[1]["prev_seal"] = "0000000000000000"
bad[1]["seal"] = seal_of(bad[1])  # internally consistent seal, broken link
write("invalid_01_linkage_broken.jsonl", bad)
expected["invalid_01_linkage_broken.jsonl"] = {"L1": "FAIL", "reason": "linkage broken at entry 1"}

# i02: first entry prev_seal != genesis
bad = [dict(e) for e in v01]
bad[0]["prev_seal"] = "deadbeefdeadbeef"
bad[0]["seal"] = seal_of(bad[0])
bad[1]["prev_seal"] = bad[0]["seal"]
bad[1]["seal"] = seal_of(bad[1])
write("invalid_02_no_genesis.jsonl", bad)
expected["invalid_02_no_genesis.jsonl"] = {"L1": "FAIL", "reason": "first entry prev_seal must be genesis"}

# i03: malformed JSON line
text = "\n".join(json.dumps(e, ensure_ascii=False) for e in v01[:1])
text += "\n{this is not json}\n"
write("invalid_03_malformed.jsonl", text)
expected["invalid_03_malformed.jsonl"] = {"L1": "FAIL", "reason": "malformed JSON"}

# i04: empty ledger
write("invalid_04_empty.jsonl", "")
expected["invalid_04_empty.jsonl"] = {"L1": "FAIL", "reason": "ledger is empty"}

# i05: content tampered but declared chain kept consistent
#      (kill_threshold loosened after the fact; seals NOT recomputed)
bad = [json.loads(json.dumps(e)) for e in v01]
bad[0]["kill_threshold"]["threshold"] = 0.30  # silent loosening
write("invalid_05_tampered_content.jsonl", bad)
expected["invalid_05_tampered_content.jsonl"] = {
    "L1": "OK", "L1_seal_recompute": "FAIL",
    "reason": "declared chain intact but entry 0 seal does not match recomputation (§6.2)"}

# i06: peer truncated below witnessed count (L2)
write("invalid_06_peer_truncated.jsonl", v03_peer[:1])
expected["invalid_06_peer_truncated.jsonl"] = {
    "L1": "OK",
    "L2_vs_valid_03_witness.jsonl": "FAIL", "reason": "TRUNCATED: peer has 1 < witnessed 2"}

# i07: peer rewritten at witnessed position (valid internal chain, different head)
rew = chain([
    dict(v03_peer[0], seal=None, prev_seal=None) | {},
    {"_type": "action", "ts": "2026-07-02T02:10:00Z", "agent": "demo_agent",
     "action": "report", "target": "demo_claim", "payload": {"note": "rewritten history"}},
])
# rebuild cleanly (chain() already handles seals)
rew = chain([
    {"_type": "action", "ts": "2026-07-02T02:00:00Z", "agent": "demo_agent",
     "action": "measure", "target": "demo_claim", "payload": {"n": 30, "acc": 0.51}},
    {"_type": "action", "ts": "2026-07-02T02:10:00Z", "agent": "demo_agent",
     "action": "report", "target": "demo_claim", "payload": {"note": "rewritten history"}},
])
write("invalid_07_peer_rewritten.jsonl", rew)
expected["invalid_07_peer_rewritten.jsonl"] = {
    "L1": "OK",
    "L2_vs_valid_03_witness.jsonl": "FAIL", "reason": "REWRITTEN: head at witnessed position differs"}

# i08: line parses as JSON but is not an object (SPEC §3.1 / §6.1 step 2)
text = json.dumps(v01[0], ensure_ascii=False) + "\n42\n"
write("invalid_08_non_object.jsonl", text)
expected["invalid_08_non_object.jsonl"] = {"L1": "FAIL", "reason": "non-object JSON line is malformed"}

with open(os.path.join(OUT, "expected.json"), "w", encoding="utf-8") as f:
    json.dump(expected, f, indent=2, ensure_ascii=False)

# ---------- self-check against reference implementation ----------
sys.path.insert(0, "/data/seara/measure_mirror_poc")
from measure_mirror.mm import linkage_check

fails = []
for name, exp in expected.items():
    if "L1" not in exp:
        continue
    ok, msg, entries = linkage_check(os.path.join(OUT, name))
    got = "OK" if ok else "FAIL"
    status = "✓" if got == exp["L1"] else "✗"
    if got != exp["L1"]:
        fails.append((name, exp["L1"], got, msg))
    print(f"{status} {name}: expected L1={exp['L1']}, got {got} ({msg})")

# L1+ seal recomputation check for i05
ok, msg, entries = linkage_check(os.path.join(OUT, "invalid_05_tampered_content.jsonl"))
recomputed_ok = all(seal_of(e) == e["seal"] for e in entries)
print(("✓" if not recomputed_ok else "✗") +
      f" invalid_05 L1+ recompute: expected FAIL, got {'OK' if recomputed_ok else 'FAIL'}")
if recomputed_ok:
    fails.append(("invalid_05", "L1+ FAIL", "L1+ OK", "tamper not caught"))

# L2 checks
def l2_check(witness_path, peer_path):
    _, _, wit = linkage_check(witness_path)
    _, _, peer = linkage_check(peer_path)
    peer = peer or []
    for w in wit:
        if w.get("_type") != "peer_witness":
            continue
        n = w["peer_entries"]
        if len(peer) < n:
            return "FAIL", "TRUNCATED"
        if peer[n - 1].get("seal") != w["peer_head_seal"]:
            return "FAIL", "REWRITTEN"
    return "OK", "pinned heads consistent"

for peer_file, exp_key in [("valid_03_peer.jsonl", "OK"),
                            ("invalid_06_peer_truncated.jsonl", "FAIL"),
                            ("invalid_07_peer_rewritten.jsonl", "FAIL")]:
    got, why = l2_check(os.path.join(OUT, "valid_03_witness.jsonl"),
                        os.path.join(OUT, peer_file))
    status = "✓" if got == exp_key else "✗"
    if got != exp_key:
        fails.append((peer_file, exp_key, got, why))
    print(f"{status} L2 witness vs {peer_file}: expected {exp_key}, got {got} ({why})")

print()
print("VECTOR SELF-CHECK:", "ALL PASS" if not fails else f"{len(fails)} MISMATCH: {fails}")
