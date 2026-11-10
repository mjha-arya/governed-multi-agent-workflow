"""The agent-spec IR — the minimal structured representation the compiler passes transform.
Deliberately small (start with a few fields, not sixty)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .capabilities import Capability


@dataclass
class Skill:
    name: str
    purpose: str
    declared_capabilities: "list[Capability]" = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "declared_capabilities": [c.value for c in self.declared_capabilities],
        }

    @staticmethod
    def from_dict(d: "dict[str, Any]") -> "Skill":
        return Skill(
            name=d["name"],
            purpose=d.get("purpose", ""),
            declared_capabilities=[Capability(c) for c in d.get("declared_capabilities", [])],
        )


@dataclass
class AgentSpec:
    name: str
    purpose: str
    skills: "list[Skill]" = field(default_factory=list)
    constraints: "dict[str, Any]" = field(default_factory=dict)

    def skill(self, name: str) -> "Skill | None":
        for s in self.skills:
            if s.name == name:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "skills": [s.to_dict() for s in self.skills],
            "constraints": self.constraints,
        }

    @staticmethod
    def from_dict(d: "dict[str, Any]") -> "AgentSpec":
        return AgentSpec(
            name=d["name"],
            purpose=d.get("purpose", ""),
            skills=[Skill.from_dict(s) for s in d.get("skills", [])],
            constraints=d.get("constraints", {}),
        )
