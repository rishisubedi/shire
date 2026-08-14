from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator
from pydantic import BaseModel, Field

class ProposedTrade(BaseModel):
    """Structured output expected from the Analyst Agent."""
    ticker: str = Field(..., description="The stock or crypto ticker symbol (e.g., AAPL, AZN, BTC)")
    action: str = Field(..., description="Action to perform: 'buy' or 'sell'")
    amount: float = Field(..., description="Total notional value of the trade", ge=0)
    currency: str = Field(..., description="The currency of the trade: 'GBP', 'USD', or 'EUR'")
    asset_class: str = Field(..., description="The asset class: 'EQUITY', 'CRYPTO', or 'OPTION'")

class RiskAssessment(BaseModel):
    """Deterministic assessment result from the Risk Gatekeeper."""
    approved: bool
    reason: str
    violations: List[str] = Field(default_factory=list)
    requires_human_approval: bool = False

class ShireState(TypedDict):
    """
    The shared state of the LangGraph execution flow.
    Represents the full context of a single transaction lifecycle.
    """
    # Context (Inputs)
    market_context: str
    portfolio_value: float
    holdings: Dict[str, float]
    human_override_token: Optional[str]
    
    
    # Workflow Progression
    proposed_trade: Optional[ProposedTrade]
    risk_assessment: Optional[RiskAssessment]
    approval_signature: Optional[str]
    execution_payload: Optional[Dict[str, Any]]
    
    # Audit Trail (Append-only logs)
    logs: Annotated[List[str], operator.add]
