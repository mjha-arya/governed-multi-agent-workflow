"""The shared workflow state that flows through the multi-agent graph.

In LangGraph this is your `StateGraph` schema (a TypedDict); nodes read it and return partial
updates that get merged in. We keep it a plain dataclass so the prototype runs with no deps,
but the shape is the same one you'd hand LangGraph's StateGraph(WorkflowState).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowState:
    request: str                                  # the user's question
    route: str = ""                               # supervisor's routing decision
    retrieved_docs: "list[str]" = field(default_factory=list)   # from Cortex Search (RAG)
    analytics_rows: "list[dict]" = field(default_factory=list)  # from Cortex Analyst (NL->SQL)
    draft_answer: str = ""
    compliance_verdict: str = ""                  # "pass" | "blocked: <reason>"
    final_answer: str = ""
    # A2A message log + governed-access trace -- the audit surface Shiva proves over.
    messages: "list[dict]" = field(default_factory=list)
    access_trace: "list[dict]" = field(default_factory=list)

    def say(self, agent: str, content: str) -> None:
        """Agent-to-agent (A2A) message onto the shared bus."""
        self.messages.append({"from": agent, "content": content})

    def as_dict(self) -> "dict[str, Any]":
        return {
            "request": self.request,
            "route": self.route,
            "retrieved_docs": self.retrieved_docs,
            "analytics_rows": self.analytics_rows,
            "draft_answer": self.draft_answer,
            "compliance_verdict": self.compliance_verdict,
            "final_answer": self.final_answer,
            "messages": self.messages,
            "access_trace": self.access_trace,
        }
