"""Register the shared schema without constructing an HTTP application."""

from importlib import import_module


def register_models():
    for module in (
        "access",
        "campaigns.data",
        "applications.data",
        "documents.data",
        "analyses.data",
        "sources.data",
        "evaluations.data",
        "reception_limits.data",
    ):
        import_module("talent_engine." + module)
