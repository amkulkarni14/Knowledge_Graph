"""Bounded views and traversals of an instance graph (pure NetworkX: no I/O, no UI).

A client should never have to receive the whole graph of a large build: `ego` takes a few hops around a node and
`limit_graph` caps the node count. `shortest_connection` finds how two nodes are linked."""
from __future__ import annotations

import networkx as nx


def ego(G: nx.MultiDiGraph, node: str, radius: int = 1) -> nx.MultiDiGraph:
    radius = max(1, min(radius, 3))
    keep = nx.ego_graph(G.to_undirected(as_view=True), node, radius=radius).nodes
    return G.subgraph(keep).copy()


def limit_graph(G: nx.MultiDiGraph, max_nodes: int = 300, labels: set[str] | None = None) -> nx.MultiDiGraph:
    nodes = [n for n, d in G.nodes(data=True) if not labels or d.get("label") in labels]
    if len(nodes) > max_nodes:
        nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)[:max_nodes]
    return G.subgraph(nodes).copy()


def shortest_connection(G: nx.MultiDiGraph, source: str, target: str) -> tuple[list[str], list[dict]] | None:
    """Shortest path ignoring edge direction, as (nodes, hops); None when the two nodes are not connected.
    Each hop names the relationship and whether it was followed forward (→) or backward (←)."""
    U = G.to_undirected(as_view=True)
    if not nx.has_path(U, source, target):
        return None
    path = nx.shortest_path(U, source, target)
    hops = []
    for p, q in zip(path, path[1:]):
        d = G.get_edge_data(p, q) or G.get_edge_data(q, p)
        hops.append({"from": p, "relationship": ("→ " if G.has_edge(p, q) else "← ") + next(iter(d.values()))["type"],
                     "to": q})
    return path, hops
