"""Versioned graph snapshots on disk (JSON + GraphML + manifest with checksums) and the CURRENT pointer.

    storage/graphs/<ontology_id>/<build_id>/   graph.json.gz, graph.graphml, quarantine.json, manifest.json
    storage/graphs/<ontology_id>/CURRENT       active build_id (moved ONLY if validation passed)

Pickle is not used: it is version-specific and unsafe to load from untrusted files."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx

from app.core.config import settings


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _graphml_safe(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """GraphML stores scalars only: lists/dicts become JSON strings, None is dropped."""
    H = G.copy()

    def fix(d):
        for k, v in list(d.items()):
            if v is None:
                del d[k]
            elif isinstance(v, (list, tuple, set, dict)):
                d[k] = json.dumps(sorted(v) if isinstance(v, set) else v, default=str)
    fix(H.graph)
    for _, d in H.nodes(data=True):
        fix(d)
    for *_, d in H.edges(data=True):
        fix(d)
    return H


def save_graph(G: nx.MultiDiGraph, validation: dict, quarantine: list, root: Path | None = None) -> dict:
    root = Path(root or settings.graph_store_dir)
    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = root / G.graph["ontology_id"] / build_id
    out.mkdir(parents=True, exist_ok=True)

    with gzip.open(out / "graph.json.gz", "wt", encoding="utf-8") as f:
        json.dump(nx.node_link_data(G, edges="edges"), f, default=str)
    nx.write_graphml(_graphml_safe(G), out / "graph.graphml")
    (out / "quarantine.json").write_text(json.dumps(quarantine, indent=1, default=str), encoding="utf-8")

    manifest = {
        "build_id": build_id, "ontology_id": G.graph["ontology_id"],
        "ontology_version": G.graph["ontology_version"], "build_mode": G.graph.get("build_mode"),
        "built_at": G.graph.get("built_at"), "source": G.graph.get("source"),
        "source_watermarks": G.graph.get("source_watermarks", {}),
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "nodes_by_class": validation.get("nodes_by_class", {}), "edges_by_type": validation.get("edges_by_type", {}),
        "validation": {"ok": validation["ok"], "errors": len(validation["errors"]),
                       "warnings": len(validation["warnings"])},
        "quarantined": len(quarantine),
        "files": {p.name: _sha256(p) for p in sorted(out.iterdir())},
        "published": bool(validation["ok"]),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    if validation["ok"]:
        (root / G.graph["ontology_id"] / "CURRENT").write_text(build_id, encoding="utf-8")
    manifest["path"] = str(out)
    return manifest


def current_build(ontology_id: str, root: Path | None = None) -> Optional[str]:
    p = Path(root or settings.graph_store_dir) / ontology_id / "CURRENT"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None


def list_builds(ontology_id: str, root: Path | None = None) -> list[dict]:
    base = Path(root or settings.graph_store_dir) / ontology_id
    if not base.exists():
        return []
    cur = current_build(ontology_id, root)
    rows = []
    for d in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        mf = d / "manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            rows.append({"build_id": m["build_id"], "current": m["build_id"] == cur,
                         "ontology_version": m["ontology_version"], "nodes": m["nodes"], "edges": m["edges"],
                         "valid": m["validation"]["ok"], "quarantined": m.get("quarantined", 0),
                         "built_at": (m.get("built_at") or "")[:19]})
    return rows


def set_current(ontology_id: str, build_id: str, root: Path | None = None) -> None:
    """Rollback / promote: point CURRENT at an existing, valid snapshot."""
    base = Path(root or settings.graph_store_dir) / ontology_id
    m = json.loads((base / build_id / "manifest.json").read_text(encoding="utf-8"))
    if not m["validation"]["ok"]:
        raise ValueError("only a validated build can become CURRENT")
    (base / "CURRENT").write_text(build_id, encoding="utf-8")


def load_graph(ontology_id: str, build_id: str | None = None, root: Path | None = None) -> nx.MultiDiGraph:
    base = Path(root or settings.graph_store_dir) / ontology_id
    build_id = build_id or current_build(ontology_id, root)
    if not build_id:
        raise FileNotFoundError(f"no CURRENT build for {ontology_id}")
    manifest = json.loads((base / build_id / "manifest.json").read_text(encoding="utf-8"))
    path = base / build_id / "graph.json.gz"
    if _sha256(path) != manifest["files"]["graph.json.gz"]:
        raise ValueError(f"checksum mismatch for {path}")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, directed=True, multigraph=True, edges="edges")
