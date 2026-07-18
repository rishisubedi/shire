from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict
import os

from .graph import build_graph

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

@app.post("/api/run")
async def run_simulation(req: RunSimulationRequest):
    """
    Executes a LangGraph trade simulation given a market context and portfolio.
    Returns the final graph state containing the logs, risk assessment, and execution payload.
    """
    initial_state = {
        "market_context": req.market_context,
        "portfolio_value": req.portfolio_value,
        "holdings": req.holdings,
        "logs": []
    }
    
    try:
        final_state = shire_graph.invoke(initial_state)
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
