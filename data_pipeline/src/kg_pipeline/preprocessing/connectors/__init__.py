"""Data sources. Both implement the same read-only interface (see base.py)."""
from kg.sources.base import DataSource
from kg.sources.sample_source import SampleSource

__all__ = ["DataSource", "SampleSource"]
