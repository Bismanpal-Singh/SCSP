"""
prompts.py

Person 2: Prompt templates for CriticalMat.

This file contains prompts for:
1. Parsing a natural language hypothesis into structured search constraints.
2. Interpreting candidate material results for the demo.

Project context:
CriticalMat is an autonomous AI agent for the SCSP 2026 Cloud Laboratories track.
It searches for rare-earth alternatives for defense applications using Materials Project data
and an autonomous hypothesis-to-candidate loop.
"""

import json


def parse_hypothesis_prompt(user_text: str) -> str:
    """
    Prompt for converting a user hypothesis into structured JSON.
    """

    return f"""
You are CriticalMat, an autonomous materials-discovery agent for national-security critical-mineral substitution.

The user will give a plain-English hypothesis or mission need.
Your job is to convert it into STRICT JSON for a downstream Materials Project search.

User hypothesis:
\"\"\"{user_text}\"\"\"

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations outside JSON.

Required JSON schema:
{{
  "allowed_elements": [],
  "banned_elements": [],
  "target_props": {{
    "material_class": "permanent_magnet",
    "needs_magnetism": true,
    "prefer_high_magnetic_moment": true,
    "max_stability_above_hull": 0.1,
    "prefer_low_formation_energy": true,
    "avoid_rare_earths": true
  }},
  "context": "Short explanation of what the user is trying to achieve.",
  "defense_application": "Short phrase describing the defense or national-security application."
}}

Rules:
- If the user asks for no neodymium, ban "Nd".
- If the user mentions Chinese rare earths or rare-earth dependence, ban ["Nd", "Dy", "Tb", "Pr", "Sm", "Gd"].
- If the user mentions cobalt-free or avoiding cobalt, ban "Co".
- If the user asks for magnets, set material_class to "permanent_magnet".
- If the user mentions missile guidance, drones, actuators, sonar, aircraft, submarines, or defense hardware, include that in defense_application.
- allowed_elements can be empty if the user does not specify allowed elements.
- banned_elements must include explicitly forbidden elements.
- target_props should be simple and useful for scoring.
"""


def interpret_results_prompt(candidates: list, spec: dict, iteration: int) -> str:
    """
    Prompt for interpreting candidate results from the materials search/scoring step.
    """

    top_candidates = candidates[:5]

    return f"""
You are CriticalMat's result interpretation agent.

You are reviewing candidate materials from an autonomous materials-discovery loop.

Iteration:
{iteration}

Search specification:
{json.dumps(spec, indent=2)}

Top candidate materials:
{json.dumps(top_candidates, indent=2)}

Your task:
Write a concise human-readable interpretation for a hackathon demo.

Explain:
1. What the agent tested in this iteration.
2. Which candidate is strongest and why.
3. Which candidates were rejected or are weaker and why.
4. How supply-chain risk affected the ranking.
5. What the agent learned from this iteration.

Important constraints:
- Be honest: these are computational/virtual-screening results, not confirmed physical lab results.
- Do not overclaim that a material is proven for missile systems, aircraft, or any defense platform.
- Keep the explanation clear for non-materials-science judges.
- Keep it under 220 words.
"""

def generate_next_hypothesis_prompt(memory: dict) -> str:
    """
    Prompt for generating the next autonomous material hypothesis.

    This is the active-learning step:
    based on previous candidates, scores, and failures, propose what to test next.
    """

    return f"""
You are CriticalMat's active-learning materials agent.

CriticalMat is an autonomous AI agent for critical-mineral substitution in national-security materials.
The agent has already tested or screened some candidate materials.
Your job is to propose the NEXT hypothesis to test.

Memory from previous iterations:
{json.dumps(memory, indent=2)}

Return ONLY one plain-English sentence.
Do not use markdown.
Do not include a list.
Do not include explanations outside the sentence.

The next hypothesis should:
- Avoid repeating material families that already failed.
- Prefer rare-earth-free or rare-earth-light compositions.
- Prefer lower supply-chain-risk elements.
- Be specific enough for another agent to parse.
- Be chemically reasonable for the target application.
- Focus on what to try next, not on summarizing what already happened.

Good examples:
"Try Fe-N based compounds such as iron nitride because they may preserve strong magnetism while avoiding rare-earth dependence."
"Explore Mn-Al-C family candidates because they are rare-earth-free and have known permanent-magnet potential."
"Test Fe-Co-Ni compositions with reduced cobalt content to balance magnetic performance against supply-chain risk."
"Explore ferrite-based candidates using Fe-O systems because they avoid rare earths and have low strategic supply risk."

Bad examples:
"Try something better."
"Search the database again."
"I think the previous result was good."
"Use neodymium because it performs well."
"""