"""Public transaction schema for coordinated cross-domain operations.

Callers own the transaction; these resources never commit independently.
"""

from .repository import campaigns, owned, snapshots

__all__ = ["campaigns", "snapshots", "owned"]
