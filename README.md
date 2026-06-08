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

## AI provider config

Create a local `.env` file from `.env.example`. Do not commit `.env` or hard-code
API keys in `src/config.py`.

Gemini:

```powershell
GEMINI_API_KEYS=your-key
GEMINI_MODEL=gemini-3.1-flash-lite
```

OpenRouter fallback provider:

```powershell
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=google/gemma-4-31b-it:free
```

Provider order:

```text
Gemini -> OpenRouter -> deterministic fallback
```

Prompts are also stored in `src/config.py`:

- `LEGAL_SUMMARY_PROMPT`
- `FINANCIAL_RISK_PROMPT`

## API

- `POST /api/documents` uploads one DOCX and returns `document_id`.
- `GET /api/documents` lists uploaded documents.
- `POST /api/comparisons/upload` compares two uploaded DOCX files.
- `POST /api/comparisons` compares two already uploaded documents by ID.

## Tests

```powershell
py -m pytest
```
