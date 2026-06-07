from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENT_STORAGE_DIR = DATA_DIR / "documents"
FRONTEND_DIR = BASE_DIR / "frontend"
APP_HOST = "127.0.0.1"
APP_PORT = 8010

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SUPPORTED_EXTENSIONS = frozenset({".docx"})


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue
        name, raw_value = value.split("=", 1)
        name = name.strip()
        if not name or name in os.environ:
            continue
        os.environ[name] = raw_value.strip().strip('"').strip("'")


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value)


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return float(raw_value)


def _env_csv(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")
    return tuple(value.strip() for value in raw_value.split(",") if value.strip())


_load_dotenv(BASE_DIR / ".env")

GEMINI_GATEWAY_SRC_PATH = Path(r"C:\gemini-gateway\src")
GEMINI_MODEL = _env_str("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_API_KEYS = _env_csv("GEMINI_API_KEYS")
GEMINI_REQUESTS_PER_MINUTE = _env_int("GEMINI_REQUESTS_PER_MINUTE", 15)
GEMINI_TOKENS_PER_MINUTE = _env_int("GEMINI_TOKENS_PER_MINUTE", 250_000)
GEMINI_REQUESTS_PER_DAY = _env_int("GEMINI_REQUESTS_PER_DAY", 500)
GEMINI_TIMEOUT_MS = _env_int("GEMINI_TIMEOUT_MS", 120_000)
GEMINI_MAX_RETRIES = _env_int("GEMINI_MAX_RETRIES", 3)
GEMINI_TEMPERATURE = _env_float("GEMINI_TEMPERATURE", 0.1)

OPENROUTER_API_KEY = _env_str("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _env_str("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
OPENROUTER_BASE_URL = _env_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_TIMEOUT_SECONDS = _env_int("OPENROUTER_TIMEOUT_SECONDS", 120)
OPENROUTER_MAX_TOKENS = _env_int("OPENROUTER_MAX_TOKENS", 4000)
OPENROUTER_TEMPERATURE = _env_float("OPENROUTER_TEMPERATURE", 0.1)
OPENROUTER_SITE_URL = _env_str("OPENROUTER_SITE_URL", "http://127.0.0.1:8010")
OPENROUTER_APP_NAME = _env_str("OPENROUTER_APP_NAME", "Document Diff Check")

# A financial RISK is a contingent or asymmetric monetary exposure — something
# that can cost a party money beyond the agreed price. The agreed price itself,
# the quantity, and a normal payment schedule are NOT risks (they are terms).
_RISK_DEFINITION = """
A "financial_risk" is a CONTINGENT or asymmetric monetary exposure — something
that can cost a party extra money beyond the agreed deal:
- penalties, fines, неустойка, пеня, штраф, liquidated damages;
- consequences of late delivery or late payment (просрочка);
- liability, especially uncapped liability, damages (убытки);
- price indexation / unilateral price change;
- prepayment that can be lost / non-refundable, withholding (удержание),
  forfeiture of a deposit or guarantee.
The agreed contract price, the quantity, totals, taxes, and a normal payment
schedule are NOT financial risks — they are ordinary commercial terms. Do not
mark them as financial_risk (still list them as regular items when relevant).
"risk_type" must be one of: penalty | liability | indexation | price_change |
prepayment | withholding | other.
"""

COMPARISON_ANALYSIS_PROMPT = (
    """
You are a legal document review assistant. Analyze only the provided structured
DOCX diff. Do not invent clauses that are not present in the diff.

Return JSON that matches the provided schema. Write in Russian.

Produce ONE unified list of changes ("changes"). For each change:
- "description": one self-contained sentence describing what changed, for a
  lawyer (no headings, no separate "significance" field, no boilerplate);
- "source_change_ids": the change_id values from the payload that this item
  covers (one or several). Use only ids that exist in the payload;
- "financial_risk": true ONLY for a genuine financial risk as defined below;
- "risk_type": the tag from the list below when financial_risk is true, else null;
- "estimated_impact": when financial_risk is true, the money effect as a value
  or a short formula using amounts present in the document; null when it cannot
  be estimated. Do not invent missing contract values.
"""
    + _RISK_DEFINITION
    + """
Also fill:
- "summary": 1-2 sentences on what changed overall;
- "overall_risk_level": "low" | "medium" | "high" based on the financial risks;
- "recommended_review_points": a few concrete things a lawyer should check.

Comparison payload:
{comparison_payload}
"""
).strip()

DOCUMENT_ANALYSIS_PROMPT = (
    """
You are auditing ONE legal contract for financial risk. Analyze only the
provided structured DOCX blocks. Do not invent clauses that are not present.

Return JSON that matches the provided schema. Write in Russian.

Produce ONE list ("changes") focused on financial risk. For each item:
- "description": one self-contained sentence about a risky clause, for a lawyer
  (no headings, no separate "significance" field);
- "source_change_ids": the block_id values from the payload this item refers to.
  Use only ids that exist in the payload;
- "financial_risk": true ONLY for a genuine financial risk as defined below;
- "risk_type": the tag from the list below when financial_risk is true, else null;
- "estimated_impact": when financial_risk is true, quantify the exposure using
  amounts present in the contract (e.g. the total price) when possible; null
  otherwise. Do not invent missing contract values.
"""
    + _RISK_DEFINITION
    + """
Prioritise the financial risks. You may include a few key commercial terms
(price, payment schedule) as context items with financial_risk=false, but the
agreed price is context, not a risk.

Also fill:
- "summary": 1-2 sentences on the contract's purpose and main obligations;
- "overall_risk_level": "low" | "medium" | "high" based on the financial risks;
- "recommended_review_points": a few concrete things a lawyer should check.

Document payload:
{document_payload}
"""
).strip()
