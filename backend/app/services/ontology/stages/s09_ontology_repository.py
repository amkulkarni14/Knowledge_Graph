"""Stage 9 - Save and version the ontology: save a draft as a new version, then approve it (four-eyes).

The rules (immutable approved versions, one APPROVED version, audit log, rollback) live in
app.repositories.file.ontology_repository."""
from __future__ import annotations

from app.domain.pipeline_context import PipelineContext
from app.repositories.file.ontology_repository import OntologyRepository
from kg_pipeline.models.ontology_models import Ontology
from kg_pipeline.ontology_compiler.validator import validate_ontology


def run(ctx: PipelineContext, author: str, reviewer: str, repo: OntologyRepository | None = None) -> Ontology:
    """Save the validated draft as a new version and approve it (four-eyes)."""
    draft = ctx.hybrid_draft or ctx.manual_ontology
    if draft is None:
        raise RuntimeError("Stage 5/7 must run first")
    repo = repo or OntologyRepository()
    previous = repo.get_approved(draft.ontology_id)
    # re-validate against the CURRENT approved version (conflict / breaking-change checks)
    report = validate_ontology(draft, ctx.catalog, previous)
    ctx.ontology_report = report
    if not report.ok:
        ctx.log(9, f"Approval blocked: {report.summary()}", "error")
        raise ValueError(f"validation failed: {report.summary()}")
    saved = repo.save_draft(draft, actor=author)
    repo.submit(saved.ontology_id, saved.version, actor=author)
    approved = repo.approve(saved.ontology_id, saved.version, reviewer=reviewer, report=report)
    ctx.invalidate_from(9)
    ctx.approved_ontology = approved
    ctx.log(9, f"Ontology '{approved.ontology_id}' v{approved.version} saved by {author} and approved by {reviewer}"
               + (f" (v{previous.version} superseded)" if previous else ""))
    ctx.mark_done(9)
    return approved


def use_existing(ctx: PipelineContext, ontology_id: str, repo: OntologyRepository | None = None) -> Ontology:
    """Skip editing and build from the already-approved version in the repository."""
    repo = repo or OntologyRepository()
    approved = repo.get_approved(ontology_id)
    if approved is None:
        raise ValueError(f"no approved version for {ontology_id}")
    ctx.invalidate_from(9)
    ctx.approved_ontology = approved
    ctx.log(9, f"Using approved ontology '{ontology_id}' v{approved.version} from the repository")
    ctx.mark_done(9)
    return approved
