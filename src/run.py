"""Entrypoint: run the multi-agent enterprise workflow, then its evals -- all Shiva-governed.

    python src/run.py "What is the wire transfer policy?"   # run one request through the graph
    python src/run.py --evals                                # run the shipped eval suite

Runs fully offline (deterministic). Set AWS/Azure/Snowflake env vars to light up the real seams.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Make the parent Shiva package importable (we reuse its capability taxonomy + gate).
_SHIVA_SRC = Path(__file__).resolve().parents[1] / "vendor"
sys.path.insert(0, str(_SHIVA_SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `src` is a package root

from src.agents import Agents            # noqa: E402
from src.graph import build_graph        # noqa: E402
from src.state import WorkflowState      # noqa: E402
from src import evals                    # noqa: E402

_LINE = "  " + "-" * 62


def run_one(request: str) -> None:
    graph = build_graph(Agents())
    state = graph.invoke(WorkflowState(request=request))
    print()
    print(f"  ENTERPRISE MULTI-AGENT WORKFLOW  --  request: {request!r}")
    print(_LINE)
    print("  A2A message flow:")
    for m in state.messages:
        print(f"    {m['from']:<11}| {m['content']}")
    print("  Governed data access (creds never seen by agents):")
    for a in state.access_trace:
        tag = "BLOCKED" if a["blocked"] else "ok"
        print(f"    [{tag}] {a['agent']} -> {a['accessor']} ({a['capability']})")
    print(_LINE)
    print(f"  Compliance : {state.compliance_verdict}")
    print(f"  Answer     : {state.final_answer}")
    print()


def run_evals() -> None:
    results = evals.run_evals(Agents, build_graph)
    passed = sum(1 for r in results if r["passed"])
    print()
    print("  MULTI-AGENT WORKFLOW -- EVAL SUITE")
    print(_LINE)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"    [{mark}] {r['name']}")
    print(_LINE)
    print(f"  {passed}/{len(results)} eval cases passed")
    print()
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--evals":
        run_evals()
    else:
        run_one(" ".join(args) or "What is the wire transfer policy?")
