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
