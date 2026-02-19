"""Exceptions for the Inspire to Arc middleware.

This module provides custom exception classes for handling errors
during Inspire record processing and conversion to Arc format.
"""


class InspireToArcError(Exception):
    """Base exception for Inspire to Arc middleware."""


class SemanticError(InspireToArcError):
    """Raised when there is a semantic error in the Inspire record processing."""


class RecordProcessingError(InspireToArcError):
    """Raised when a specific record fails to be processed, carrying its identifier."""

    def __init__(self, message: str, record_id: str, original_error: Exception | None = None):
        """
        Initialize the RecordProcessingError.

        Args:
            message (str): The error message describing the issue.
            record_id (str): The identifier of the record that caused the error.
            original_error (Exception | None): The original exception that caused this error, if any.
        """
        super().__init__(message)
        self.record_id = record_id
        self.original_error = original_error
