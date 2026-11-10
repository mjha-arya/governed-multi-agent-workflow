"""The governed, API-mediated data access layer -- the heart of the JD's hard requirement:
"agents never touch raw database credentials directly."

Every path to enterprise data goes through here. This layer HOLDS the credentials/connection
(from a secret store / IAM role) inside deterministic, policy-checked functions; agents only ever
pass a natural-language query or an approved tool name. The credential object is never returned to,
or visible to, the model -- exactly the "harness holds the privilege, not the agent" pattern.

Two Snowflake Cortex seams (Analyst = NL->SQL over a semantic model; Search = RAG over docs) and
one MCP seam. All three are stubbed with deterministic fixtures so the workflow runs offline; the
real client slots in behind each `_connect`/`_call` with no change to the agent-facing signature.

Governance: each accessor is tagged with the Shiva Capability it exercises, and `invoke()` runs
the calling agent's DECLARED capabilities through Shiva's gate BEFORE executing -- so an agent that
reaches for data it wasn't granted is blocked here, at the boundary, before any query runs.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Callable

from shiva.capabilities import Capability   # reuse Shiva's taxonomy + gate (the whole point)
from shiva import gate
from shiva.ir import AgentSpec, Skill


# ---- credential handling: loaded here, NEVER handed to an agent -------------------------------
def _secret(name: str) -> str:
    """Fetch a secret from the environment / secret manager. In prod this is AWS Secrets Manager
    or Azure Key Vault via the service's IAM role -- the agent has no path to this function."""
    return os.environ.get(name, f"<{name}:not-set-offline>")


# ---- Snowflake Cortex Search (RAG over unstructured enterprise docs) --------------------------
_DOC_FIXTURES = {
    "return policy": "KB-114: Customers may return items within 30 days with proof of purchase.",
    "wire transfer": "KB-207: International wire transfers post in 1-3 business days; cutoff 4pm ET.",
    "kyc": "KB-330: KYC re-verification is required every 24 months for active accounts.",
}


def _cortex_search(query: str) -> "list[str]":
    # real: snowflake.connector.connect(... _secret('SNOWFLAKE_PAT') ...);
    #       SELECT * FROM TABLE(CORTEX_SEARCH_SERVICE(...))
    _ = _secret("SNOWFLAKE_PAT")  # held here, not exposed
    q = query.lower()
    return [doc for key, doc in _DOC_FIXTURES.items() if key in q] or \
           ["No matching enterprise document found."]


# ---- Snowflake Cortex Analyst (NL -> governed SQL over a semantic model) ----------------------
def _cortex_analyst(question: str) -> "list[dict]":
    # real: POST /api/v2/cortex/analyst/message with the semantic model; execute the returned SQL
    #       under a SCOPED read-only role -- never raw admin creds.
    _ = _secret("SNOWFLAKE_PAT")
    q = question.lower()
    if "open tickets" in q or "how many" in q:
        return [{"metric": "open_tickets", "value": 42, "as_of": "2026-07-12"}]
    if "refund" in q:
        return [{"metric": "refunds_last_30d", "value": 128, "currency": "USD"}]
    return [{"note": "no matching governed metric"}]


# ---- MCP (Model Context Protocol) tool call --------------------------------------------------
def _mcp_call(server: str, tool: str, args: dict) -> str:
    # real: an MCP client session to `server`, calling `tool` -- the standardized, governed
    #       tool interface. Stubbed to echo so the graph runs offline.
    return f"[mcp:{server}] {tool}({args}) -> ok (stub)"


@dataclass
class Accessor:
    name: str
    capability: Capability
    fn: Callable[..., Any]


# The registry of governed accessors, each capability-tagged for the gate.
_ACCESSORS = {
    "cortex_search":  Accessor("cortex_search",  Capability.MEMORY_RETRIEVAL, _cortex_search),
    "cortex_analyst": Accessor("cortex_analyst", Capability.EXTERNAL_API,     _cortex_analyst),
    "mcp_call":       Accessor("mcp_call",       Capability.EXTERNAL_API,     _mcp_call),
}


class GovernedAccessLayer:
    """The single door to enterprise data. Agents call `invoke`; the gate decides; creds stay here."""

    def invoke(self, agent_name: str, declared: "list[Capability]", accessor: str,
               *args, trace: "list[dict] | None" = None, **kwargs):
        acc = _ACCESSORS.get(accessor)
        if acc is None:
            raise ValueError(f"no such governed accessor: {accessor}")

        # Shiva gate: is THIS agent allowed to exercise THIS capability? Blocked before executing.
        spec = AgentSpec(name=agent_name, purpose="",
                         skills=[Skill(name="main", purpose="", declared_capabilities=declared)])
        decision = gate.evaluate(spec, "main", [acc.capability])
        blocked = decision.verdict == "quarantine" or acc.capability in decision.delta

        if blocked:
            result = (f"[gate] blocked {agent_name} -> {accessor}: "
                      f"undeclared capability {acc.capability.value}")
        else:
            result = acc.fn(*args, **kwargs)   # creds used INSIDE here; never returned to caller

        if trace is not None:
            trace.append({"agent": agent_name, "accessor": accessor,
                          "capability": acc.capability.value, "blocked": blocked})
        if blocked:
            raise PermissionError(result)
        return result
