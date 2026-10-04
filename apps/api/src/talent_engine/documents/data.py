"""Public transaction schema for coordinated cross-domain operations.

Callers own the transaction; these resources never commit independently.
"""

from .repository import upload_sessions, uploads

__all__ = ["uploads", "upload_sessions"]
