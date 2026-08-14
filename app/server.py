from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict
import os
from dotenv import load_dotenv

load_dotenv()

from .graph import build_graph
from .ingress import SemanticDebiaser
from .egress import EgressGuardrail, EgressViolationError
from .agents import recommend_trades

app = FastAPI(
    title="Shire Zero-Trust Engine API",
    description="API for evaluating financial trade flows using LangGraph and strict determinism.",
    version="1.0.0"
)

# Initialize the LangGraph
shire_graph = build_graph()

class RunSimulationRequest(BaseModel):
    market_context: str
    portfolio_value: float = 100000.0
    holdings: Dict[str, float] = {}
    human_override_token: str = None

class RecommendRequest(BaseModel):
    portfolio_value: float = 100000.0
    holdings: Dict[str, float] = {}

@app.post("/api/recommend")
async def get_recommendations(req: RecommendRequest):
    """Generates beginner-friendly safe trade recommendations."""
    return recommend_trades(req.portfolio_value, req.holdings)

@app.post("/api/run")
async def run_simulation(req: RunSimulationRequest):
    """
    Executes a LangGraph trade simulation given a market context and portfolio.
    Routes through Ingress Security -> LangGraph Consensus Brain -> Egress Guardrail.
    """
    # 1. Ingress Security Layer (Semantic De-biasing)
    cleaned_context, ingress_logs = SemanticDebiaser.process(req.market_context)

    initial_state = {
        "market_context": cleaned_context,
        "portfolio_value": req.portfolio_value,
        "holdings": req.holdings,
        "human_override_token": req.human_override_token,
        "logs": ingress_logs
    }
    
    try:
        # 2. Isolated LangGraph Orchestration Engine
        final_state = shire_graph.invoke(initial_state)
        
        # 3. Egress Tool-Calling Guardrail (Runtime Barrier)
        execution_payload = final_state.get("execution_payload")
        if execution_payload:
            try:
                validated_payload, egress_logs = EgressGuardrail.validate_and_format(execution_payload)
                final_state["logs"].extend(egress_logs)
                final_state["execution_payload"] = validated_payload
            except EgressViolationError as e:
                final_state["logs"].append(f"🛑 EGRESS RUNTIME CONNECTION DROPPED: {str(e)}")
                final_state["execution_payload"] = None

        return final_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Configure static file serving for the frontend dashboard
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_dashboard():
    """Serves the main frontend UI dashboard."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Shire API is running, but frontend/index.html was not found."}
