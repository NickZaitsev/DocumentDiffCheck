from __future__ import annotations


class DomainError(Exception):
    """Base class for business-level errors."""


class DocumentValidationError(DomainError):
    """Raised when an uploaded document is invalid."""


class DocumentParsingError(DomainError):
    """Raised when a document cannot be parsed."""


class DocumentNotFoundError(DomainError):
    """Raised when a stored document does not exist."""


class ReportNotFoundError(DomainError):
    """Raised when a stored comparison report does not exist."""


class ComparisonError(DomainError):
    """Raised when documents cannot be compared."""


class AIProcessingError(DomainError):
    """Raised when AI-assisted processing fails."""

