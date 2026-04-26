# CriticalMat

CriticalMat is an autonomous materials-discovery agent for national security. It helps identify rare-earth-free material alternatives for defense hardware by combining Materials Project computational data with Gemini-driven scientific reasoning in an iterative loop.

## The Problem

US defense systems rely heavily on rare earth supply chains, especially elements with concentrated geopolitical risk. If those supply chains are disrupted, programs that depend on high-performance magnetic materials are exposed to schedule and readiness risk. CriticalMat accelerates substitute discovery by screening computational candidates before physical lab work.

## How It Works

1. A user enters a plain-English mission hypothesis (for example, "find a rare-earth-free magnet for missile guidance").  
2. The AI parser converts that text into structured constraints (banned elements, stability targets, practical-material requirements).  
3. The system queries Materials Project, gathers computed properties, and enriches candidates with supply-chain risk metadata.  
4. Candidates are scored and filtered, then Gemini explains why top options pass or fail.  
5. The agent proposes the next hypothesis and iterates until convergence or max iterations.

## Setup

```bash
git clone <your-repo-url>
cd SCSP
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with:
- `MP_API_KEY`
- `GEMINI_API_KEY`
- optionally `GEMINI_MODEL`
- `LLM_PROVIDER=gemini` or `LLM_PROVIDER=ollama`
- when using Ollama: `OLLAMA_MODEL` and `OLLAMA_HOST`

## Run

Start backend + frontend together:

```bash
npm run dev:full
```

Frontend: `http://localhost:3003`  
Backend API: `http://localhost:8000`

Live run (uses Materials Project API):

```bash
python -m criticalmat.main --hypothesis "Find a rare-earth-free permanent magnet for missile guidance"
```

Fast demo mode (uses cached candidates, avoids live MP query):

```bash
python -m criticalmat.main --fast --hypothesis "Find a rare-earth-free permanent magnet for missile guidance"
```

## Example Output

```text
Input hypothesis: Find a rare-earth-free permanent magnet candidate for precision military actuators with high magnetic moment and strong thermal stability.

=== Iteration 1/2 ===
1) Parsed hypothesis into structured spec.
2) Retrieved 50 candidates.
3) Scored candidates. Best eligible score this round: 70
4) Interpretation: [Gemini reasoning text]
5) Next hypothesis: Explore Mn-Al-C permanent magnet candidates...

=== Iteration 2/2 ===
...
Converged: best score exceeded 95.

=== Final Result ===
Formula: Mn4Al9
Score: 100 / 100
Magnetic moment: 60.0580876 uB
Supply chain risk: 0% China dependency
Synthesis route: [Gemini-generated recommendation]
```

## Tech Stack

- Materials Project API (`mp-api`) — computational materials data ("virtual lab")
- Google Gemini API (`google-genai`) — reasoning, interpretation, and next-step generation
- Python 3.11+ with `python-dotenv` and `rich` for runtime and terminal UX