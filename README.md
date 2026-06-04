[6/4/2026 12:35 PM] nenavision: Итак, нужно сделать проект. Его суть в том, что нужен фронтенд, и также чтобы был какой-то API endpoint, чтобы была возможность загрузить два документа, и чтобы между ними, эти docx документы, решение docx, чтобы между ними находился диф, то есть разница между документами. После этого нужно отправить, собственно, summary, summary, да, что изменилось для юриста, да, то есть в чём суть этих изменений, которые были внесены в документ. Вот. Здесь какие мои важные идеи, которые, ну, важно подсветить, что, во-первых, не знаю, какой-то лучше использовать диф, возможно, библиотеку, да, потому что там, если где-то что-то съедет, то диф может быть очень большим между документами, да, если, ну, ты понимаешь. Вот. Диф может поехать, нужно за этим подумать. Во-вторых, как использовать какую библиотеку для docx использовать, я не знаю, в принципе. Собственно, важно, чтобы мы чанки нормально делали, чтобы мы не только диф выбрасывали, но и, возможно, нужно что-то другое, да, то есть по предложениям, возможно, делить или по абзацам.
[6/4/2026 12:35 PM] nenavision: Также должна быть возможность кинуть третий документ, чтобы он сравнился со вторым, вот. То есть, возможно, я предлагаю какой-то внутренний ID документов ввести, да. Возможно, что ты об этом думаешь, да. Чтобы человек мог просто кинуть третий документ, и ему нашелся второй. Кинуть третий документ и кинуть какой-то ID, допустим, или скинуть два документа. В общем, это пока не очень важно, это UXUI. Вот это первая часть.
[6/4/2026 12:35 PM] nenavision: Первую часть нужно обязательно выполнить. Вторая часть – это конкретные финансовые риски выписать. То есть не только описание TLR, да, то есть что изменилось, а конкретно по каждому риску, да, то есть надо каким-то образом выявить вот эти вот части документа, где у нас есть риск. Я предлагаю просто кидать по какой-то количеству токенов документ, да, его поделить как-то. И, ну, максимум там какое-то количество токенов, а так лучше делить, наверное, по или частям, или абзацам. Вот. И чтобы не было очень много контекста, потому что тогда он будет путаться, и чтобы он возвращал нам JSON с теми пунктами, которые, собственно, могут финансовые риски иметь какие-то. Вот. Надо, чтобы, собственно, сначала он находил эти пункты, а потом старался делать расчёт, собственно, в какой конкретно финансовый риск в собственных деньгах. Да, я не знаю, как точно, то есть я думаю, что, возможно, здесь стоит или прикрепить будущие возможные для добавления семантического поиска, или просто добавлять, допустим, в системный промпт, да, сколько, например, у нас у такого-то документа стоимость и так далее. Да, потому что, ну, суть в чём? Там часто бывает пункт такой, как, допустим, если опоздает поставка, то 10%, допустим, да, нужно платить относительно полной стоимости поставки. Вот. Нужно как-то это доставывать, да, при этом ещё нужно понимать, что не всегда прям в этом же документе у нас будут все стоимости. Это такой пункт второй уже не который не так важен, но я тоже хочу его выполнить.

## Current implementation

The project contains a production-oriented MVP for DOCX comparison:

- `FastAPI` backend with explicit `api`, `application`, `domain`, `infrastructure`, `integrations`, and `schemas` layers.
- DOCX parser that converts documents into deterministic structural blocks: paragraphs and table rows.
- Structural diff engine based on normalized blocks, fuzzy matching for modified clauses, and word-level diff inside modified blocks.
- Upload by two files or compare by stored `document_id`.
- Legal summary and financial risk assessment through an `InsightProvider` abstraction.
- Gemini integration through `C:\gemini-gateway`; when keys are not configured, deterministic fallback insights keep the demo working.
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

## Gemini config

Do not use `.env` for this project. Configure AI providers directly in `src/config.py`.

Gemini:

```python
GEMINI_API_KEYS = ("your-key",)
GEMINI_MODEL = "gemini-2.0-flash"
```

OpenRouter fallback provider:

```python
OPENROUTER_API_KEY = "your-openrouter-key"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
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
