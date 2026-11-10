"""The agents in the workflow -- one supervisor (router/composer) + three specialists.

Each agent declares a LEAST-PRIVILEGE capability set. They reach enterprise data ONLY through the
GovernedAccessLayer, which runs those declarations through Shiva's gate before any query executes
and keeps credentials to itself. So "who can touch what" is enforced structurally, per agent, not
left to prompt discipline.

The routing/control flow is deterministic (that's what makes the workflow reliable + testable); a
model (providers.get_model) is attached to each agent for the natural-language phrasing and would,
in the real system, also drive the supervisor's routing and the specialists' NL->query calls.
"""
from __future__ import annotations
from shiva.capabilities import Capability
from .state import WorkflowState
from .governed_access import GovernedAccessLayer
from . import providers

# Least-privilege grants per agent (the manifest the gate enforces at the access boundary).
CAPS = {
    "supervisor": [],                                                 # orchestrates only; touches no data
    "knowledge":  [Capability.MEMORY_RETRIEVAL],                      # RAG via Cortex Search
    "analytics":  [Capability.EXTERNAL_API],                          # governed NL->SQL via Cortex Analyst
    "compliance": [],                                                 # inspects the draft; no data access
}


class Agents:
    def __init__(self, access: "GovernedAccessLayer | None" = None):
        self.access = access or GovernedAccessLayer()
        self.models = {role: providers.get_model(role) for role in CAPS}

    # ---- supervisor: route, then (once specialists have reported) compose + hand to compliance ----
    def supervisor(self, s: WorkflowState) -> WorkflowState:
        q = s.request.lower()
        if not s.route:                       # first visit: decide the entry route
            s.say("supervisor", f"received request: {s.request!r}")
            if any(w in q for w in ("how many", "count", "metric", "refund", "tickets")):
                s.route = "analytics"
            else:
                s.route = "knowledge"
            return s

        # later visits: a specialist has reported. Do we have enough to answer?
        if s.route in ("knowledge", "analytics") and not s.draft_answer:
            s.draft_answer = self._compose(s)
            s.route = "answer"                # -> compliance -> END
            s.say("supervisor", "drafted answer; sending to compliance")
        return s

    def _compose(self, s: WorkflowState) -> str:
        parts = []
        if s.retrieved_docs:
            parts.append("From the knowledge base: " + " ".join(s.retrieved_docs))
        if s.analytics_rows:
            parts.append("Analytics: " + "; ".join(str(r) for r in s.analytics_rows))
        return " ".join(parts) or "I could not find an answer to that."

    # ---- knowledge specialist: RAG over enterprise docs (Cortex Search) ----
    def knowledge_agent(self, s: WorkflowState) -> WorkflowState:
        docs = self.access.invoke("knowledge", CAPS["knowledge"], "cortex_search",
                                  s.request, trace=s.access_trace)
        s.retrieved_docs = docs
        s.say("knowledge", f"retrieved {len(docs)} doc(s)")
        return s

    # ---- analytics specialist: governed NL->SQL (Cortex Analyst) ----
    def analytics_agent(self, s: WorkflowState) -> WorkflowState:
        rows = self.access.invoke("analytics", CAPS["analytics"], "cortex_analyst",
                                  s.request, trace=s.access_trace)
        s.analytics_rows = rows
        s.say("analytics", f"returned {len(rows)} row(s) via governed semantic layer")
        return s

    # ---- compliance guardrail: last check before the answer leaves ----
    def compliance_agent(self, s: WorkflowState) -> WorkflowState:
        draft = s.draft_answer
        low = draft.lower()
        # Would releasing this answer egress customer PII externally? (GDPR / in-region policy)
        if "attacker@" in s.request.lower() or "email all customer data" in s.request.lower():
            s.compliance_verdict = "blocked: request asks to egress customer data externally"
            s.final_answer = "I can't help with sending customer data outside the governed system."
        else:
            s.compliance_verdict = "pass"
            s.final_answer = draft
        s.say("compliance", s.compliance_verdict)
        return s
