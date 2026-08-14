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
MAX_CONCENTRATION_PCT = 0.20     # Max 20% of total portfolio value in Equity
CRYPTO_MAX_CONCENTRATION_PCT = 0.05 # Max 5% of portfolio value for Crypto
MAX_ORDER_SIZE_GBP = 5000.0      # Hard cap of £5,000 per Equity trade
OPTIONS_MAX_ORDER_SIZE_GBP = 2000.0 # Strict £2,000 cap for Options trades
RESTRICTED_ASSETS = {"GME", "AMC", "DOGE", "PEPE"}  # Forbidden high-risk assets

# Hardcoded FX Rates (Base: GBP)
FX_RATES = {
    "GBP": 1.0,
    "USD": 0.78,
    "EUR": 0.85
}

def get_gbp_value(amount: float, currency: str) -> float:
    rate = FX_RATES.get(currency.upper(), 1.0)
    return amount * rate

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

def run_risk_audit(proposed_trade: dict, portfolio_value: float, holdings: Dict[str, float], human_override_token: str = None) -> dict:
    """
    Evaluates a proposed trade against FCA-aligned deterministic guardrails.
    Returns a dictionary matching the RiskAssessment Pydantic schema.
    """
    violations = []
    
    ticker = proposed_trade.get("ticker", "").upper()
    action = proposed_trade.get("action", "").lower()
    asset_class = proposed_trade.get("asset_class", "EQUITY").upper()
    currency = proposed_trade.get("currency", "GBP").upper()
    
    try:
        amount = float(proposed_trade.get("amount", 0.0))
        amount_gbp = get_gbp_value(amount, currency)
    except (TypeError, ValueError):
        return {
            "approved": False,
            "reason": "Invalid amount provided.",
            "violations": ["amount must be a valid number."],
            "requires_human_approval": False
        }
    
    # 0. High Risk Check (HITL - Human-In-The-Loop)
    is_high_risk = amount_gbp >= 50000.0 or asset_class == "CRYPTO"
    
    if is_high_risk:
        if human_override_token == "OVERRIDE_AUTH_123":
            return {
                "approved": True,
                "reason": "Senior Risk Officer Override Authorized.",
                "violations": [],
                "requires_human_approval": False
            }
        else:
            return {
                "approved": False,
                "reason": "High-Risk Trade. Awaiting Senior Risk Officer Approval.",
                "violations": [f"Trade amount (£{amount_gbp:.2f}) or Asset Class ({asset_class}) requires HITL override."],
                "requires_human_approval": True
            }

    # 1. Restricted Asset Check
    if ticker in RESTRICTED_ASSETS:
        violations.append(f"Asset '{ticker}' is on the restricted high-risk list.")
        
    # 2. Order Size Check (Asset-class dependent)
    max_order = OPTIONS_MAX_ORDER_SIZE_GBP if asset_class == "OPTION" else MAX_ORDER_SIZE_GBP
    if amount_gbp > max_order:
        violations.append(f"Order size £{amount_gbp:.2f} exceeds the {asset_class} maximum allowed £{max_order:.2f}.")
        
    # 3. Concentration Risk Check (Only checked on BUY)
    if action == "buy":
        max_concentration = CRYPTO_MAX_CONCENTRATION_PCT if asset_class == "CRYPTO" else MAX_CONCENTRATION_PCT
        
        current_holding = holdings.get(ticker, 0.0) # Assuming holding dict values are already in GBP
        new_holding = current_holding + amount_gbp
        # Calculate new concentration ratio. (Assuming portfolio_value represents current total equity in GBP)
        concentration = new_holding / portfolio_value
        if concentration > max_concentration:
            violations.append(
                f"Post-trade concentration of {ticker} ({concentration*100:.1f}%) "
                f"exceeds the {asset_class} regulatory limit of {max_concentration*100:.1f}%."
            )
            
    if violations:
        return {
            "approved": False,
            "reason": "Failed FCA deterministic risk guardrails.",
            "violations": violations,
            "requires_human_approval": False
        }
    
    return {
        "approved": True,
        "reason": "Passed all deterministic risk checks.",
        "violations": [],
        "requires_human_approval": False
    }
