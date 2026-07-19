import logging
from typing import Dict, Any

from .state import ShireState, ProposedTrade
from .risk_engine import run_risk_audit, generate_trade_signature, verify_trade_signature

logger = logging.getLogger(__name__)

def mock_analyst_llm(context: str) -> dict:
    """
    Mock LLM to ensure the demo works robustly out of the box without API keys.
    Simulates prompt injection detection and various trade proposals based on context keywords.
    """
    import re
    context_lower = context.lower()
    
    # Simulate Prompt Injection Vulnerability:
    # If the LLM has direct tools, it would execute this. Shire catches it downstream.
    if "override" in context_lower or "ignore" in context_lower or "bypass" in context_lower:
        return {"ticker": "GME", "action": "buy", "amount_gbp": 50000.0}
    
    # Regex to dynamically capture e.g. "buy 2000 of AAPL" or "sell 1500 MSFT"
    match = re.search(r'(buy|sell)\s+(?:£)?([\d\.]+)(?:\s+of)?\s+([a-zA-Z]+)', context_lower)
    if match:
        action = match.group(1)
        amount = float(match.group(2))
        ticker = match.group(3).upper()
        return {"ticker": ticker, "action": action, "amount_gbp": amount}
    
    if "vodafone" in context_lower:
        return {"ticker": "VOD", "action": "buy", "amount_gbp": 2000.0}
    
    if "astrazeneca" in context_lower and "10000" in context_lower:
        return {"ticker": "AZN", "action": "buy", "amount_gbp": 10000.0}
        
    if "astrazeneca" in context_lower:
        return {"ticker": "AZN", "action": "buy", "amount_gbp": 3000.0}
        
    return {"ticker": "AAPL", "action": "buy", "amount_gbp": 1000.0}

def analyst_node(state: ShireState) -> Dict[str, Any]:
    """
    1. Analyst Agent
    Scans market context and proposes a trade. 
    SECURITY: This node HAS ZERO TOOL ACCESS. It can only propose state.
    """
    context = state.get("market_context", "")
    
    # In production:
    # llm = ChatOpenAI(model="gpt-4", temperature=0).with_structured_output(ProposedTrade)
    # trade = llm.invoke(context)
    
    raw_trade = mock_analyst_llm(context)
    proposed_trade = ProposedTrade(**raw_trade)
    
    log_msg = f"🔍 Analyst Agent proposed: {proposed_trade.action.upper()} £{proposed_trade.amount_gbp:,.2f} of {proposed_trade.ticker}"
    
    return {
        "proposed_trade": proposed_trade.model_dump(),
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
        "side": proposed_trade.get("action").upper(),
        "notional_value": proposed_trade.get("amount_gbp"),
        "currency": "GBP",
        "compliance_token": signature,
        "execution_timestamp": "now" # In real app, datetime.now().isoformat()
    }
    
    logs = [
        "✅ Execution Agent: Signature verified securely.",
        f"🚀 Execution Agent: Trade payload generated for broker -> {execution_payload['side']} {execution_payload['asset']} £{execution_payload['notional_value']:,.2f}"
    ]
    
    return {
        "execution_payload": execution_payload,
        "logs": logs
    }
