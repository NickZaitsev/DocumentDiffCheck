# AGENTS.md

## Summary

This repository contains a document-analysis service.

The system accepts document uploads, performs document comparison workflows, extracts structured information, and generates AI-assisted insights.

Primary goals:

* deterministic document processing
* reproducible comparison results
* reliable API behavior
* maintainable and extensible architecture
* clear separation between domain logic and infrastructure
* production readiness from day one

The implementation must be designed so that new document-processing pipelines, AI providers, extraction strategies, storage backends, and comparison algorithms can be added without major refactoring.

---

# Engineering Principles

## Architecture First

Prefer explicit architecture over quick implementations.

Business logic must never depend directly on:

* HTTP framework
* database implementation
* LLM provider SDK
* storage provider SDK
* third-party libraries

Use dependency inversion.

Example:

Domain Service
→ Interface
→ Implementation

Never:

Domain Service
→ OpenAI SDK
→ Database ORM
→ External API

---

## Strong Typing

Use strict typing everywhere.

Required:

* Python type hints
* Pydantic models for API contracts
* Typed DTOs between layers

Avoid:

* dict[str, Any]
* untyped responses
* dynamic structures

Public interfaces must be self-documenting through types.

---

## Layer Separation

Recommended structure:

src/

* api/
* application/
* domain/
* infrastructure/
* integrations/
* schemas/
* tests/

Responsibilities:

### api

Transport layer only.

Responsibilities:

* request parsing
* response formatting
* validation

Must not contain business logic.

---

### application

Use cases.

Examples:

* upload document
* compare documents
* generate summary
* analyze risks

Coordinates domain services.

---

### domain

Core business logic.

Must be framework-independent.

Contains:

* entities
* value objects
* domain services
* business rules

This layer is the most important.

---

### infrastructure

Implementations of interfaces.

Examples:

* storage providers
* repositories
* AI adapters
* document parsers

---

### integrations

External service wrappers.

Examples:

* LLM clients
* vector databases
* cloud storage

---

# Error Handling

Never swallow exceptions.

Use explicit exception hierarchy.

Example:

DomainError
├── ValidationError
├── ComparisonError
├── DocumentParsingError
└── AIProcessingError

API layer converts exceptions into HTTP responses.

Business logic must never return error strings.

Raise exceptions instead.

---

# Logging

Use structured logging.

Required log fields:

* request_id
* operation
* execution_time
* document_id

Never log:

* document contents
* secrets
* API keys
* sensitive customer information

---

# Testing Policy

Tests are mandatory.

Every feature must include tests.

Minimum:

### Unit Tests

Required for:

* business rules
* parsers
* chunking strategies
* comparison logic
* risk extraction logic

Target:

80%+ coverage for domain layer.

---

### Integration Tests

Required for:

* API endpoints
* storage integration
* AI provider integration

External services must be mocked.

---

### Regression Tests

Every production bug must receive:

1. failing test
2. fix
3. passing test

Never fix without adding a test.

---

# AI Usage Rules

LLM outputs are untrusted.

Treat model responses as external input.

Always:

* validate outputs
* parse structured responses
* use schemas
* handle malformed responses

Never rely on free-form text when structured output is possible.

Prefer JSON contracts.

---

# Prompt Management

Prompts are code.

Store prompts in dedicated files.

Do not inline large prompts inside services.

Every prompt must:

* have versioning
* have tests where possible
* be reusable

---

# Performance

Avoid premature optimization.

However:

* stream large files when possible
* avoid loading unnecessary data
* process documents incrementally
* keep memory usage predictable

Large documents must not cause quadratic complexity.

---

# Extensibility

New implementations should be pluggable.

Expected future extensions:

* new document formats
* alternative comparison engines
* additional AI providers
* semantic search
* vector databases
* risk-scoring engines
* workflow orchestration

Design interfaces accordingly.

---

# Code Style

Prefer readability over cleverness.

Functions should:

* do one thing
* have clear names
* be small

Avoid:

* deeply nested conditionals
* hidden side effects
* large service classes

Prefer composition over inheritance.

---

# Pull Request Requirements

Every PR must include:

* tests
* typing
* documentation updates if needed

PR reviewer should be able to understand:

* why the change exists
* what was changed
* how it is tested

---

# Definition of Done

A feature is complete only when:

* implementation exists
* tests exist
* typing exists
* logging exists
* error handling exists
* documentation is updated

If any of the above is missing, the feature is not done.

Please include git convetional commit message after every change