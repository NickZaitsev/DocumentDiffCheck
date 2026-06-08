# Code Review — DocumentDiffCheck

Production-readiness review for publishing on GitHub. Findings are ordered by
severity. Each item lists **what**, **where**, **why it matters**, and a
**concrete fix** so it can be handed to an automated agent (Claude Code / Codex)
and implemented without further clarification.

---

## 0. Executive summary

The architecture is clean and the layer separation (`api` → `application` →
`domain` → `infrastructure`/`integrations` → `schemas`) genuinely follows
`AGENTS.md`. The diff engine is solid (structural block diff + fuzzy pairing +
word-level diff). The provider fallback chain is a good idea.

However, the project is **not production-ready** and, more importantly, the
single most prominent product requirement — *splitting the document by tokens /
paragraphs so the model does not get a too-large context* — **is not actually
implemented**. The code truncates instead of chunking. This is the first thing
to fix. There are also blocking-I/O, concurrency-safety, portability, and
repo-hygiene problems described below.

---

## 1. Blockers (must fix before publishing)

### 1.1 There is no real chunking / context-window management — only truncation
**Where:** `src/infrastructure/insights.py`
(`build_prompt_payload`, `max_changes=60`; `build_document_review_payload`,
`max_blocks=120`; `_trim`, `limit=1400`), called once per request from
`src/integrations/gemini_provider.py` and `src/integrations/openrouter_provider.py`.

**What:** Both providers build **one** payload and make **one** LLM call. Any
change beyond #60, any block beyond #120, and any text longer than 1400 chars is
**silently dropped**. There is no token counting and no splitting into multiple
requests.

**Why it matters:** The core deliverable (find *every* financial risk) fails on
any real contract: risks living in block #121, or in the truncated tail of a long
clause, are never sent to the model. `README.md` and `AGENTS.md` both advertise
"chunking strategies" that do not exist — this will read as false advertising on
GitHub.

**Fix:**
- Add a `domain/chunking.py` strategy that splits the change list / block list
  into batches that fit a configurable token budget (`MAX_INPUT_TOKENS`), using a
  real token estimate (e.g. `tiktoken` or a chars/4 heuristic with a safety
  margin), never a hard count of 60/120.
- Call the LLM once per batch, then merge the `ChangeReport`s (concat `changes`,
  recompute `overall_risk_level`, merge `recommended_review_points`,
  re-summarize). Keep `source_change_ids` stable across batches.
- Stop truncating clause text by default; only trim a single block if it alone
  exceeds the budget, and mark it as truncated.
- Make the budgets configuration-driven, not magic numbers in function defaults.

### 1.2 Hard-coded local path to an out-of-repo dependency
**Where:** `src/config.py:57` `GEMINI_GATEWAY_SRC_PATH = Path(r"C:\gemini-gateway\src")`
and `src/integrations/gemini_provider.py:23-28` (`sys.path.insert` + `from
gemini_gateway import ...`).

**Why it matters:** Nobody who clones the repo from GitHub has `C:\gemini-gateway`.
The Gemini provider is unimportable for everyone else, and `sys.path` mutation at
runtime is fragile. This makes the project non-portable.

**Fix:** Either publish/vendor `gemini_gateway` as a real dependency in
`pyproject.toml`, or replace it with a direct `httpx` client to the Gemini REST
API (mirroring the OpenRouter provider). Remove the hard-coded path and the
`sys.path` hack.

### 1.3 Startup crash if the Gemini gateway import fails
**Where:** `src/api/app.py:249-256` (`_build_primary_insight_providers`) only
catches `AIProcessingError`.

**What:** `GeminiInsightProvider.__init__` does `from gemini_gateway import ...`.
If that import raises `ImportError`/`ModuleNotFoundError` (the normal case for a
fresh clone — see 1.2), it is **not** caught, so `create_app()` throws and the
whole app fails to boot — even though OpenRouter and the deterministic fallback
are available.

**Fix:** Catch `Exception` (or specifically `ImportError` + `AIProcessingError`)
per-provider, log a warning, and continue. A provider that cannot initialize must
degrade, not crash the app.

### 1.4 Blocking I/O on the async event loop
**Where:** `src/api/app.py` async routes `upload_document`, `compare_uploads`,
`review_upload`; provider HTTP call `httpx.post(...)` in
`src/integrations/openrouter_provider.py:68`.

**What:** `compare_uploads`/`review_upload` are `async def` but synchronously call
use cases that do CPU-bound DOCX parsing and **blocking** network calls to the LLM
(`httpx.post`, the Gemini gateway). This blocks the single event loop and serializes
all concurrent requests.

**Fix:** Use `httpx.AsyncClient` and `await` the request, and make the provider
interface async; or keep the routes synchronous (`def`) so FastAPI runs them in
the threadpool. Do not mix `async def` with blocking calls.

### 1.5 File-backed repositories are not concurrency-safe
**Where:** `src/infrastructure/storage.py`, `reports.py`, `reviews.py` — all do
read-whole-index-JSON → mutate dict → rewrite-whole-file with no locking.

**Why it matters:** Two concurrent uploads/saves race on `index.json`; one write
overwrites the other (lost data) or leaves a half-written/corrupt file. The full
rewrite is also O(n) per save and will not scale.

**Fix:** Introduce an `DocumentRepository`/report/review backend backed by SQLite
(stdlib, transactional) behind the existing Protocols, or at minimum add a file
lock + atomic write (`tempfile` + `os.replace`). SQLite is the cleanest path and
keeps the ports unchanged.

---

## 2. Security (must address for a public service; acceptable to document as
"demo only" otherwise)

### 2.1 No authentication or authorization on any endpoint
Anyone can upload, list, download, and analyze every stored document
(`/api/documents`, `/api/documents/{id}/download`, etc.). Add at least an API-key
dependency, and scope document access. At minimum, document loudly in the README
that this is an unauthenticated demo.

### 2.2 Upload size limit is enforced *after* the whole file is in memory
**Where:** `app.py` `await file.read()` then `UploadDocumentUseCase._validate_upload`
checks `MAX_UPLOAD_BYTES`. A 2 GB upload is fully buffered before rejection → memory
DoS. Enforce a streaming size cap (read in chunks, abort early) or a reverse-proxy
body limit.

### 2.3 CORS is fully open
`allow_origins=["*"]` + `allow_methods=["*"]`. Fine for local demo; lock to a
configured origin list for production.

### 2.4 LLM output is partially validated, but the enums are not
`risk_type` and `overall_risk_level` are free `str` in `schemas/insights.py`. The
prompt defines a closed set (`penalty | liability | indexation | price_change |
prepayment | withholding | other`) but nothing enforces it. Make them `StrEnum`s
so an out-of-contract value from the model is rejected, per the AGENTS.md
"LLM outputs are untrusted / strong typing" rules.

---

## 3. Correctness & reliability

### 3.1 Structured logging does not actually emit its fields
**Where:** `app.py:208-216`. The log record passes `extra={"request_id": ...,
"operation": ..., ...}`, but the formatter is `"%(asctime)s %(levelname)s
%(message)s"` — none of `request_id`, `operation`, `execution_time`, `document_id`
appear in the output. AGENTS.md explicitly requires these fields. Switch to a JSON
log formatter (e.g. a small custom `logging.Formatter`) that serializes the extras.

### 3.2 `document_id` is always logged as `None`
Same middleware: `"document_id": None` is hard-coded. Either remove it or thread
the real id through (e.g. via `request.state`).

### 3.3 `created_at` microsecond-bumping is a fragile ordering hack
**Where:** `storage.py:51-54`. Ordering by an artificially incremented timestamp
breaks under concurrency and across process restarts. Use an explicit monotonic
sequence column or rely on the DB insert order (ties into 1.5 / SQLite).

### 3.4 OpenRouter strict JSON schema may be rejected by many models
**Where:** `openrouter_provider.py:58-65` sends `ChangeReport.model_json_schema()`
with `strict: True`. That schema includes fields with defaults (`provider`,
`model`, optional lists). Several OpenRouter models reject non-strict-compatible
schemas (defaults, additionalProperties). Build a dedicated, minimal
request-schema (only the fields you want the model to fill, all required,
`additionalProperties: false`) instead of reusing the storage model.

### 3.5 Dead code
`FileHasher` Protocol in `src/domain/ports.py:34-37` is never implemented or used.
Remove it or wire up dedup-by-hash (which would also be a genuinely useful
feature: detect re-uploads of the same file).

---

## 4. Architecture & AGENTS.md compliance gaps

- **Prompts are not in dedicated, versioned files.** AGENTS.md: "Store prompts in
  dedicated files… every prompt must have versioning." They currently live in
  `config.py`. Move to `src/prompts/` with a version tag (e.g. `COMPARISON_V1`)
  echoed into `ChangeReport.model`/telemetry so outputs are traceable to a prompt
  version.
- **Imports in the middle of the module.** `reports.py:14-19` and `reviews.py:14-19`
  put `logger = logging.getLogger(...)` between imports. Move all imports to the
  top (PEP 8 / will be flagged by ruff).
- **No linter / type checker configured or run.** `.gitignore` lists `.ruff_cache`
  and `.mypy_cache`, but neither tool is in `pyproject.toml` dev deps, and there
  is no config. AGENTS.md mandates strict typing. Add `ruff` + `mypy --strict`
  to dev deps and a config, and fix what they surface.
- **No CI.** There is no `.github/workflows`. Add a workflow running `ruff`,
  `mypy`, and `pytest` on push/PR. This is table stakes for a public repo.

---

## 5. Repository hygiene for GitHub

- **README starts with a raw Russian voice-transcript** of the task brief
  (`README.md:1-3`). Remove it from the README (move to `docs/BRIEF.md` if you
  want to keep it). A public README should open with what the project is and how
  to run it.
- **Model defaults look non-existent / future-dated:** `gemini-3.1-flash-lite`
  and `google/gemma-4-31b-it:free` (`config.py:58,68`). Verify against the live
  model catalogs and default to currently available model ids, or these 404 on
  first run.
- **`.env.example` is incomplete.** It omits the rate-limit, timeout, temperature,
  base-url, and `OPENROUTER_SITE_URL`/`APP_NAME` variables that `config.py` reads.
  Document every supported variable.
- **No `LICENSE`.** Add one (MIT/Apache-2.0) before publishing.
- **No architecture doc / diagram.** A short `docs/ARCHITECTURE.md` describing the
  layers and the provider fallback chain would help reviewers and contributors.
- **`run.py` has `reload=False` hard-coded.** Expose host/port/reload via env or a
  small CLI so local dev and container runs differ cleanly.

---

## 6. Testing gaps (relative to AGENTS.md "80%+ domain coverage")

- Add tests that **prove chunking** once 1.1 lands: a document larger than one
  budget must produce multiple LLM calls and a merged report with no dropped
  blocks. (Today no such test can pass because there is no chunking.)
- Add a regression test for 1.3 (Gemini import failure must not crash app boot).
- Add concurrency tests for the repositories (parallel saves must not lose data)
  once 1.5 lands.
- Add a test asserting the structured log line actually contains `request_id` /
  `operation` / `execution_time` (covers 3.1).

---

## 7. Suggested implementation order (for the agent)

1. **1.2 + 1.3** — make the app importable and boot-safe for any cloner.
2. **1.1** — real token-aware chunking + report merging (the headline feature).
3. **1.5** — SQLite-backed repositories behind the existing Protocols.
4. **1.4** — async/threadpool correctness for I/O.
5. **2.x** — auth gate, streaming size limit, enum-typed LLM fields.
6. **3.x / 4.x** — logging formatter, prompt module + versioning, ruff/mypy/CI.
7. **5.x** — README cleanup, LICENSE, `.env.example`, model defaults.
8. **6** — tests for every change above.

---

## 8. What is already good (keep)

- Clean hexagonal layering with `Protocol` ports and dependency inversion.
- Deterministic structural diff with numbering normalization and fuzzy clause
  pairing (`domain/comparison.py`) — this is the strongest part of the codebase.
- The resilient provider chain (Gemini → OpenRouter → deterministic fallback) and
  the `clean_report` step that drops hallucinated `source_change_ids`.
- Frozen, slotted dataclasses for domain entities and a typed Pydantic API
  boundary.
- A genuinely useful deterministic fallback so the demo works with zero keys.
