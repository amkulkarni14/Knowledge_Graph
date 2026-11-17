"""Which nodes matter most in an instance graph (pure NetworkX)."""
from __future__ import annotations

import networkx as nx


def degree_ranking(G: nx.MultiDiGraph, limit: int = 15) -> list[dict]:
    """The `limit` most connected nodes (degree centrality on the undirected graph), best first."""
    S = nx.Graph(G.to_undirected())
    deg = nx.degree_centrality(S)
    return [{"node": k, "label": G.nodes[k]["label"], "centrality": v, "links": S.degree(k)}
            for k, v in sorted(deg.items(), key=lambda kv: -kv[1])[:limit]]
