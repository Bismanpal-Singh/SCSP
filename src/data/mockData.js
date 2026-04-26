// ─────────────────────────────────────────────────────────────
//  mockData.js
//  Single source of truth for all fake data while building.
//  When the real FastAPI backend is ready, this gets replaced
//  by API responses — but the shape stays exactly the same.
// ─────────────────────────────────────────────────────────────

export const mockHypothesis =
  "Find a permanent magnet for missile guidance systems that does not depend on Chinese rare earths."

export const mockIterations = [
  {
    num: 1,
    candidatesTested: 47,
    bestFormula: "Fe₃Co",
    bestFormulaPlain: "Fe3Co",
    score: 34,
    interpretation:
      "Cobalt content too high — supply chain risk flagged. Co is on China-controlled list. Magnetic moment is promising but geopolitical score tanks the overall ranking.",
    nextHypothesis:
      "Switch to iron-nitrogen compounds. No cobalt. Nitrogen interstitials may stabilize the structure without rare earths.",
    status: "continue",
  },
  {
    num: 2,
    candidatesTested: 31,
    bestFormula: "Fe₈N",
    bestFormulaPlain: "Fe8N",
    score: 61,
    interpretation:
      "Good magnetic strength, zero China dependency. But it breaks down at 200°C. The missile spec requires stability up to 350°C. Fails on temperature alone.",
    nextHypothesis:
      "Try Fe₁₆N₂ — denser nitrogen packing in the alpha-prime phase should improve both stability and coercivity.",
    status: "continue",
  },
  {
    num: 3,
    candidatesTested: 22,
    bestFormula: "Fe₁₆N₂",
    bestFormulaPlain: "Fe16N2",
    score: 87,
    interpretation:
      "Meets spec on all three axes. Magnetic moment 2.9 μB exceeds minimum. Stable to 400°C. All precursors domestically available. Score converged — recommending this candidate.",
    nextHypothesis: null,
    status: "converged",
  },
]

export const mockFinalCandidate = {
  formula:          "Fe₁₆N₂",
  formulaPlain:     "Fe16N2",
  fullName:         "Iron Nitride (alpha-prime phase)",
  score:            87,
  magneticMoment:   "2.9 μB",
  thermalStability: "Stable to 400°C",
  formationEnergy:  "−0.34 eV/atom",
  supplyChainScore: 96,
  chinaDependency:  "0%",
  mpId:             "mp-fe16n2",
  synthesisRecommendation:
    "Nitrogen ion implantation into a pure iron thin film at 150°C for 4 hours. Anneal in nitrogen atmosphere at 120°C to stabilize the alpha-prime phase. Target film thickness 200–500 nm for optimal coercivity. Process is compatible with existing US defense manufacturing infrastructure — no new equipment required.",
  supplyChain: [
    { element: "Fe",  name: "Iron",                 source: "US domestic",  riskPct: 0,  barPct: 100, safe: true,  replaced: false },
    { element: "N₂",  name: "Nitrogen",             source: "US domestic",  riskPct: 0,  barPct: 100, safe: true,  replaced: false },
    { element: "Nd",  name: "Neodymium (replaced)", source: "China (85%)",  riskPct: 85, barPct: 85,  safe: false, replaced: true  },
  ],
}

// ── Tab 3: Agent Decision Log ─────────────────────────────────
// Full log of every candidate the agent touched across all
// iterations — kept or rejected — with the exact reason why.
export const mockDecisionLog = [
  { iteration: 1, formula: "Fe₃Co",  score: 34, decision: "rejected", reason: "Cobalt is on China-controlled list. Supply chain risk score 78/100 — eliminates candidate despite decent magnetic moment.", mpId: "mp-fe3co" },
  { iteration: 1, formula: "SmCo₅",  score: 12, decision: "rejected", reason: "Both samarium and cobalt are China-controlled. Eliminated in first filter pass.", mpId: "mp-smco5" },
  { iteration: 1, formula: "MnBi",   score: 28, decision: "rejected", reason: "Bismuth supply chain risk. Magnetic moment drops sharply at room temperature — fails spec.", mpId: "mp-mnbi" },
  { iteration: 1, formula: "AlNiCo", score: 41, decision: "rejected", reason: "Coercivity too low for missile guidance application. Standard commercial magnet, not suitable for defense spec.", mpId: "mp-alnico" },
  { iteration: 1, formula: "FePt",   score: 22, decision: "rejected", reason: "Platinum supply chain risk — >70% from South Africa and Russia.", mpId: "mp-fept" },
  { iteration: 1, formula: "Fe₃N",   score: 38, decision: "rejected", reason: "Magnetic moment below minimum threshold. Formation energy unstable at elevated temperature.", mpId: "mp-fe3n" },
  { iteration: 2, formula: "Fe₈N",   score: 61, decision: "rejected", reason: "Good magnetic strength and zero China dependency. Fails on thermal stability — degrades at 200°C, spec requires 350°C.", mpId: "mp-fe8n" },
  { iteration: 2, formula: "Fe₄N",   score: 45, decision: "rejected", reason: "Thermal stability adequate but magnetic moment 1.8 μB too low — spec requires 2.5 μB minimum.", mpId: "mp-fe4n" },
  { iteration: 2, formula: "Fe₂N",   score: 33, decision: "rejected", reason: "High nitrogen content destabilizes crystal structure at target operating temperature.", mpId: "mp-fe2n" },
  { iteration: 2, formula: "FeN",    score: 29, decision: "rejected", reason: "Antiferromagnetic at room temperature — no net magnetic moment. Unusable for permanent magnet application.", mpId: "mp-fen" },
  { iteration: 3, formula: "Fe₁₆N₂", score: 87, decision: "selected", reason: "Meets all three spec requirements. Magnetic moment 2.9 μB, stable to 400°C, zero China dependency. Agent converged — recommended.", mpId: "mp-fe16n2" },
  { iteration: 3, formula: "Fe₁₂N",  score: 71, decision: "rejected", reason: "Close to spec on magnetic moment but hull distance suggests metastability — synthesis at scale would be unreliable.", mpId: "mp-fe12n" },
  { iteration: 3, formula: "Fe₈N₂",  score: 58, decision: "rejected", reason: "Thermal stability improved over Fe₈N but still below 350°C threshold. Formation energy also unfavorable.", mpId: "mp-fe8n2" },
]

export const mockStructuredDecisionLog = {
  mission: "Find a solid-state manufacturable replacement material for a defense component that avoids Chinese-controlled rare earths and radioactive elements.",
  constraints: {
    material_class: "permanent_magnet",
    banned_elements: ["Nd", "Dy", "Tb", "Co"],
    exclude_radioactive: true,
    require_solid_state: true,
  },
  portfolio: [
    {
      rank: 1,
      candidate: "Mn4Al9",
      mpId: "mp-mn4al9",
      family: "Mn-Al",
      status: "TEST_FIRST",
      scores: {
        scientific_fit: 85,
        stability: 90,
        supply_chain_safety: 100,
        manufacturability: 80,
        evidence_confidence: 90,
        overall: 100,
      },
      main_uncertainty: "Phase stability of tau-MnAl phase under thermal cycling above 400C",
      likely_failure_mode: "Decomposition to non-magnetic phases during operation",
      recommended_experiment: "VSM characterization to determine magnetic anisotropy and coercivity",
    },
    {
      rank: 2,
      candidate: "Mn2O3",
      mpId: "mp-mn2o3",
      family: "Fe-O",
      status: "BACKUP_TEST",
      scores: {
        scientific_fit: 80,
        stability: 85,
        supply_chain_safety: 60,
        manufacturability: 70,
        evidence_confidence: 85,
        overall: 90,
      },
      main_uncertainty: "Antiferromagnetic nature may limit utility without structural modification",
      likely_failure_mode: "Low remanence due to antiferromagnetic coupling",
      recommended_experiment: "SQUID magnetometry to evaluate ferrimagnetic behavior",
    },
    {
      rank: 3,
      candidate: "Fe2O3",
      mpId: "mp-fe2o3",
      family: "Fe-O",
      status: "SAFE_FALLBACK",
      scores: {
        scientific_fit: 75,
        stability: 80,
        supply_chain_safety: 50,
        manufacturability: 75,
        evidence_confidence: 95,
        overall: 88,
      },
      main_uncertainty: "High-temperature phase transformation into non-magnetic hematite variants",
      likely_failure_mode: "Insufficient coercivity for high-performance actuator applications",
      recommended_experiment: "XRD and SEM analysis to assess microstructural stability",
    },
  ],
  ineligible: [
    { formula: "Nd2Fe14B", reason: "Contains banned element: Nd", mpId: "mp-nd2fe14b" },
  ],
  testQueue: [
    "VSM characterization of Mn4Al9 to determine magnetic anisotropy and coercivity.",
    "SQUID magnetometry of Mn2O3 to evaluate potential for ferrimagnetic behavior.",
    "XRD and SEM analysis of Fe2O3 to assess microstructural stability.",
  ],
  constraintsPayload: {
    material_class: "permanent_magnet",
    banned_elements: ["Nd", "Dy", "Tb", "Co"],
    exclude_radioactive: true,
    require_solid_state: true,
  },
  provenanceTree: {
    mission: "Find a solid-state manufacturable replacement material...",
    constraints: {
      material_class: "permanent_magnet",
      banned_elements: ["Nd", "Dy", "Tb", "Co"],
      exclude_radioactive: true,
      require_solid_state: true,
    },
    candidate_search: {
      iterations_run: 1,
      ineligible: [{ formula: "Nd2Fe14B", reason: "Contains banned element: Nd" }],
      portfolio: [
        { rank: 1, candidate: "Mn4Al9", status: "TEST_FIRST" },
        { rank: 2, candidate: "Mn2O3", status: "BACKUP_TEST" },
        { rank: 3, candidate: "Fe2O3", status: "SAFE_FALLBACK" },
      ],
    },
    test_queue: [
      "VSM characterization of Mn4Al9 to determine magnetic anisotropy and coercivity.",
      "SQUID magnetometry of Mn2O3 to evaluate ferrimagnetic behavior.",
      "XRD and SEM analysis of Fe2O3 to assess microstructural stability.",
    ],
  },
}

export const mockLogSummary = {
  totalCandidates:  100,
  totalRejected:    99,
  totalSelected:    1,
  iterationsRun:    3,
  convergenceScore: 87,
}

export const mockDecisionTree = {
  root: {
    id: "root",
    label: "Hypothesis",
    description: "Magnet without Chinese rare earths",
  },
  levels: [
    {
      iteration: 1,
      candidatesTested: 47,
      bestScore: 34,
      branchedFrom: "root",
      candidates: [
        { id: "smco5",  formula: "SmCo₅",  fullName: "Samarium Cobalt", score: 12, status: "rejected", reason: "Both Sm and Co China-controlled", magneticMoment: "strong", thermalStability: "high", formationEnergy: "stable", chinaDependency: "high", supplyChainRisk: "very high", mpId: "mp-smco5" },
        { id: "mnbi",   formula: "MnBi",   fullName: "Manganese Bismuth", score: 28, status: "rejected", reason: "Bismuth supply chain risk", magneticMoment: "moderate", thermalStability: "room-temperature dropoff", formationEnergy: "metastable", chinaDependency: "medium", supplyChainRisk: "high", mpId: "mp-mnbi" },
        { id: "fe3co",  formula: "Fe₃Co",  fullName: "Iron Cobalt", score: 34, status: "explored", isBest: true, reason: "Cobalt fails supply chain", magneticMoment: "promising", thermalStability: "acceptable", formationEnergy: "stable", chinaDependency: "medium", supplyChainRisk: "high", mpId: "mp-fe3co" },
        { id: "alnico", formula: "AlNiCo", fullName: "Aluminum Nickel Cobalt", score: 41, status: "rejected", reason: "Coercivity too low", magneticMoment: "moderate", thermalStability: "good", formationEnergy: "stable", chinaDependency: "medium", supplyChainRisk: "medium", mpId: "mp-alnico" },
        { id: "fept",   formula: "FePt",   fullName: "Iron Platinum", score: 22, status: "rejected", reason: "Pt from South Africa/Russia", magneticMoment: "strong", thermalStability: "good", formationEnergy: "stable", chinaDependency: "low", supplyChainRisk: "very high", mpId: "mp-fept" },
      ],
    },
    {
      iteration: 2,
      candidatesTested: 31,
      bestScore: 61,
      branchedFrom: "fe3co",
      candidates: [
        { id: "fe2n", formula: "Fe₂N", fullName: "Iron Nitride", score: 33, status: "rejected", reason: "Crystal structure unstable", magneticMoment: "moderate", thermalStability: "unstable", formationEnergy: "unfavorable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe2n" },
        { id: "fe8n", formula: "Fe₈N", fullName: "Iron-rich Nitride", score: 61, status: "explored", isBest: true, reason: "Thermal stability below spec", magneticMoment: "good", thermalStability: "breaks down at 200°C", formationEnergy: "near stable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe8n" },
        { id: "fe4n", formula: "Fe₄N", fullName: "Iron Nitride", score: 45, status: "rejected", reason: "Magnetic moment too low", magneticMoment: "1.8 μB", thermalStability: "adequate", formationEnergy: "stable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe4n" },
        { id: "fen",  formula: "FeN",  fullName: "Iron Mononitride", score: 29, status: "rejected", reason: "Antiferromagnetic", magneticMoment: "none", thermalStability: "poor", formationEnergy: "unfavorable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fen" },
      ],
    },
    {
      iteration: 3,
      candidatesTested: 22,
      bestScore: 87,
      branchedFrom: "fe8n",
      candidates: [
        { id: "fe8n2",  formula: "Fe₈N₂",  fullName: "Dense Iron Nitride", score: 58, status: "rejected", reason: "Stability still below 350°C", magneticMoment: "good", thermalStability: "below 350°C", formationEnergy: "unfavorable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe8n2" },
        { id: "fe16n2", formula: "Fe₁₆N₂", fullName: "Iron Nitride (alpha-prime phase)", score: 87, status: "winner", reason: "Meets all spec — converged", magneticMoment: "2.9 μB", thermalStability: "Stable to 400°C", formationEnergy: "−0.34 eV/atom", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe16n2" },
        { id: "fe12n",  formula: "Fe₁₂N",  fullName: "Iron Nitride", score: 71, status: "rejected", reason: "Metastable at scale", magneticMoment: "close to spec", thermalStability: "adequate", formationEnergy: "metastable", chinaDependency: "0%", supplyChainRisk: "low", mpId: "mp-fe12n" },
      ],
    },
  ],
  converged: true,
  finalWinner: "fe16n2",
}

// ── App-level state shape ─────────────────────────────────────
export const mockAppState = {
  isDemo:         true,
  isRunning:      false,
  isComplete:     true,
  hypothesis:     mockHypothesis,
  iterations:     mockIterations,
  finalCandidate: mockFinalCandidate,
  decisionLog:    mockDecisionLog,
  decisionTree:   mockDecisionTree,
  logSummary:     mockLogSummary,
  portfolio:      mockStructuredDecisionLog.portfolio,
  ineligible:     mockStructuredDecisionLog.ineligible,
  testQueue:      mockStructuredDecisionLog.testQueue,
  constraints:    mockStructuredDecisionLog.constraints,
  provenanceTree: mockStructuredDecisionLog.provenanceTree,
}
