"""Public transaction schema for coordinated cross-domain operations.

Callers own the transaction; these resources never commit independently.
"""

from .repository import steps

__all__ = ["steps"]
