"""Exceptions for the Inspire to Arc middleware.

This module provides custom exception classes for handling errors
during Inspire record processing and conversion to Arc format.
"""

from middleware.harvester.errors import HarvesterError


class InspireError(HarvesterError):
    """Base exception for Inspire plugin."""


class CswConnectionError(InspireError):
    """Raised when a connection to the CSW endpoint fails."""


class SemanticError(InspireError):
    """Raised when there is a semantic error in the Inspire record processing."""
