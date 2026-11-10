# Governed Multi-Agent Workflow
### (AWS Bedrock · Azure AI Foundry · LangGraph · MCP · Snowflake Cortex)

A runnable prototype of a **governed multi-agent workflow** for a regulated (financial-services)
enterprise. The differentiator: **every agent is capability-gated** by a minimal open version of the
[Shiva](https://github.com/mjha-arya/shiva) gate (`vendor/shiva/`, *Gate = Blast Radius × Capability Delta*),
so "which agent may touch which data" is enforced *structurally*, not by prompt discipline.

> Status: **runs today, fully offline & deterministic** (no keys, no cloud). Every external
> integration is a clearly-marked *seam* with the real SDK call noted inline. This is a
> portfolio/architecture prototype, not a production deployment.

## What it does
A support-analytics assistant. A **supervisor** agent routes each request to the right specialist,
specialists do the work through a **governed access layer**, and a **compliance** agent checks the
answer before it leaves.

```
        START → supervisor ─┬─→ knowledge  (RAG / Cortex Search) ──┐
                            ├─→ analytics  (NL→SQL / Cortex Analyst)┤→ supervisor → compliance → END
                            └─────────────── answer ────────────────┘
```

## Enterprise requirement → where it lives
| Requirement | In this prototype |
|---|---|
| Multi-agent workflows using **LangGraph (or equivalent orchestration)** | `graph.py` — a minimal engine that **mirrors LangGraph's `StateGraph` API** (`add_node` / `add_conditional_edges` / `compile` / `invoke`); swap is near-mechanical |
| **RAG** over enterprise data | `governed_access.cortex_search` (Snowflake **Cortex Search** seam) → `knowledge_agent` |
| **Tool / function-calling** | governed accessors are the tools; agents request, the layer executes |
| **Governed access layer — agents never touch raw DB credentials** | `governed_access.py` — creds loaded via `_secret()` and used **inside** the layer; never returned to any agent. The gate blocks an agent reaching beyond its grant |
| **Snowflake Cortex (Analyst / Search)** | `cortex_analyst` (NL→SQL over a semantic model) + `cortex_search` seams |
| **MCP** | `governed_access._mcp_call` — MCP client seam |
| **AWS Bedrock / Azure AI Foundry** | `providers.py` — model routing across Bedrock / Foundry / offline, per agent role |
| **Evals into every agent you ship** | `evals.py` — 4 cases incl. an adversarial least-privilege probe |
| **A2A patterns** | `state.py` message bus; supervisor↔specialist handoff in `graph.py` |
| **Regulated-industry / GDPR** | `compliance_agent` blocks external customer-data egress; in-region/zero-retention constraints carried in the brief |

## The governance story (the differentiator)
Each agent has a **least-privilege capability manifest** (`agents.CAPS`): the knowledge agent gets
`memory-retrieval`, analytics gets `external-api`, the supervisor and compliance agents get *no*
data capabilities at all. The `GovernedAccessLayer` runs each data call through **Shiva's gate**
(`shiva.gate`) *before executing*. An agent that reaches beyond its grant is **blocked at the
boundary** — proven by the `least_privilege_enforced_at_access_layer` eval, where the knowledge
agent's attempt to run a governed analytics query is refused.

## Run it
No dependencies — Python 3.10+. From this folder:

    python src/run.py "What is the wire transfer policy?"   # RAG path
    python src/run.py "How many open tickets do we have?"   # governed-analytics path
    python src/run.py --evals                               # the shipped eval suite (4/4)

## Files
    src/
      state.py            shared workflow state (LangGraph-style schema) + A2A message bus
      graph.py            LangGraph-compatible orchestration engine + the workflow wiring
      agents.py           supervisor + knowledge / analytics / compliance specialists + CAPS manifest
      governed_access.py  the API-mediated data layer: Cortex Search/Analyst + MCP seams; holds creds
      providers.py        model routing: AWS Bedrock / Azure AI Foundry / offline fallback
      evals.py            workflow-level evals incl. the adversarial least-privilege probe
      run.py              entrypoint

## To make it real (the seams, in priority order)
1. `graph.py` → `from langgraph.graph import StateGraph` (keep node fns + wiring).
2. `governed_access.py` → real Snowflake `connector` + Cortex Analyst REST + an MCP client session.
3. `providers.py` → boto3 `bedrock-runtime.converse` and/or azure-ai-inference.
4. Attach each agent to the **Shiva harness loop** (`shiva.harness.Harness`) so specialists run a
   real gated tool-calling loop, not just deterministic control flow.

---
Built by **[Manish Jha](https://github.com/mjha-arya)**, secure and provable AI agents. MIT licensed; `vendor/shiva/` is a minimal open subset of the Shiva gate.
