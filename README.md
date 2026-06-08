# Document Diff Check

Document Diff Check is a DOCX comparison and contract-review service. It parses
documents into deterministic structural blocks, compares revisions, and produces
AI-assisted legal summaries with financial-risk findings.

## Current implementation

The project contains a production-oriented MVP for DOCX comparison:

- `FastAPI` backend with explicit `api`, `application`, `domain`, `infrastructure`, `integrations`, and `schemas` layers.
- DOCX parser that converts documents into deterministic structural blocks: paragraphs and table rows.
- Structural diff engine based on normalized blocks, fuzzy matching for modified clauses, and word-level diff inside modified blocks.
- Upload by two files or compare by stored `document_id`.
- Legal summary and financial risk assessment through an `InsightProvider` abstraction.
- Gemini and OpenRouter provider adapters; when keys or dependencies are not configured, deterministic fallback insights keep the demo working.
- Token-budgeted paragraph/change batching for LLM requests, with merged reports across batches.
- Static frontend served by the same FastAPI app.

## Run

Install dependencies if needed:

```powershell
py -m pip install -e ".[dev]"
```

Start the server:

```powershell
py run.py
```

Open:

```text
http://127.0.0.1:8010
```

The uploaded document list is available at `http://127.0.0.1:8010/documents.html`
and supports search by document name, ID, date, and size.

This is an unauthenticated demo service. Do not expose it publicly with customer
documents unless you add authentication and restrict CORS.

## AI provider config

Create a local `.env` file from `.env.example`. Do not commit `.env` or hard-code
API keys in `src/config.py`.

Token budget:

```powershell
MAX_INPUT_TOKENS=12000
```

Gemini:

```powershell
GEMINI_API_KEYS=your-gemini-key
GEMINI_MODEL=gemini-1.5-flash
GEMINI_REQUESTS_PER_MINUTE=15
GEMINI_TOKENS_PER_MINUTE=250000
GEMINI_REQUESTS_PER_DAY=500
GEMINI_TIMEOUT_MS=120000
GEMINI_MAX_RETRIES=3
GEMINI_TEMPERATURE=0.1
```

The Gemini adapter imports the optional `gemini_gateway` package. If it is not
installed, the app skips Gemini and continues with the next provider.

OpenRouter:

```powershell
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=google/gemini-flash-1.5
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_TIMEOUT_SECONDS=120
OPENROUTER_MAX_TOKENS=4000
OPENROUTER_TEMPERATURE=0.1
OPENROUTER_SITE_URL=http://127.0.0.1:8010
OPENROUTER_APP_NAME=Document Diff Check
```

Provider order:

```text
Gemini -> OpenRouter -> deterministic fallback
```

The LLM prompts are stored in `src/config.py`:

- `COMPARISON_ANALYSIS_PROMPT`
- `DOCUMENT_ANALYSIS_PROMPT`

## API

- `POST /api/documents` uploads one DOCX and returns `document_id`.
- `GET /api/documents` lists uploaded documents.
- `GET /api/documents/{document_id}/download` downloads a stored document.
- `POST /api/comparisons/upload` compares two uploaded DOCX files.
- `POST /api/comparisons` compares two already uploaded documents by ID.
- `GET /api/reports` lists saved comparison reports.
- `GET /api/reports/{report_id}` returns one comparison report.
- `POST /api/reviews/upload` reviews one uploaded DOCX for financial risk.
- `POST /api/reviews` reviews an already uploaded document by ID.
- `GET /api/reviews` lists saved document reviews.
- `GET /api/reviews/{review_id}` returns one document review.

## Tests

```powershell
py -m pytest
py -m ruff check .
py -m mypy
```
