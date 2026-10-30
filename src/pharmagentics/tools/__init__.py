"""Shared deterministic tools for both lanes (core-004 in first form): a governed, read-only data
registry that records every query as an evidence item, plus claim tokens that code fills."""
from .registry import Registry, DEFAULT_DB

__all__ = ["Registry", "DEFAULT_DB"]
