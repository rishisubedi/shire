import hmac
import hashlib
import json
import secrets
import os
from typing import Dict

# In a production environment, this key would be injected securely via AWS KMS / HashiCorp Vault.
# It is used by the Risk Gatekeeper to sign approved trades, preventing downstream nodes (Execution)
# from acting on state that was tampered with after the risk audit.
SECRET_KEY = os.getenv("SHIRE_HMAC_SECRET", "super_secret_shire_key_2026").encode('utf-8')

# ==========================================
# FCA-Aligned Deterministic Risk Guardrails
# ==========================================
MAX_CONCENTRATION_PCT = 0.20     # Max 20% of total portfolio value in a single asset
MAX_ORDER_SIZE_GBP = 5000.0      # Hard cap of £5,000 per individual trade
RESTRICTED_ASSETS = {"GME", "AMC", "DOGE", "PEPE"}  # Meme stocks / forbidden high-risk assets


def generate_trade_signature(trade_data: dict) -> str:
    """
    Generates a cryptographic signature (HMAC-SHA256) for a trade payload.
    Uses sort_keys=True to ensure stable JSON serialization.
    """
    payload = json.dumps(trade_data, sort_keys=True).encode('utf-8')
    return hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()

def verify_trade_signature(trade_data: dict, signature: str) -> bool:
    """
    Verifies the trade payload signature securely.
    Uses secrets.compare_digest to prevent timing attacks.
    """
    if not signature:
        return False
    expected_sig = generate_trade_signature(trade_data)
    return secrets.compare_digest(expected_sig, signature)

def run_risk_audit(proposed_trade: dict, portfolio_value: float, holdings: Dict[str, float]) -> dict:
    """
    Evaluates a proposed trade against FCA-aligned deterministic guardrails.
    Returns a dictionary matching the RiskAssessment Pydantic schema.
    """
    violations = []
    
    ticker = proposed_trade.get("ticker", "").upper()
    action = proposed_trade.get("action", "").lower()
    
    try:
        amount = float(proposed_trade.get("amount_gbp", 0.0))
    except (TypeError, ValueError):
        return {
            "approved": False,
            "reason": "Invalid amount_gbp provided.",
            "violations": ["amount_gbp must be a valid number."]
        }
    
    # 1. Restricted Asset Check
    if ticker in RESTRICTED_ASSETS:
        violations.append(f"Asset '{ticker}' is on the restricted high-risk list.")
        
    # 2. Order Size Check
    if amount > MAX_ORDER_SIZE_GBP:
        violations.append(f"Order size £{amount:.2f} exceeds the maximum allowed £{MAX_ORDER_SIZE_GBP:.2f}.")
        
    # 3. Concentration Risk Check (Only checked on BUY)
    if action == "buy":
        current_holding = holdings.get(ticker, 0.0)
        new_holding = current_holding + amount
        # Calculate new concentration ratio. (Assuming portfolio_value represents current total equity)
        concentration = new_holding / portfolio_value
        if concentration > MAX_CONCENTRATION_PCT:
            violations.append(
                f"Post-trade concentration of {ticker} ({concentration*100:.1f}%) "
                f"exceeds the {MAX_CONCENTRATION_PCT*100:.1f}% regulatory limit."
            )
            
    if violations:
        return {
            "approved": False,
            "reason": "Failed FCA deterministic risk guardrails.",
            "violations": violations
        }
    
    return {
        "approved": True,
        "reason": "Passed all deterministic risk checks.",
        "violations": []
    }
