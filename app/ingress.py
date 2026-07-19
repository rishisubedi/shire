import re
import logging

logger = logging.getLogger(__name__)

class SemanticDebiaser:
    """
    Ingress Security Gate: Market Stream Hydrator & Semantic De-biasing.
    Standardizes raw textual context, stripping out manipulative prompt injections
    before it reaches the Analyst Node.
    """
    # Regex patterns for malicious intent
    MALICIOUS_PATTERNS = [
        r"(ignore|override|bypass)\s+(previous\s+instructions|security|rules|guardrails|limits)",
        r"execute\s+maximum\s+limit\s+bypass"
    ]

    @classmethod
    def process(cls, raw_context: str) -> tuple[str, list[str]]:
        logs = ["🛡️ INGRESS GATE: Hydrating stream and scanning context..."]
        cleaned_context = raw_context
        stripped_count = 0

        for pattern in cls.MALICIOUS_PATTERNS:
            matches = re.finditer(pattern, cleaned_context, flags=re.IGNORECASE)
            for match in matches:
                stripped_count += 1
                cleaned_context = cleaned_context.replace(match.group(0), "[REDACTED_BY_INGRESS]")

        if stripped_count > 0:
            logs.append(f"🚨 INGRESS ALERT: Neutralized {stripped_count} prompt injection vector(s). Malicious text stripped.")
        else:
            logs.append("✅ INGRESS GATE: Context is semantically clean.")

        return cleaned_context, logs
