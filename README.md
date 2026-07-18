# Shire: Zero-Trust Multi-Agent Wealth Orchestration Engine

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.14+-blue.svg)

Shire is a production-grade, non-custodial multi-agent financial execution architecture built on top of LangGraph. Designed specifically to navigate the risk boundaries of the UK fintech landscape, Shire eliminates the single points of failure inherent in conversational AI systems by implementing an ironclad Three-Key Consensus Protocol.

## 💡 Why Shire Matters

In production fintech environments, granting an LLM direct access to transactional brokerage APIs introduces critical security vulnerabilities. A single hallucinated parameter, prompt injection, or logic error can result in unauthorized trades or catastrophic capital misallocation. 

Shire enforces a zero-trust architecture at the state-machine level, ensuring that no trade execution payload can reach a brokerage interface without passing an independent, deterministic risk audit.

## 🏗️ Architecture & Consensus Flow

Shire models execution workflows as state graphs rather than unstructured chats, completely blocking agentic "hallucination shortcuts."

1. **Analyst Agent:** Scans market context, tokenizes macro updates, and proposes a raw order payload. It has zero tool access.
2. **Risk Gatekeeper:** Intercepts the proposed state and evaluates it against hardcoded FCA-aligned guardrails (e.g., asset concentration limits, maximum daily drawdown). It appends an explicit cryptographic or boolean approval key.
3. **Execution Agent:** Translates the order into strict JSON schemas wrapping runtime validation layers *if and only if* the Risk Gatekeeper approves.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/shire.git
cd shire

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the FastAPI server and visualization dashboard
python main.py
```

## 🛡️ Risk Engine Guardrails

Shire implements deterministic checks to adhere to strict compliance:
- **Maximum Asset Concentration:** No single asset can exceed 20% of the portfolio.
- **Order Size Limits:** Individual transactions are capped at predefined thresholds.
- **Restricted Assets:** Automatic blocking of trades involving forbidden tickers.
- **Cryptographic Signing:** Approved trades are signed via HMAC to prevent state tampering before execution.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
