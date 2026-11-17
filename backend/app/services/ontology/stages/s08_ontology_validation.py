"""Stage 8 - Validate the ontology.

STRUCTURAL : is the rulebook well formed by itself? (names, duplicates, references, cycles)
SEMANTIC   : is it true against the real database and compatible with the approved version?
             (tables/columns exist, types fit, keys unique, FK declared, breaking changes)
Errors block approval (Stage 9); warnings are shown to the reviewer.
"""
from __future__ import annotations

from typing import Optional

from app.domain.pipeline_context import PipelineContext
from kg_pipeline.models.ontology_models import Ontology
from kg_pipeline.ontology_compiler.validator import ValidationReport, validate_ontology


def run(ctx: PipelineContext, approved: Optional[Ontology] = None) -> ValidationReport:
    draft = ctx.hybrid_draft or ctx.manual_ontology
    if draft is None:
        raise RuntimeError("Stage 5/7 must run first")
    report = validate_ontology(draft, ctx.catalog, approved)
    ctx.invalidate_from(8)
    ctx.ontology_report = report
    ctx.log(8, f"Ontology validation: {report.summary()}", "info" if report.ok else "error")
    if report.ok:
        ctx.mark_done(8)
    return report
