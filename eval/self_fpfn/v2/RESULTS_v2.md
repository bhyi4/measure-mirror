# self_fpfn v2 — precision pass (mm_self_fpfn_v2)

v1 gave a point estimate with a wide Wilson bound (small n). v2 tightens the two
probes that carry an **approximation**, using oracles **independent of the probe
code**, and surfaces a real (small) calibration gap.

## Provenance (sealed before running)
- Pre-registration seal: `e978e43cf1e56686` (depends on v1 `6a029bdca093bbac`)
- `cases_v2.jsonl` sha256: `3e44b62076600088aa80d4687bf3f061241798ffb13f3e1d1c4d8b3482ff5476`
- Action seal: `0fc1b99d50eb81cd`
- 1119 cases. Deterministic generator (`gen_cases_v2.py`), no RNG.

## Oracles (independent of the probe)
| probe | probe uses | independent oracle |
|---|---|---|
| grim | 2-candidate (`k_lo`,`k_hi`) shortcut | **full brute-force k-sweep** over all k∈[0,n] |
| small_sample | Wilson / score CI vs baseline | **exact two-sided binomial test** (α=0.05) |

## Results
| probe | n | FN | FP | FN_rate (Wilson CI) | FP_rate (Wilson CI) |
|---|---|---|---|---|---|
| grim | 304 | 0 | 0 | 0.0 [0, 0.025] | 0.0 [0, 0.025] |
| small_sample | 815 | 7 | 0 | **0.0129 [0.006, 0.026]** | 0.0 [0, 0.014] |

- **grim**: 0 disagreement with brute force across 304 cases → the 2-candidate
  shortcut is **complete**. Kill (`grim_disagree_rate>0`) NOT triggered.
- **small_sample**: 7 disagreements, **all FN** (probe PASSES a result the exact
  test calls indistinguishable from chance). All sit just past the boundary —
  exact-binomial p ∈ [0.052, 0.065]:

  | id | n | k | acc | exact p | probe |
  |---|---|---|---|---|---|
  | s0005 | 5 | 5 | 1.000 | 0.0625 | OK |
  | s0181 | 50 | 32 | 0.640 | 0.0649 | OK |
  | s0221 | 60 | 38 | 0.633 | 0.0519 | OK |
  | s0271 | 80 | 49 | 0.613 | 0.0567 | OK |
  | s0335 | 100 | 60 | 0.600 | 0.0569 | OK |
  | s0550 | 200 | 114 | 0.570 | 0.0560 | OK |
  | s0728 | 300 | 167 | 0.557 | 0.0566 | OK |

## Reading it (honest, both directions)
- The Wilson/score CI is slightly **narrower** than the exact test near the
  boundary, so the probe is **over-optimistic** on ~1.3% of boundary cases
  (it never over-flags — FP=0). Notably `5/5` at n=5 is passed, though two-sided
  exact can never reach p≤0.05 at n=5 (min p = 0.0625).
- This is a **known approximation gap between two legitimate methods**, not a
  bug. It is **below** the pre-registered 0.15 concern bar.
- It **independently supports external critique point ①** (prefer
  Clopper-Pearson / exact for small n): switching the small-sample verdict to an
  exact test would remove all 7 FNs.

## Independence & scope
- Independence here is via **independent oracles** (brute-force, exact binomial),
  which is stronger than re-running the same code. A cross-**party** witness
  (L2) is still open — addressed by committing this for external reproduction,
  not by manufacturing a witness.
- Still deterministic-probe-only; LLM-judge probes out of scope.
