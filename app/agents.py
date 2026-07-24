import logging
from typing import Dict, Any, List
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import ShireState, ProposedTrade
from .risk_engine import run_risk_audit, generate_trade_signature, verify_trade_signature

logger = logging.getLogger(__name__)

class TradeRecommendation(BaseModel):
    rationale: str = Field(description="Why this trade is safe and diversified based on the current portfolio.")
    suggested_prompt: str = Field(description="A plain English string like 'Buy $1000 of AAPL'")

class RecommendationList(BaseModel):
    recommendations: List[TradeRecommendation]

def recommend_trades(portfolio_value: float, holdings: Dict[str, float]) -> dict:
    """Uses LLM to recommend 3 safe, diversified trades for a beginner user."""
    api_key = os.getenv("GOOGLE_API_KEY", "dummy_key")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7, google_api_key=api_key)
        structured_llm = llm.with_structured_output(RecommendationList)
        
        prompt = f"""
        You are a helpful, conservative financial advisor. 
        The user is a beginner. Their current portfolio value is {portfolio_value}.
        Their current holdings (in GBP) are: {holdings}.
        
        Suggest 3 safe, diversified trades (EQUITY only, no Crypto or Options) they could make right now to balance their portfolio.
        Ensure no single trade is larger than 4000 in notional value. 
        Provide a very friendly, jargon-free rationale for each.
        The suggested_prompt must be a simple natural language string like 'Buy $1000 of AAPL' or 'Buy £500 of VOD'.
        """
        
        result = structured_llm.invoke(prompt)
        return result.model_dump()
    except Exception as e:
        return {"error": str(e), "recommendations": []}

def analyst_node(state: ShireState) -> Dict[str, Any]:
    """
    1. Analyst Agent
    Scans market context and proposes a trade using a real LLM. 
    SECURITY: This node HAS ZERO TOOL ACCESS. It can only propose state.
    """
    context = state.get("market_context", "")
    
    # Initialize the real LLM with strict output formatting
    api_key = os.getenv("GOOGLE_API_KEY", "dummy_key")
    
    try:
        # We use gemini-1.5-flash as it is fast and supports structured outputs well.
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=api_key)
        structured_llm = llm.with_structured_output(ProposedTrade)
        
        prompt = f"""
        You are a highly sophisticated financial analyst agent. 
        Analyze the following market context and determine the requested trade action.
        Extract the ticker symbol, the action (buy or sell), the absolute amount, the currency (GBP, USD, EUR) based on the symbol (e.g. $, £, €), and the asset_class (EQUITY, CRYPTO, OPTION).
        
        Market Context:
        {context}
        """
        
        proposed_trade = structured_llm.invoke(prompt)
        
        # Determine appropriate symbol for logging
        sym = "£" if proposed_trade.currency == "GBP" else "$" if proposed_trade.currency == "USD" else "€"
        
        log_msg = f"🧠 Analyst LLM Reasoned Trade: {proposed_trade.action.upper()} {sym}{proposed_trade.amount:,.2f} of {proposed_trade.ticker} ({proposed_trade.asset_class})"
        
        return {
            "proposed_trade": proposed_trade.model_dump(),
            "logs": [log_msg]
        }
        
    except Exception as e:
        log_msg = f"❌ Analyst LLM Error (Check API Key): {str(e)}"
        return {
            "logs": [log_msg]
        }

def gatekeeper_node(state: ShireState) -> Dict[str, Any]:
    """
    2. Risk Gatekeeper
    Evaluates the proposed trade against FCA deterministic rules.
    If approved, appends a cryptographic signature.
    """
    proposed_trade = state.get("proposed_trade")
    if not proposed_trade:
        return {"logs": ["❌ Gatekeeper Error: No trade proposed."]}
        
    portfolio_value = state.get("portfolio_value", 0.0)
    holdings = state.get("holdings", {})
    
    assessment = run_risk_audit(proposed_trade, portfolio_value, holdings)
    
    logs = []
    signature = None
    
    if assessment["approved"]:
        signature = generate_trade_signature(proposed_trade)
        logs.append("✅ Gatekeeper: Trade PASSED all FCA risk checks.")
        logs.append("🔐 Gatekeeper: Cryptographic HMAC signature attached to state.")
    else:
        logs.append(f"⛔ Gatekeeper: Trade BLOCKED. Reason: {assessment['reason']}")
        for v in assessment["violations"]:
            logs.append(f"   - {v}")
            
    return {
        "risk_assessment": assessment,
        "approval_signature": signature,
        "logs": logs
    }

def execution_node(state: ShireState) -> Dict[str, Any]:
    """
    3. Execution Agent
    Validates the cryptographic signature. If valid, translates the state
    into a strict brokerage execution JSON schema.
    """
    assessment = state.get("risk_assessment", {})
    proposed_trade = state.get("proposed_trade", {})
    signature = state.get("approval_signature", "")
    
    if not assessment.get("approved"):
        return {"logs": ["🛑 Execution Halted: Trade was not approved by Gatekeeper."]}
        
    # ==========================================
    # SECURITY: ZERO-TRUST SIGNATURE VALIDATION
    # ==========================================
    if not verify_trade_signature(proposed_trade, signature):
        return {"logs": ["🚨 CRITICAL SECURITY ALERT: State tampering detected! Signature validation failed. Execution halted."]}
        
    # Translate into strict JSON payload for brokerage API
    execution_payload = {
        "broker_action": "EXECUTE_MARKET_ORDER",
        "asset": proposed_trade.get("ticker"),
        "asset_class": proposed_trade.get("asset_class"),
        "side": proposed_trade.get("action").upper(),
        "notional_value": proposed_trade.get("amount"),
        "currency": proposed_trade.get("currency"),
        "compliance_token": signature,
        "execution_timestamp": "now" # In real app, datetime.now().isoformat()
    }
    
    sym = "£" if execution_payload["currency"] == "GBP" else "$" if execution_payload["currency"] == "USD" else "€"
    
    logs = [
        "✅ Execution Agent: Signature verified securely.",
        f"🚀 Execution Agent: Trade payload generated for broker -> {execution_payload['side']} {execution_payload['asset']} {sym}{execution_payload['notional_value']:,.2f}"
    ]
    
    return {
        "execution_payload": execution_payload,
        "logs": logs
    }
