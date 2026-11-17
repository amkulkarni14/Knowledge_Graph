"""Stage 16 - Store the graph (versioned graph store; optional Neo4j).

What : write each validated graph as an immutable snapshot
           storage/graphs/<ontology_id>/<build_id>/
               graph.json.gz    node-link JSON - primary format, language neutral, lossless
               graph.graphml    interchange (Gephi, yEd, Cytoscape, Neo4j APOC import)
               quarantine.json  rows that did not become nodes/edges, with reasons
               manifest.json    ontology version, counts, watermarks, validation, SHA-256 checksums
           storage/graphs/<ontology_id>/CURRENT  -> active build_id (moved ONLY if validation passed)
       Optionally push the same graph into Neo4j (phase-2 serving store).
Why  : a NetworkX graph lives only in process memory. Snapshots give restart, rollback,
       audit ("which graph produced this report?") and a base for incremental runs.
       Pickle is not used: it is version-specific and unsafe to load from untrusted files.
"""
from __future__ import annotations

from app.domain.pipeline_context import PipelineContext
from app.repositories.file.snapshot_store import load_graph, save_graph
from kg_pipeline.graph_builder.loaders.neo4j_loader import push_to_neo4j


def run(ctx: PipelineContext, neo4j: dict | None = None) -> dict:
    if ctx.graph is None or ctx.graph_report is None:
        raise RuntimeError("Stages 14 and 15 must run first")
    manifest = save_graph(ctx.graph, ctx.graph_report, ctx.build_stats["quarantine"])
    if manifest["published"]:
        reloaded = load_graph(manifest["ontology_id"], manifest["build_id"])
        manifest["reload_check"] = (reloaded.number_of_nodes() == ctx.graph.number_of_nodes()
                                    and reloaded.number_of_edges() == ctx.graph.number_of_edges())
        ctx.log(16, f"Snapshot {manifest['build_id']} saved and marked CURRENT "
                    f"(reload check {'ok' if manifest['reload_check'] else 'FAILED'})")
    else:
        ctx.log(16, f"Snapshot {manifest['build_id']} saved for investigation but NOT published "
                    "(validation failed); previous CURRENT kept", "warning")
    if neo4j and manifest["published"]:
        manifest["neo4j"] = push_to_neo4j(ctx.graph, **neo4j)
        ctx.log(16, f"Pushed to Neo4j: {manifest['neo4j']}")
    ctx.snapshot = manifest
    ctx.mark_done(16)
    return manifest
