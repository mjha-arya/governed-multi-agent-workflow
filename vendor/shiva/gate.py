"""The capability gate — Kartikeya in code.

Gate = Blast Radius x Capability Delta. Compares a skill's DECLARED capability set
against the OBSERVED (actual) capabilities of a call, and decides allow/flag/quarantine.
This is the same object the compiler runs at design time and that ships INSIDE the agent
to run at runtime."""
from __future__ import annotations
from dataclasses import dataclass
from .capabilities import Capability, BLAST_RADIUS_WEIGHT
from .ir import AgentSpec

# Thresholds (tunable). An undeclared capability whose blast weight >= this quarantines.
QUARANTINE_BLAST = 3


@dataclass
class GateDecision:
    skill: str
    declared: "list[Capability]"
    observed: "list[Capability]"
    delta: "list[Capability]"   # observed - declared = the UNJUSTIFIED capability
    blast_radius: int           # sum of the delta's weights (x reach; reach=1 in v1)
    verdict: str                # "allow" | "flag" | "quarantine"

    def as_dict(self) -> dict:
        return {
            "skill": self.skill,
            "declared": [c.value for c in self.declared],
            "observed": [c.value for c in self.observed],
            "delta": [c.value for c in self.delta],
            "blast_radius": self.blast_radius,
            "verdict": self.verdict,
        }


def evaluate(spec: AgentSpec, skill_name: str, observed: "list[Capability]") -> GateDecision:
    skill = spec.skill(skill_name)
    declared = list(skill.declared_capabilities) if skill else []
    declared_set = set(declared)
    delta = [c for c in observed if c not in declared_set]
    blast = sum(BLAST_RADIUS_WEIGHT.get(c, 1) for c in delta)
    if not delta:
        verdict = "allow"
    elif blast >= QUARANTINE_BLAST:
        verdict = "quarantine"
    else:
        verdict = "flag"
    return GateDecision(skill_name, declared, list(observed), delta, blast, verdict)
