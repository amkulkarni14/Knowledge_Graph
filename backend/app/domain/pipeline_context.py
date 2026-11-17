"""PipelineContext: the hand-off object passed from one stage to the next.

Every stage reads what earlier stages produced and writes its own output here.
The UI keeps one context per browser session; the CLI keeps one per run.
It also records an activity log so the UI can show *what is happening*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PipelineContext:
    # Stage 1
    scope: Any = None
    # Stage 2
    source: Any = None                 # DataSource (PostgresSource or SampleSource)
    source_info: dict = field(default_factory=dict)
    # Stage 3-4
    catalog: Any = None                # SchemaCatalog
    table_analysis: list = field(default_factory=list)
    # Stage 5-10
    manual_ontology: Any = None        # Ontology (draft)
    ai_items: list = field(default_factory=list)
    ai_meta: dict = field(default_factory=dict)
    hybrid_draft: Any = None           # Ontology after review decisions
    ontology_report: Any = None        # ValidationReport
    approved_ontology: Any = None      # Ontology (approved)
    build_plan: Any = None
    # Stage 11-16
    extraction: Any = None             # ExtractionResult
    dq_report: Any = None
    clean: Any = None                  # CleanResult
    graph: Any = None                  # nx.MultiDiGraph
    build_stats: Any = None
    graph_report: Any = None
    snapshot: Any = None               # manifest dict

    source_version: int = 0            # bumped whenever Stage 2 connects to a (new) source

    completed: set = field(default_factory=set)
    events: list = field(default_factory=list)

    def clear_results_from_schema(self) -> None:
        """A different source makes everything derived from the old one meaningless (Stages 3-16)."""
        self.catalog, self.table_analysis = None, []
        self.manual_ontology, self.ai_items, self.ai_meta = None, [], {}
        self.hybrid_draft = self.ontology_report = self.approved_ontology = self.build_plan = None
        self.extraction = self.dq_report = self.clean = self.graph = None
        self.build_stats = self.graph_report = self.snapshot = None

    def log(self, stage: int, message: str, level: str = "info") -> None:
        self.events.append({"time": datetime.now().strftime("%H:%M:%S"), "stage": stage,
                            "level": level, "message": message})

    def mark_done(self, stage: int) -> None:
        self.completed.add(stage)

    def invalidate_from(self, stage: int) -> None:
        """When an upstream stage is re-run, downstream results are no longer valid."""
        self.completed = {s for s in self.completed if s < stage}

    def is_done(self, stage: int) -> bool:
        return stage in self.completed

    def require(self, *stages: int) -> Optional[int]:
        """Returns the first missing prerequisite stage, or None."""
        return next((s for s in stages if s not in self.completed), None)
