from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Absolute Runtime Barrier Limit (Hardcoded safety cap)
ABSOLUTE_MAX_ORDER_SIZE = 100000.0

class StrictBrokerPayload(BaseModel):
    """
    Strict validation schema acting as the Runtime Barrier before Brokerage API transmission.
    """
    broker_action: str = Field(pattern="^EXECUTE_MARKET_ORDER$")
    asset: str = Field(min_length=1, max_length=10)
    side: str = Field(pattern="^(BUY|SELL)$")
    notional_value: float = Field(gt=0, le=ABSOLUTE_MAX_ORDER_SIZE)
    currency: str = Field(pattern="^GBP$")
    compliance_token: str = Field(min_length=32)
    execution_timestamp: str

class EgressViolationError(Exception):
    pass

class EgressGuardrail:
    """
    Egress Tool-Calling Guardrail: Final line of defense.
    Maps the schema parameters against a strict validation class. If any field contains corrupted 
    data or overflow variables, the runtime environment immediately flags and drops the connection.
    """
    @classmethod
    def validate_and_format(cls, raw_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], list[str]]:
        logs = ["🛡️ EGRESS GATE: Validating payload against strict structural barrier..."]
        
        try:
            # Strict schema parsing and validation
            validated = StrictBrokerPayload(**raw_payload)
            logs.append("✅ EGRESS GATE: Payload perfectly conforms to strict runtime schema. Ready for broker.")
            return validated.model_dump(), logs
        except ValidationError as e:
            logs.append(f"🛑 CRITICAL EGRESS FAILURE: Structural violation or parameter overflow detected.")
            for err in e.errors():
                logs.append(f"   - Field '{err['loc'][0]}': {err['msg']}")
            raise EgressViolationError("Payload failed Egress runtime barrier constraints.")
