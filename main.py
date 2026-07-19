import uvicorn
import logging

# Configure basic logging for visibility
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    print("=========================================================")
    print(" Starting Shire Zero-Trust Wealth Orchestration Engine")
    print(" FCA Guardrails Active | Cryptographic Signing Enabled")
    print("=========================================================")
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, reload=True)
