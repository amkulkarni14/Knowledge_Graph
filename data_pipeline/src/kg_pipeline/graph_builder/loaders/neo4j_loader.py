"""Optional phase-2 store: load a validated graph into Neo4j (idempotent MERGE in batches)."""
from __future__ import annotations

import json
import re

import networkx as nx

_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")


def push_to_neo4j(G: nx.MultiDiGraph, uri: str, user: str, password: str, batch: int = 5000) -> dict:
    """Optional phase-2 store. Labels / relationship types come from the validated ontology
    (PascalCase / UPPER_SNAKE); they are re-checked here because Cypher cannot parameterise them."""
    from neo4j import GraphDatabase      # optional dependency: pip install neo4j

    def scalar(d):
        return {k: (json.dumps(v, default=str) if isinstance(v, (list, dict)) else v)
                for k, v in d.items() if v is not None}

    counts = {"nodes": 0, "edges": 0}
    with GraphDatabase.driver(uri, auth=(user, password)) as drv, drv.session() as s:
        for label in sorted({d["label"] for _, d in G.nodes(data=True)}):
            if not _LABEL_RE.match(label):
                raise ValueError(f"unsafe label {label!r}")
            s.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.id IS UNIQUE")
            rows = [{"id": n, "props": scalar(d)} for n, d in G.nodes(data=True) if d["label"] == label]
            for i in range(0, len(rows), batch):
                s.run(f"UNWIND $rows AS r MERGE (n:`{label}` {{id: r.id}}) SET n += r.props", rows=rows[i:i + batch])
            counts["nodes"] += len(rows)
        for rtype in sorted({d["type"] for *_, d in G.edges(data=True)}):
            if not _LABEL_RE.match(rtype):
                raise ValueError(f"unsafe relationship type {rtype!r}")
            rows = [{"u": u, "v": v, "k": k, "props": scalar(d)}
                    for u, v, k, d in G.edges(keys=True, data=True) if d["type"] == rtype]
            for i in range(0, len(rows), batch):
                s.run(f"UNWIND $rows AS r MATCH (a {{id: r.u}}), (b {{id: r.v}}) "
                      f"MERGE (a)-[e:`{rtype}` {{key: r.k}}]->(b) SET e += r.props", rows=rows[i:i + batch])
            counts["edges"] += len(rows)
    return counts
