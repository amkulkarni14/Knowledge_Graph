"""Stage 4 - Understand the structure (schema analysis).

What : classify each table (entity / event / bridge / lookup / log), find FK-based
       relationship candidates and columns that look like UNDECLARED foreign keys.
Why  : different table kinds become different graph things; a bridge table must
       become edges, not a node type, or the graph gets cluttered.
Out  : ctx.table_analysis (list of dicts) - a first guess the data owner confirms.
"""
from __future__ import annotations

from app.domain.pipeline_context import PipelineContext
from kg_pipeline.metadata_extractor.key_detector import classify_with_reason, undeclared_fk_candidates

BECOMES = {
    "entity": "Node type (class)",
    "event": "Node type (class) with a date",
    "bridge": "Edges (M:N) with properties",
    "lookup": "Node property (usually)",
    "log": "Excluded or aggregated",
}


def run(ctx: PipelineContext) -> list[dict]:
    if ctx.catalog is None:
        raise RuntimeError("Stage 3 (schema extraction) must run first")
    cat = ctx.catalog
    result = []
    for t in cat.tables.values():
        kind, reason = classify_with_reason(t, cat)
        cands = undeclared_fk_candidates(t, cat)
        result.append({
            "table": t.name, "type": kind, "becomes": BECOMES[kind], "reason": reason,
            "primary_key": t.primary_key, "foreign_keys": [f"{','.join(fk.columns)} → {fk.ref_table}"
                                                           for fk in t.foreign_keys],
            "referenced_by": cat.referenced_by(t.name), "rows": t.row_estimate,
            "undeclared_fk": cands,
        })
    ctx.invalidate_from(4)
    ctx.table_analysis = result
    counts = {}
    for r in result:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    ctx.log(4, "Table types: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for r in result:
        for c in r["undeclared_fk"]:
            ctx.log(4, f"{c['table']}.{c['column']} looks like a link to {c['probably_references']} "
                       "but has no declared FK", "warning")
    ctx.mark_done(4)
    return result
