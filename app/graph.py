from langgraph.graph import StateGraph, END
from typing import Literal
from .state import ShireState
from .agents import analyst_node, gatekeeper_node, execution_node

def route_gatekeeper(state: ShireState) -> Literal["execution", "__end__"]:
    """
    Conditional edge routing based on Gatekeeper approval.
    If the Gatekeeper rejects the trade, the execution path is unreachable.
    """
    assessment = state.get("risk_assessment", {})
    if assessment.get("approved"):
        return "execution"
    return "__end__"

def build_graph():
    """
    Builds and compiles the Shire LangGraph.
    Enforces the Zero-Trust Three-Key Consensus Protocol.
    """
    workflow = StateGraph(ShireState)
    
    # Add Agent Nodes
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("execution", execution_node)
    
    # Define Workflow Edges
    workflow.set_entry_point("analyst")
    workflow.add_edge("analyst", "gatekeeper")
    workflow.add_conditional_edges(
        "gatekeeper", 
        route_gatekeeper,
        {
            "execution": "execution",
            "__end__": END
        }
    )
    workflow.add_edge("execution", END)
    
    return workflow.compile()
