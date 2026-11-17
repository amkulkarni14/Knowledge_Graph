"""Stage 15 - Check the graph before anyone can use it.

Reconciliation (proves nothing was lost silently):
    per class        : source rows = nodes + merged + quarantined
    per relationship : rows read   = edges created + duplicates + null refs + dangling + quarantined
Ontology conformance: known classes, required attributes, allowed (type, source, target)
triples, cardinality, forbidden cycles. Isolated nodes are listed for review.
Out : ctx.graph_report {ok, errors, warnings, checks[], nodes_by_class, edges_by_type}
"""
from __future__ import annotations

from app.domain.pipeline_context import PipelineContext
from kg_pipeline.graph_builder.graph_validator import validate_graph


def run(ctx: PipelineContext) -> dict:
    if ctx.graph is None or not ctx.is_done(14):
        raise RuntimeError("Stage 14 must run first")
    report = validate_graph(ctx.graph, ctx.approved_ontology, ctx.extraction.staged, ctx.build_stats)
    ctx.invalidate_from(15)
    ctx.graph_report = report
    ctx.log(15, f"Graph validation {'PASSED' if report['ok'] else 'FAILED'}: {len(report['errors'])} error(s), "
                f"{len(report['warnings'])} warning(s)", "info" if report["ok"] else "error")
    if report["ok"]:
        ctx.mark_done(15)
    return report
