# Architecture

Document Diff Check is organized around dependency inversion. The API layer owns
transport concerns, application use cases coordinate workflows, and domain
services contain deterministic comparison logic. Infrastructure and integrations
implement the ports used by the inner layers.

```mermaid
flowchart LR
    API[api]
    APP[application]
    DOMAIN[domain]
    INFRA[infrastructure]
    INTEGRATIONS[integrations]
    SCHEMAS[schemas]

    API --> APP
    API --> SCHEMAS
    APP --> DOMAIN
    APP --> SCHEMAS
    INFRA --> DOMAIN
    INTEGRATIONS --> DOMAIN
    INTEGRATIONS --> SCHEMAS
```

## Layers

- `api`: FastAPI routes, request parsing, response formatting, middleware, and
  domain-exception to HTTP response conversion.
- `application`: use cases for upload, comparison, and single-document review.
- `domain`: entities, ports, comparison logic, exceptions, and token-budget
  chunking strategy.
- `infrastructure`: DOCX parsing, fallback insights, file-backed repositories,
  and prompt payload construction.
- `integrations`: provider adapters for Gemini and OpenRouter.
- `schemas`: Pydantic API and LLM response contracts.

## Insight Provider Chain

The API builds a resilient provider chain at startup:

```mermaid
flowchart LR
    Gemini[Gemini provider]
    OpenRouter[OpenRouter provider]
    Fallback[Deterministic fallback]
    Result[ChangeReport]

    Gemini -->|success| Result
    Gemini -->|init or request failure| OpenRouter
    OpenRouter -->|success| Result
    OpenRouter -->|init or request failure| Fallback
    Fallback --> Result
```

Each LLM provider receives token-budgeted batches of changes or document blocks.
Batch reports are cleaned against valid source IDs and merged before returning to
the application layer.
