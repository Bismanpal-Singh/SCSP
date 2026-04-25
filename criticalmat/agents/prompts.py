"""
prompts.py

Person 2: Prompt templates for CriticalMat.

This file contains prompts for:
1. Parsing a natural language hypothesis into structured search constraints.
2. Interpreting candidate material results for the demo.
3. Generating the next autonomous hypothesis for active-learning iteration.

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
Your job is to convert it into STRICT JSON for a downstream Materials Project search and scoring pipeline.

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
    "avoid_rare_earths": true,

    "exclude_radioactive": true,
    "require_solid_state": true,
    "require_practical_materials": true,
    "require_manufacturable": true,
    "avoid_toxic_elements": true,
    "avoid_precious_metals": false
  }},
  "context": "Short explanation of what the user is trying to achieve.",
  "defense_application": "Short phrase describing the defense or national-security application."
}}

Rules for element constraints:
- If the user asks for no neodymium, ban "Nd".
- If the user mentions Chinese rare earths or rare-earth dependence, ban ["Nd", "Dy", "Tb", "Pr", "Sm", "Gd"].
- If the user asks to avoid all rare earths, ban ["Sc", "Y", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"].
- If the user mentions cobalt-free or avoiding cobalt, ban "Co".
- If the user says non-radioactive, radioactive-free, safe, field-safe, or deployable, set exclude_radioactive to true.
- If the user says solid-state, bulk material, ceramic, alloy, or crystal, set require_solid_state to true.
- If the user says manufacturable, scalable, practical, production-ready, or deployable, set require_practical_materials and require_manufacturable to true.
- If the user says non-toxic, low-toxicity, or environmentally safe, set avoid_toxic_elements to true.

Rules for material class:
- If the user asks for magnets, set material_class to "permanent_magnet".
- If the user asks for batteries or cathodes, set material_class to "battery_material".
- If the user asks for semiconductors, set material_class to "semiconductor".
- If the user asks for coatings, set material_class to "protective_coating".
- If unsure, set material_class to "unknown".

Rules for defense application:
- If the user mentions missile guidance, drones, actuators, sonar, aircraft, submarines, or defense hardware, include that in defense_application.
- Keep the phrase short and clear.

Defaults:
- allowed_elements can be empty if the user does not specify allowed elements.
- banned_elements must include explicitly forbidden elements.
- target_props should be simple and useful for scoring.
- For national-security materials, default exclude_radioactive, require_solid_state, require_practical_materials, and require_manufacturable to true unless the user clearly asks for something else.
"""


def interpret_results_prompt(candidates: list, spec: dict, iteration: int) -> str:
    """
    Prompt for interpreting candidate results from the materials search/scoring step.
    """

    top_candidates = candidates[:8]

    return f"""
You are CriticalMat's result interpretation agent.

You are reviewing candidate materials from an autonomous materials-discovery loop.

Iteration:
{iteration}

Search specification:
{json.dumps(spec, indent=2)}

Candidate materials:
{json.dumps(top_candidates, indent=2)}

Your task:
Write a concise human-readable interpretation for a hackathon demo.

You must explicitly apply the user's constraints:
- banned elements
- rare-earth avoidance
- exclude_radioactive
- require_solid_state
- require_practical_materials
- require_manufacturable
- avoid_toxic_elements
- supply-chain risk

Important:
If a candidate violates a hard constraint, call it "INELIGIBLE".
Do NOT describe an ineligible candidate as the strongest candidate, best candidate, or top candidate.
The best candidate must be selected only from eligible candidates.

Explain:
1. What the agent tested in this iteration.
2. Which candidates are INELIGIBLE and exactly why.
3. Which eligible candidate is strongest and why.
4. How supply-chain risk affected the ranking.
5. What the agent learned from this iteration.

Hard constraint examples:
- If a candidate contains a banned element, it is INELIGIBLE.
- If exclude_radioactive is true and the candidate contains radioactive elements, it is INELIGIBLE.
- If require_solid_state is true and a candidate is not a solid/bulk material, it is INELIGIBLE.
- If require_practical_materials is true and a candidate is too exotic, unstable, or impractical, mark it as lower priority or INELIGIBLE if clearly unsuitable.
- If require_manufacturable is true and a candidate looks highly impractical for scalable synthesis, mark it lower priority.

Important constraints:
- Be honest: these are computational/virtual-screening results, not confirmed physical lab results.
- Do not overclaim that a material is proven for missile systems, aircraft, or any defense platform.
- Keep the explanation clear for non-materials-science judges.
- Keep it under 240 words.
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
Your job is to propose the NEXT realistic composition family to test.

Memory from previous iterations:
{json.dumps(memory, indent=2)}

Return ONLY one plain-English sentence.
Do not use markdown.
Do not include a list.
Do not include explanations outside the sentence.

The next hypothesis must:
- Be a realistic material family, not generic text.
- Avoid repeating material families that already failed or were already tested.
- Prefer rare-earth-free or rare-earth-light compositions.
- Prefer lower supply-chain-risk elements.
- Avoid radioactive or impractical materials.
- Prefer solid-state, manufacturable, scalable materials.
- Be specific enough for another agent to parse.
- Be chemically reasonable for the target application.
- Choose a different search direction if failures cluster around one family.

Use these realistic next-step families in priority order when appropriate:
1. Mn-Al-C family for rare-earth-free permanent magnets because it is solid-state, practical, and lower supply-chain risk.
2. Ferrite Fe-O family such as strontium ferrite or barium ferrite for low-cost stable magnets.
3. Fe-N / iron nitride family for rare-earth-free permanent magnets.
4. Co-reduced Fe-Ni or Fe-Co-Ni family only if cobalt is not banned and cobalt risk is acceptable.
5. Heusler alloy families such as Mn-Al, Fe-Mn-Si, or Co-free variants when suitable.
6. Fe-Si or Fe-Ga families for magnetostrictive or actuator-related applications.
7. Mn-Bi family only if bismuth supply risk is explicitly acceptable and lower-risk families have already failed.
8. Alnico-style Fe-Al-Ni-Co family only if cobalt is not banned.

Diversity rule:
- If the memory shows Fe-N failed, do not suggest Fe-N again.
- If Mn-Al failed, do not suggest Mn-Al again.
- If ferrites failed, do not suggest ferrites again.
- If cobalt was penalized or banned, avoid Co-heavy families.
- If candidates failed due to supply-chain risk, suggest more abundant Fe/Mn/Al/Si/O/N based families.
- If candidates failed due to weak magnetism, suggest a family known for stronger magnetic behavior.
- If candidates failed due to poor stability, suggest more chemically stable oxide, nitride, or alloy families.

Good examples:
"Explore Mn-Al-C permanent magnet candidates because they are rare-earth-free, solid-state, and more manufacturable than exotic rare-earth substitutes."
"Test ferrite Fe-O candidates such as strontium ferrite because they avoid rare earths and offer low supply-chain risk for scalable magnet applications."
"Try Fe-N iron nitride candidates because they may preserve strong magnetism while avoiding rare-earth dependence."
"Explore Co-reduced Fe-Ni alloy candidates because they may balance magnetic performance with lower strategic supply-chain risk."

Bad examples:
"Try something better."
"Search the database again."
"I think the previous result was good."
"Use neodymium because it performs well."
"Try radioactive actinide compounds."
"Explore Mn-Bi first even though lower-risk Mn-Al-C or ferrite families have not been tested."
"""