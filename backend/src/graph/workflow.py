from langgraph.graph import StateGraph, END
from backend.src.graph.state import VideoAuditState

from backend.src.graph.nodes import (
    index_video_node,
    audit_content_node
)

def create_graph():
    """
Constructs and compiles the LangGraph workflow

Returns:
    Compiled Graph: runnable graph object for execution
"""

    