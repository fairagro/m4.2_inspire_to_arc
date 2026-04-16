"""Core exceptions for the Middleware Harvester ecosystem.

This module provides the overarching exception hierarchy used by the orchestrator
and all plugins to standardize error handling and logging.
"""


class HarvesterError(Exception):
    """Base exception for all Harvester and plugin-related errors."""


class RecordProcessingError(HarvesterError):
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
