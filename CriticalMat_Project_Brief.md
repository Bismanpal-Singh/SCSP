# CriticalMat

AI-Accelerated Critical Minerals Discovery  
SCSP 2026 National Security Hackathon | Cloud Laboratories Track | 4-Person Team Brief

## 1. Project Overview

CriticalMat is an autonomous AI agent that discovers rare earth element alternatives for US defense applications. It runs a full hypothesis-to-candidate loop without human intervention, using computational materials screening as a substitute for physical lab experiments.

### The National Security Problem

The US depends on China for ~80% of rare earth elements used in defense hardware — neodymium and dysprosium in missile guidance magnets, F-35 actuators, submarine sonar transducers. If China restricts supply (as it has begun doing), these programs stop.

Normally finding a substitute material takes 6-18 months of manual lab work. CriticalMat compresses this to minutes.

### How The Agent Loop Works

- User types one plain English hypothesis — e.g. "Find a permanent magnet without neodymium for missile guidance"
- Parse & structure — Claude extracts allowed/banned elements and target material properties
- Database sweep — Materials Project API queried for matching compounds (150,000+ materials)
- Virtual experiment — computed properties fetched for each candidate (magnetic moment, stability, formation energy)
- Score & filter — candidates scored 0-100 against spec. Supply chain risk deducts points. Poor performers cut.
- Claude interprets — human-readable explanation of results, why each candidate passed or failed
- Propose next hypothesis — Claude reasons over failures and proposes a novel composition to try next
- Iterate — loop repeats until score converges or max iterations (5) reached

### Track Alignment

- Directly uses Materials Project API — explicitly listed in the track's provided resources
- Implements "autonomous experiment loop" — the first example direction in the hackathon brief
- Matches "active-learning style next-step selection" called out in the MP API description
- National security hook maps directly to SCSP's mission: China rare earth dependency is an active DoD concern
- No physical lab hardware needed — computational screening is the real first step in materials research

## 2. Tech Stack

One unified stack — all teammates use the same environment. No one is blocked by another's tooling choice.

| Component | Technology | Purpose |
| --- | --- | --- |
| Language | Python 3.11+ | Entire project — one language, no friction |
| Materials DB | `mp-api` (Materials Project) | Virtual lab — 150k+ computed material properties |
| AI reasoning | Anthropic Claude API | Hypothesis parsing, result interpretation, next-step generation |
| Agent framework | Custom Python loop | Simple while loop — no LangChain overhead for a hackathon |
| Terminal UI | `rich` (Python) | Colored live output for the demo — looks great on stage |
| Env management | `python-dotenv` | API keys in `.env`, never hardcoded |
| Version control | Git + GitHub | One shared repo, each person on their own branch |
| Demo safety | `demo_cache.json` | Pre-cached MP results so live demo has no network dependency |

### Install Everything

```bash
pip install mp-api anthropic python-dotenv rich
```

### Shared `.env` File (Everyone Uses This)

```env
MP_API_KEY=your_key_here          # from materialsproject.org (free)
ANTHROPIC_API_KEY=your_key_here   # from console.anthropic.com
```

### Shared Repo Structure

```text
criticalmat/
  interfaces.py    # P3 writes this FIRST — agreed function signatures
  mocks.py         # P3 writes this — fake functions so loop runs immediately
  search.py        # P1 owns — MP queries, supply chain filter
  scorer.py        # P1 owns — scoring function
  agent.py         # P2 owns — all Claude API calls
  prompts.py       # P2 owns — prompt strings
  loop.py          # P3 owns — main agent loop
  memory.py        # P3 owns — AgentMemory class
  main.py          # P3 owns — entry point
  demo.py          # P4 owns — terminal UI
  demo_cache.json  # P1 creates — pre-cached MP results
  README.md        # P4 owns
  pitch.md         # P4 owns
  .env             # everyone — never commit this
```

## 3. Team Roles & Timeline

| Person | Hours 0-3 | Hours 3-7 | Hours 7-10+ |
| --- | --- | --- | --- |
| P1 — MP Engineer | MP query + supply chain filter | Scorer + demo cache | Polish, edge cases, network testing |
| P2 — Claude Engineer | Hypothesis parser + result interpreter | Next-hypothesis generator, prompt tuning | Prompt polish, output quality |
| P3 — Loop Engineer | `interfaces.py` + mocks + loop skeleton | Integrate P1 + P2 real functions | End-to-end testing, debug |
| P4 — Demo Engineer | Terminal UI + output card (mock data) | README + pitch script | Rehearse, fast demo path |

### Critical Rule — No Blocking

P3 writes mock versions of P1 and P2's functions in the first hour. The loop runs end-to-end with fake data from minute one. When P1 and P2 finish their real functions, P3 swaps mocks out in one line each. Nobody waits for anyone.

The only thing all 4 people must do together in the first 30 minutes: agree on function signatures in `interfaces.py`.

## 4. Shared Interface Contract

P3 creates this file first. Everyone codes to these signatures. Do not change them without telling the team.

### `interfaces.py` — Agree On This Before Writing Any Real Code

```python
# P1 implements these:
def get_candidates(allowed_elements: list, banned_elements: list,
                   target_props: dict, limit: int = 50) -> list[dict]:
    # Returns: list of dicts with keys:
    # formula, magnetic_moment, formation_energy,
    # stability_above_hull, elements, mp_id, supply_chain_risk
    pass

def score_candidate(candidate: dict, spec: dict) -> int:
    # Returns: int 0-100
    pass

# P2 implements these:
def parse_hypothesis(text: str) -> dict:
    # Returns: {allowed_elements, banned_elements, target_props, context}
    pass

def interpret_results(candidates: list, spec: dict, iteration: int) -> str:
    # Returns: human-readable string
    pass

def generate_next_hypothesis(memory: dict) -> str:
    # Returns: plain English description of next composition to try
    pass
```

## 5. Cursor Prompts — Copy & Paste

Each person pastes their prompt below into Cursor's system prompt or as the first message. The prompt tells Cursor the full project context and exactly what that person is responsible for building.

### P1 — Person 1 (MP Data Engineer)

Paste this into your Cursor system prompt:

```text
You are working on CriticalMat — an autonomous AI agent for a national security hackathon (SCSP 2026). The project finds rare earth element alternatives for US defense applications using the Materials Project API and Claude AI.

YOUR ROLE: Person 1 — MP Data Engineer
You own all interactions with the Materials Project (MP) API. You do not touch Claude API calls or the main agent loop — those belong to teammates.

PROJECT OVERVIEW:
- User types a plain English hypothesis (e.g. "find a magnet without neodymium for missile guidance")
- Agent autonomously: searches MP database -> scores candidates -> Claude interprets -> Claude proposes next hypothesis -> loops
- Output: ranked list of viable material candidates with synthesis recommendations

YOUR FILES: search.py, scorer.py, demo_cache.json

YOUR TASKS:
1. Write get_candidates(allowed_elements: list, banned_elements: list, target_props: dict, limit: int = 50) -> list[dict]
   - Queries Materials Project using mp-api Python client
   - Returns list of dicts with keys: formula, magnetic_moment, formation_energy, stability_above_hull, band_gap, elements, mp_id
2. Write apply_supply_chain_filter(candidates: list) -> list[dict]
   - Hardcode CHINA_CONTROLLED = ["Nd", "Dy", "Tb", "Ho", "Pr", "Eu", "Gd", "Co"] and similar
   - Adds supply_chain_risk field (0-100) to each candidate dict
3. Write score_candidate(candidate: dict, spec: dict) -> int
   - Returns 0-100 score. Higher magnetic_moment = more points, lower formation_energy = more points, supply_chain_risk = points deducted
4. Cache one real MP query result to demo_cache.json so the live demo doesn't depend on network

INTERFACES YOU MUST MATCH (agree with P3 before coding):
get_candidates(allowed_elements, banned_elements, target_props, limit=50) -> list[dict]
score_candidate(candidate, spec) -> int (0-100)

SETUP:
pip install mp-api anthropic python-dotenv
Get free MP API key at materialsproject.org, store in .env as MP_API_KEY=...

INTEGRATION CHECKPOINTS:
- Hour 1: Push working get_candidates() with real MP data to shared repo
- Hour 3: Push scorer + supply chain filter
- Hour 6: P3 will swap your real functions into the loop — be available to debug
- Hour 8: Test full end-to-end run, fix any property key mismatches

PERIODICALLY: Pull from main branch and check interfaces.py has not changed. If P3 updates function signatures, update yours immediately.
```

### P2 — Person 2 (Claude Agent Engineer)

Paste this into your Cursor system prompt:

```text
You are working on CriticalMat — an autonomous AI agent for a national security hackathon (SCSP 2026). The project finds rare earth element alternatives for US defense applications using the Materials Project API and Claude AI.

YOUR ROLE: Person 2 — Claude Agent Engineer
You own all Claude API calls and prompt engineering. You do not touch the MP database queries or the main loop — those belong to teammates.

PROJECT OVERVIEW:
- User types a plain English hypothesis (e.g. "find a magnet without neodymium for missile guidance")
- Agent autonomously: searches MP database -> scores candidates -> Claude interprets -> Claude proposes next hypothesis -> loops
- Output: ranked list of viable material candidates with synthesis recommendations

YOUR FILES: agent.py, prompts.py

YOUR TASKS:
1. Write parse_hypothesis(text: str) -> dict
   - Claude call that converts plain English input into structured JSON: {allowed_elements, banned_elements, target_props, context, defense_application}
   - Must return valid Python dict (parse Claude's JSON response carefully)
2. Write interpret_results(candidates: list, spec: dict, iteration: int) -> str
   - Claude call that reads top-5 scored candidates and writes human-readable explanation
   - Should explain WHY each candidate passed or failed, and what property was closest
3. Write generate_next_hypothesis(memory: dict) -> str
   - Claude call that looks at what has been tried (in memory dict) and proposes a new composition
   - Output: plain English description of next composition to try, e.g. "try Fe16N2 family, nitrogen stabilizes..."
4. Iterate prompts until outputs are clean — this is most of your time

INTERFACES YOU MUST MATCH (agree with P3 before coding):
parse_hypothesis(text: str) -> dict with keys: allowed_elements (list), banned_elements (list), target_props (dict), context (str)
interpret_results(candidates, spec, iteration) -> str
generate_next_hypothesis(memory) -> str

ANTHROPIC SETUP:
pip install anthropic
Get API key from console.anthropic.com, store in .env as ANTHROPIC_API_KEY=...
Use model: claude-opus-4-5 or claude-sonnet-4-5

INTEGRATION CHECKPOINTS:
- Hour 1: Push working parse_hypothesis() that correctly extracts elements from plain English
- Hour 3: Push interpret_results() and generate_next_hypothesis()
- Hour 5: Tune prompts so generate_next_hypothesis() proposes chemically sensible compositions
- Hour 6: P3 integrates your functions — be available to debug prompt output format issues
- Hour 8: Full end-to-end test

PERIODICALLY: Pull from main branch. Check that memory dict structure matches what P3 is building in loop.py — your generate_next_hypothesis() reads from it.
```

### P3 — Person 3 (Loop & Integration Engineer)

Paste this into your Cursor system prompt:

```text
You are working on CriticalMat — an autonomous AI agent for a national security hackathon (SCSP 2026). The project finds rare earth element alternatives for US defense applications using the Materials Project API and Claude AI.

YOUR ROLE: Person 3 — Loop & Integration Engineer
You own the main agent loop and are responsible for connecting all teammates' work. You are the integration point — when P1 and P2 finish their functions, you swap them into the loop.

PROJECT OVERVIEW:
- User types a plain English hypothesis (e.g. "find a magnet without neodymium for missile guidance")
- Agent autonomously: searches MP database -> scores candidates -> Claude interprets -> Claude proposes next hypothesis -> loops
- Output: ranked list of viable material candidates with synthesis recommendations

YOUR FILES: loop.py, mocks.py, memory.py, interfaces.py, main.py

YOUR TASKS:
1. FIRST (hour 0-1): Write interfaces.py — the agreed function signatures for P1 and P2. Share this file before anyone writes real code.
2. Write mocks.py — fake versions of P1 and P2's functions that return hardcoded plausible data so the loop runs immediately
3. Write memory.py — AgentMemory class tracking: tried_compositions (list), scores_by_iteration (dict), current_best (dict), rejection_reasons (list)
4. Write loop.py — main run_agent(hypothesis, max_iterations=5) function:
   - Calls parse_hypothesis() -> get_candidates() -> score_candidate() for each -> interpret_results() -> generate_next_hypothesis() -> repeat
   - Prints progress at each step (P4 will style this output)
   - Convergence: exit if best score > 80, or if score hasn't improved in 2 iterations, or max_iterations reached
5. Write main.py — entry point: loads .env, takes user input, calls run_agent(), prints final result

INTEGRATION PROCESS:
- Hours 0-3: Build entire loop using mocks — it should run end-to-end with fake data
- Hour 3-4: Swap in P1's real functions from search.py (one import change)
- Hour 5-6: Swap in P2's real functions from agent.py (one import change)
- Hours 6-8: Debug integration issues, fix any data format mismatches between teammates

interfaces.py to write and share in first 30 min:
  get_candidates(allowed_elements, banned_elements, target_props, limit=50) -> list[dict]
  score_candidate(candidate, spec) -> int
  parse_hypothesis(text) -> dict
  interpret_results(candidates, spec, iteration) -> str
  generate_next_hypothesis(memory) -> str

PERIODICALLY (every 2 hrs): Pull all branches, check for interface changes, run end-to-end test, flag any breakage to team immediately.
```

### P4 — Person 4 (Demo & Presentation Engineer)

Paste this into your Cursor system prompt:

```text
You are working on CriticalMat — an autonomous AI agent for a national security hackathon (SCSP 2026). The project finds rare earth element alternatives for US defense applications using the Materials Project API and Claude AI.

YOUR ROLE: Person 4 — Demo & Presentation Engineer
You own the terminal UI, output formatting, README, and the pitch itself. You make the project look polished and tell the story compellingly on stage.

PROJECT OVERVIEW:
- User types a plain English hypothesis (e.g. "find a magnet without neodymium for missile guidance")
- Agent autonomously: searches MP database -> scores candidates -> Claude interprets -> Claude proposes next hypothesis -> loops
- Output: ranked list of viable material candidates with synthesis recommendations

YOUR FILES: demo.py, README.md, pitch.md

YOUR TASKS:
1. Write demo.py — terminal output layer using the 'rich' library:
   - print_header(): show project name + input hypothesis in a styled panel
   - print_iteration(n, candidates_tested, best_score, best_candidate): show live progress per loop
   - print_reasoning(text): show Claude's interpretation in a styled box
   - print_final_result(candidate): clean summary card — formula, properties, score, synthesis recommendation
   - print_rejection(formula, reason): show cut candidates with why they failed
2. Write README.md — problem -> solution -> impact structure. Include: setup instructions, how to run, example output, tech stack
3. Write pitch.md — the exact 60-second verbal script for the stage demo:
   - The one sentence you type live
   - What to say while it runs
   - The key stat to land at the end ("compressed 12 months of materials research into 90 seconds")
4. Hardcode a fast demo path in demo.py: --fast flag loads demo_cache.json from P1 instead of hitting MP API live

SETUP (independent of others):
pip install rich python-dotenv
You can build all of demo.py against a hardcoded mock output dict before P3 finishes the loop

INTEGRATION CHECKPOINTS:
- Hour 1: Build demo.py against a hardcoded dict — don't wait for P3
- Hour 4: Connect demo.py to P3's loop.py output (P3 calls your print_* functions from loop.py)
- Hour 6: Full styled run end-to-end
- Hour 8: Rehearse the pitch script with the real running system

PERIODICALLY: Pull from main and check that the output dict structure from loop.py matches what your print_final_result() expects. Coordinate with P3 on what fields the final candidate dict contains.
```

## 6. Integration Checkpoints

P3 drives these. Every checkpoint: pull all branches, run end-to-end, fix breakage before moving on.

| Time | Who | What must be true |
| --- | --- | --- |
| Hour 0 | All 4 | Repo created, `.env` set up, `interfaces.py` committed — function signatures agreed |
| Hour 1 | P1 + P3 | `get_candidates()` returns real MP data. P3's loop runs end-to-end with mocks |
| Hour 3 | P2 + P3 | `parse_hypothesis()` correctly extracts elements. Loop runs with P1 real + P2 mock |
| Hour 5 | P3 + P4 | Full loop runs with P1 + P2 real functions. P4's `demo.py` shows styled output |
| Hour 7 | All 4 | Full end-to-end: type one sentence, agent iterates, final result prints with styling |
| Hour 9 | P3 + P4 | Fast demo path working (`--fast` flag, cached data). Pitch rehearsed once |
| Demo | P4 speaks | Type sentence live, agent runs, converges, P4 delivers 60-second pitch |

### The Periodic Sync Rule

Every 2 hours, everyone stops for 10 minutes:

- Pull from `main` branch
- Check `interfaces.py` has not changed — if it has, update your code immediately
- Run `python main.py` with the fast flag — if it breaks, fix before continuing
- Each person says out loud what they finished and what they're doing next

## 7. The Demo Script

P4 owns this. Practice it with the real running system before the presentation.

### What You Type Live On Stage

"Find a permanent magnet for missile guidance systems that does not depend on Chinese rare earths."

### 60-Second Verbal Script

- (0-10s) While it runs: "Right now the US cannot build an F-35 without neodymium from China. That's not a supply chain risk — it's a national security vulnerability."
- (10-30s) While iterations print: "The agent is running its own experiments. It's querying 150,000 materials, scoring each one against the spec, cutting failures, and proposing the next composition to try — with no human in the loop."
- (30-50s) When result appears: "In 90 seconds it found iron nitride — a material that matches the magnetic performance of neodymium with zero Chinese supply chain dependency. A materials scientist would have taken 12 months to get here."
- (50-60s) Close: "This is what autonomous laboratory AI looks like for national security. The agent doesn't just search — it learns, iterates, and decides. CriticalMat."

---

CriticalMat | SCSP 2026 | Cloud Laboratories Track
