from langgraph.graph import StateGraph, END
from backend.src.graph.state import GraphState

from backend.src.graph.nodes import (
    VideoIndexerNode,
    AuditContentNode
)

def create_graph():
    """
Constructs and compiles the LangGraph workflow

Returns:
    Compiled Graph: runnable graph object for execution
"""

    graph = StateGraph(GraphState)

    graph.add_node("indexer",VideoIndexerNode)
    graph.add_node("auditor",AuditContentNode)

    graph.add_edge(START, "indexer")

    graph.add_edge("indexer", "auditor")

    graph.add_edge("auditor", END)

    app = graph.compile()

    return app

app = create_graph()