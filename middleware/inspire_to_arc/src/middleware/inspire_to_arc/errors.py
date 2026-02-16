"""Exceptions for the Inspire to Arc middleware.

This module provides custom exception classes for handling errors
during Inspire record processing and conversion to Arc format.
"""


class InspireToArcError(Exception):
    """Base exception for Inspire to Arc middleware."""


class SemanticError(InspireToArcError):
    """Raised when there is a semantic error in the Inspire record processing."""
