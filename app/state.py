from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator
from pydantic import BaseModel, Field

class ProposedTrade(BaseModel):
    """Structured output expected from the Analyst Agent."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., AAPL, AZN, VOD)")
    action: str = Field(..., description="Action to perform: 'buy' or 'sell'")
    amount_gbp: float = Field(..., description="Total value of the trade in GBP", ge=0)

class RiskAssessment(BaseModel):
    """Deterministic assessment result from the Risk Gatekeeper."""
    approved: bool
    reason: str
    violations: List[str] = Field(default_factory=list)

class ShireState(TypedDict):
    """
    The shared state of the LangGraph execution flow.
    Represents the full context of a single transaction lifecycle.
    """
    # Context (Inputs)
    market_context: str
    portfolio_value: float
    holdings: Dict[str, float]
    
    # Workflow Progression
    proposed_trade: Optional[ProposedTrade]
    risk_assessment: Optional[RiskAssessment]
    approval_signature: Optional[str]
    execution_payload: Optional[Dict[str, Any]]
    
    # Audit Trail (Append-only logs)
    logs: Annotated[List[str], operator.add]
