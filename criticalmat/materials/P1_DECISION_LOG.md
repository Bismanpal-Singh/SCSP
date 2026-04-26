# P1 Decision Log (MP Engineer)

This file records implementation decisions made for the P1 scope in CriticalMat so they are easy to reference during integration, demo prep, and later iteration.

## Context

Goal for P1 (Hours 0-3): deliver working Materials Project retrieval, supply-chain risk tagging, scoring, and demo-safe cached output.

## Decisions and Rationale

### 1) Keep P1 scope strictly limited to data + scoring

- **Decision:** Implement only `search.py`, `scorer.py`, and `demo_cache.json`.
- **Why:** Matches ownership boundaries and avoids blocking/overlapping with P2/P3 work.
- **Impact:** Clean handoff and easier integration.

### 2) Use a fixed candidate output schema

- **Decision:** Normalize all candidate records to:
  - `formula`
  - `magnetic_moment`
  - `formation_energy`
  - `stability_above_hull`
  - `band_gap`
  - `elements`
  - `mp_id`
  - `supply_chain_risk`
- **Why:** Stable downstream interface for scoring, loop integration, and demo rendering.
- **Impact:** Prevents key mismatches across teammate modules.

### 3) Keep supply-chain logic as hardcoded heuristic (for now)

- **Decision:** Use hardcoded China-controlled element risk map and derive candidate `supply_chain_risk`.
- **Why:** Fastest reliable approach for hackathon timeline; explicitly aligned with brief guidance.
- **Impact:** Deterministic behavior and easy explainability in demo.
- **Known tradeoff:** Not fully dynamic/live; risk values are heuristics, not continuously updated intelligence.

### 4) Keep `supply_chain_risk` as numeric (not just boolean)

- **Decision:** Retain `supply_chain_risk` on a `0-100` scale.
- **Why:** Preserves rank-order nuance and future-proofs the interface.
- **Impact:** Enables richer scoring now and simple upgrade path later.
- **Alternative discussed:** Binary China/non-China flag can work for MVP, but loses differentiation.

### 5) Include fallback retrieval path beyond `mp-api` client

- **Decision:** If `mp-api` client path fails, query Materials Project summary endpoint via HTTPS request fallback.
- **Why:** Local environment showed `mp-api` dependency incompatibility on Python 3.13; fallback preserves functionality.
- **Impact:** Higher robustness across dev environments.

### 6) Add empty-result widening strategy

- **Decision:** If strict allowed+excluded element query returns no hits, broaden search and then filter locally by allowed elements.
- **Why:** Strict conjunction queries can be too restrictive and return zero candidates.
- **Impact:** More reliable candidate yield for demos and early testing.

### 7) Use weighted performance + risk scoring

- **Decision:** `score_candidate` uses weighted contributions from magnetic moment, formation energy, and stability, then subtracts supply-chain penalty.
- **Why:** Project objective is dual: material performance and strategic resilience.
- **Impact:** Avoids selecting technically strong but geopolitically risky materials.

### 8) Generate and keep demo cache from real query

- **Decision:** Create `criticalmat/demo_cache.json` from live query output.
- **Why:** Demo reliability should not depend on network/API latency.
- **Impact:** Enables fast/consistent demo path.

### 9) Two-stage virtual screening (wide fetch, narrow return)

- **Decision:** `get_candidates` requests up to **100** Materials Project summary rows by default (`mp_screen_fetch_limit` in `target_props`, hard cap 500), applies supply-chain enrichment, runs `score_candidate` on **each** row as a preliminary rank, then returns only the **top `limit`** (default 50) to the loop.
- **Why:** Aligns with the brief (“screen many candidates in seconds”) and avoids returning an arbitrary first page of MP results when better candidates exist in the same query window.
- **Impact:** More local scoring work per call (up to fetch size). Tunable via `target_props["mp_screen_fetch_limit"]` without changing function signatures.
- **Override:** Lower the fetch limit during dev to reduce latency; raise (still capped at 500) for more aggressive screening.

### 10) Add viability/safety metadata (soft mode)

- **Decision:** Keep candidates in the result set but annotate them with realism/safety flags instead of hard dropping:
  - `is_radioactive`
  - `is_solid_likely`
  - `is_practical`
- **Why:** Preserve optionality for downstream decision logic (P3/P2 may choose when/how to filter).
- **Impact:** More flexible orchestration while still exposing risk/safety signals explicitly.

### 11) Apply `target_props` directly in ranking metadata

- **Decision:** Use `target_props` in scoring/practicality metadata (not hard elimination), especially:
  - `max_stability_above_hull`
  - `min_magnetic_moment` for magnet tasks
  - `mp_screen_fetch_limit`
- **Why:** Keep retrieval broad while still encoding spec-aware quality signals.
- **Impact:** Better alignment between parsed hypothesis and ranked/annotated candidate pool.

### 12) Add magnet-family diversity and realism flags

- **Decision:** Tag candidate families (`fe_n`, `mn_al`, `ferrite`, `fe_co`, etc.), diversify returns across families, and add deterministic flags:
  - `is_radioactive`
  - `is_solid_likely`
  - `is_practical`
  - `family_tag`
- **Why:** Prevent near-identical outputs and improve explainability for P2/P3 reasoning.
- **Impact:** More varied, interpretable shortlists with explicit safety/practicality metadata.

### 13) Cap MP API `exclude_elements` and enforce full bans locally

- **Decision:** Cap the `exclude_elements` sent to Materials Project API at `MAX_API_EXCLUDE_ELEMENTS=10`, while enforcing the full parsed banned-element set locally after retrieval.
- **Why:** Large parser-generated banned lists triggered intermittent MP `422 Unprocessable Entity` failures.
- **Impact:** Improves retrieval reliability without weakening ban enforcement correctness.

## Validation Evidence

- `get_candidates(...)` live run returned non-zero candidates.
- `score_candidate(...)` returned valid integer score in `0..100`.
- `demo_cache.json` generated successfully with real material entries.

## What We Explicitly Chose Not To Do (Yet)

- Build full live risk-intelligence pipeline (scheduled updates from external feeds).
- Add external config service for risk weights.
- Add source-attributed per-element risk provenance in runtime payload.

These are good post-MVP improvements once integration is stable.

## Beyond MP: reaction-level “experiments” (optional)

Materials Project answers **bulk equilibrium materials** (phases, hull, magnetization proxies). It does **not** simulate “what if I mix A + B under these reaction conditions” unless you add another layer (e.g. **Open Reaction Database** for published reaction outcomes, or explicit thermochemistry / phase-diagram tools). That would be a separate P1 extension or a cross-team feature: ORD for reaction feasibility/conditions, MP for resulting solid phases and properties.

## Future Upgrade Path (Post-Hackathon or Hour 5+)

1. Add `RISK_FEED_URL` and TTL cache.
2. Replace hardcoded element risk map with fetched risk model.
3. Compute risk from weighted components:
   - `import_dependency`
   - `country_concentration`
   - `export_restriction_signal`
   - `substitutability`
   - `price_volatility`
4. Maintain fallback to local defaults if feed unavailable.

## Quick Talking Points for Judges / Team

- CriticalMat optimizes for both **performance** and **supply resilience**.
- `supply_chain_risk` is included to avoid geopolitically fragile recommendations.
- The system is robust: live query path plus demo-safe cached mode.
