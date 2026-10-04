"""Public transaction schema for coordinated cross-domain operations.

Callers own the transaction; these resources never commit independently.
"""

from .repository import campaigns, insert_campaign, owned, snapshots

__all__ = ["campaigns", "snapshots", "owned", "insert_campaign"]
