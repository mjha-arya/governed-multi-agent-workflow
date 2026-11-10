"""A minimal, LangGraph-compatible orchestration engine + the enterprise workflow wiring.

Why a tiny engine instead of importing LangGraph: this prototype runs with zero dependencies.
The API deliberately MIRRORS LangGraph's StateGraph -- add_node / add_edge /
add_conditional_edges / set_entry_point / compile / invoke -- so migrating to the real thing is
a near-mechanical swap (drop this class, `from langgraph.graph import StateGraph`, keep the node
functions and wiring untouched). START/END are the same sentinels LangGraph uses.
"""
from __future__ import annotations
from typing import Callable
from .state import WorkflowState

START = "__start__"
END = "__end__"

NodeFn = Callable[[WorkflowState], WorkflowState]
Router = Callable[[WorkflowState], str]


class StateGraph:
    def __init__(self) -> None:
        self._nodes: "dict[str, NodeFn]" = {}
        self._edges: "dict[str, str]" = {}
        self._conditional: "dict[str, tuple[Router, dict[str, str]]]" = {}
        self._entry: str = ""
        self.max_hops = 25  # guardrail: a cyclic graph can't spin forever

    def add_node(self, name: str, fn: NodeFn) -> None:
        self._nodes[name] = fn

    def add_edge(self, src: str, dst: str) -> None:
        self._edges[src] = dst

    def add_conditional_edges(self, src: str, router: Router, mapping: "dict[str, str]") -> None:
        self._conditional[src] = (router, mapping)

    def set_entry_point(self, name: str) -> None:
        self._entry = name

    def compile(self) -> "StateGraph":
        if not self._entry:
            raise ValueError("no entry point set")
        return self

    def invoke(self, state: WorkflowState) -> WorkflowState:
        node = self._entry
        for _ in range(self.max_hops):
            if node == END:
                break
            fn = self._nodes.get(node)
            if fn is None:
                raise ValueError(f"unknown node: {node}")
            state = fn(state)
            if node in self._conditional:
                router, mapping = self._conditional[node]
                node = mapping.get(router(state), END)
            else:
                node = self._edges.get(node, END)
        return state


def build_graph(agents) -> StateGraph:
    """Wire the enterprise support-analytics workflow.

        START -> supervisor -> {knowledge | analytics | answer} -> supervisor -> compliance -> END

    The supervisor is the router (A2A orchestration); specialists do the work through the
    governed access layer; compliance is the final guardrail before the answer leaves.
    """
    g = StateGraph()
    g.add_node("supervisor", agents.supervisor)
    g.add_node("knowledge", agents.knowledge_agent)
    g.add_node("analytics", agents.analytics_agent)
    g.add_node("compliance", agents.compliance_agent)

    g.set_entry_point("supervisor")
    # supervisor decides where to go next based on state.route
    g.add_conditional_edges("supervisor", lambda s: s.route, {
        "knowledge": "knowledge",
        "analytics": "analytics",
        "answer": "compliance",   # supervisor has enough -> draft + compliance-check + done
    })
    # specialists always report back to the supervisor (A2A loop)
    g.add_edge("knowledge", "supervisor")
    g.add_edge("analytics", "supervisor")
    g.add_edge("compliance", END)
    return g.compile()
