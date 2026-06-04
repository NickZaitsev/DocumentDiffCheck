from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENT_STORAGE_DIR = DATA_DIR / "documents"
FRONTEND_DIR = BASE_DIR / "frontend"
APP_HOST = "127.0.0.1"
APP_PORT = 8010

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SUPPORTED_EXTENSIONS = frozenset({".docx"})

GEMINI_GATEWAY_SRC_PATH = Path(r"C:\gemini-gateway\src")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEYS: tuple[str, ...] = ()
GEMINI_REQUESTS_PER_MINUTE = 15
GEMINI_TOKENS_PER_MINUTE = 250_000
GEMINI_REQUESTS_PER_DAY = 500
GEMINI_TIMEOUT_MS = 120_000
GEMINI_MAX_RETRIES = 3
GEMINI_TEMPERATURE = 0.1

LEGAL_SUMMARY_PROMPT = """
You are a legal document review assistant. Analyze only the provided structured
DOCX diff. Do not invent clauses that are not present in the diff.

Return JSON that matches the provided schema. Write in Russian.

Focus on:
- what materially changed;
- what the change means for a lawyer reviewing the contract;
- which clauses deserve manual review;
- neutral wording, without legal advice beyond the provided text.

Comparison payload:
{comparison_payload}
""".strip()

FINANCIAL_RISK_PROMPT = """
You are a financial risk extraction assistant for legal contract changes.
Analyze only the provided changed clauses. Treat model output as structured data.

Return JSON that matches the provided schema. Write in Russian.

Find risks related to:
- penalties, fines, liquidated damages, late delivery, late payment;
- percentages, fixed money amounts, payment terms, indexation;
- liability caps, uncapped liability, prepayment, refund, withholding.

For estimated impact, provide a formula or explanation when exact money value
cannot be calculated from the text. Do not invent missing contract values.

Comparison payload:
{comparison_payload}
""".strip()
