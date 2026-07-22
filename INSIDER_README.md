# Shire: Insider Documentation & Architecture Deep Dive

This document is intended for engineers and security auditors maintaining the Shire Zero-Trust Engine. It breaks down the internal mechanics of the state machine, the protective boundary layers, and the multi-currency FX routing.

---

## 1. The Outer Shell: Boundaries and Guardrails

The application is built on the philosophy of **Zero-Trust**. The LLM operates in a fully sandboxed "Inner Core". To reach it, or for the core to reach the outside world, data must pass through the Outer Shell.

### A. The Ingress Boundary (`app/ingress.py`)
*   **Role**: To prevent Prompt Injections.
*   **Mechanic**: Before a user's prompt (e.g., "Buy 100 shares of AAPL") is passed to the LLM, the `SemanticDebiaser` class intercepts it. It scans against a regex catalog of known manipulative phrases (e.g., "override", "ignore instructions"). If detected, these payloads are stripped out.

### B. The Egress Boundary (`app/egress.py`)
*   **Role**: To act as the final, immutable runtime barrier before sending a JSON payload to an actual brokerage (like Interactive Brokers or Alpaca).
*   **Mechanic**: Uses a strict Pydantic model (`StrictBrokerPayload`). Even if the entire Inner Core gets compromised, the Egress layer will mathematically reject the payload if `notional_value > 100,000`, if the `asset_class` is not recognized, or if the `currency` is not explicitly whitelisted (GBP, USD, EUR).

---

## 2. The Inner Core: LangGraph Orchestration (`app/agents.py`)

The Inner Core is a state machine powered by LangGraph. It passes a single immutable typed dictionary (`ShireState`) from node to node.

### Node 1: The Analyst (LLM)
*   **Logic**: Uses Google Gemini (via `langchain-google-genai`). We utilize the `.with_structured_output()` method to force the generative model to output a strict JSON structure (`ProposedTrade`).
*   **Capabilities**: It extracts the Ticker, Action (buy/sell), Asset Class (Equity, Crypto, Option), and Currency based on context symbols ($, £, €).
*   **Security**: The Analyst has **no tools**. It cannot execute code or make API calls. It can only append a proposal to the state.

### Node 2: The Risk Gatekeeper (`app/risk_engine.py`)
*   **Logic**: A purely deterministic Python node that runs FCA-aligned financial risk audits. 
*   **FX Normalization**: If the LLM proposes a trade in USD, the Gatekeeper instantly converts it to a base currency (GBP) using the hardcoded `FX_RATES` dictionary before evaluating portfolio exposure.
*   **Asset-Specific Limits**:
    *   *Equity*: Max 20% portfolio concentration, Max £5k order.
    *   *Crypto*: Strict max 5% portfolio concentration.
    *   *Options*: Hard cap of £2k per order.
*   **Cryptography**: If the trade passes, the Gatekeeper generates an **HMAC SHA-256 signature** using a local `SECRET_KEY` and appends it to the state.

### Node 3: The Execution Agent
*   **Logic**: First, it attempts to verify the cryptographic signature using `secrets.compare_digest()`.
*   **Execution**: If the signature matches (proving the state wasn't tampered with post-audit), it maps the `ProposedTrade` into the strict schema expected by the Egress Boundary.

---

## 3. Future Recommendations & Scaling Roadmap

As Shire evolves from a prototype to a production-grade system, the following architectural upgrades are highly recommended:

### 1. Human-in-the-Loop (HITL) Interruption
*   **Concept**: For trades exceeding certain risk thresholds (e.g., any Crypto trade over £1,000), pause the LangGraph state execution entirely.
*   **Implementation**: Route an approval notification to a Slack channel or a mobile push notification. The graph will wait in memory until a human clicks "Approve", at which point it injects the manual approval token and resumes to the Execution node.

### 2. Live Forex and Market Data APIs
*   **Concept**: Replace the hardcoded `FX_RATES` and `portfolio_value` with live streaming data.
*   **Implementation**: Integrate WebSockets via Alpha Vantage or Polygon.io. When the Gatekeeper runs FX conversion, it should fetch the millisecond-accurate exchange rate.

### 3. Persistent Audit Ledger (Event Sourcing)
*   **Concept**: Currently, logs are held in application memory and disappear on refresh.
*   **Implementation**: Plumb the graph's output to an immutable append-only database (like AWS QLDB or PostgreSQL with an event-sourcing pattern). This provides absolute mathematical proof of compliance for regulatory audits.

### 4. Advanced Egress Routing
*   **Concept**: Dynamically route trades to different brokers based on the asset class and currency to minimize slippage and fee friction.
*   **Implementation**: If `asset_class == CRYPTO`, the Egress layer formats a payload for Coinbase Prime. If `asset_class == EQUITY` and `currency == USD`, it routes to Alpaca API.
