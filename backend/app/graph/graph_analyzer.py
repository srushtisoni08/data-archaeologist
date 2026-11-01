import networkx as nx


def analyze(G: nx.MultiDiGraph) -> dict:
    ds = [n for n, d in G.nodes(data=True) if d["kind"] == "dataset"]
    H = nx.Graph()
    H.add_nodes_from(ds)
    for u, v, d in G.edges(data=True):
        if d["rel"] in ("references", "derived_from") and G.nodes[u].get("kind") == "column":
            H.add_edge(G.nodes[u]["dataset"], G.nodes[v]["dataset"])
        elif d["rel"] == "derived_from":
            H.add_edge(u, v)
    comps = [sorted(c) for c in nx.connected_components(H)]
    ref = nx.DiGraph()
    ref.add_nodes_from(ds)
    for u, v, d in G.edges(data=True):
        if d["rel"] == "references":
            ref.add_edge(G.nodes[u]["dataset"], G.nodes[v]["dataset"])
    central = sorted(nx.degree_centrality(H).items(), key=lambda x: -x[1]) if len(ds) > 1 else []
    return {"clusters": comps, "isolated_datasets": [c[0] for c in comps if len(c) == 1],
            "most_connected": [{"dataset": k, "score": round(v, 3)} for k, v in central[:3]],
            "reference_cycles": [c for c in nx.simple_cycles(ref)],
            "node_count": G.number_of_nodes(), "edge_count": G.number_of_edges()}


def to_flow(G: nx.MultiDiGraph, level: str = "all") -> dict:
    """React Flow payload. level: 'datasets' hides column nodes and 'contains' edges."""
    keep = {n for n, d in G.nodes(data=True) if level == "all" or d["kind"] != "column"}
    pos, cols = {}, {}
    for n, d in G.nodes(data=True):
        if d["kind"] == "dataset":
            pos[n] = (len(cols) * 380, 0)
            cols[n] = 0
    for n, d in G.nodes(data=True):
        if d["kind"] == "column":
            i = cols[d["dataset"]] = cols[d["dataset"]] + 1
            pos[n] = (pos[d["dataset"]][0], 110 + i * 56)
        elif d["kind"] == "entity":
            pos[n] = (len([x for x in pos if x.startswith("E-")]) * 160, -180)
    nodes = [{"id": n, "type": d["kind"], "position": {"x": pos.get(n, (0, 0))[0], "y": pos.get(n, (0, 0))[1]},
              "data": {k: v for k, v in d.items() if k != "kind"} | {"kind": d["kind"]}}
             for n, d in G.nodes(data=True) if n in keep]
    edges = []
    for i, (u, v, d) in enumerate(G.edges(data=True)):
        if u in keep and v in keep and not (level == "datasets" and d["rel"] == "contains"):
            edges.append({"id": f"e{i}", "source": u, "target": v, "label": d["rel"],
                          "animated": d["provenance"] == "inferred" and d["rel"] in ("references", "derived_from"),
                          "data": d})
    return {"nodes": nodes, "edges": edges, "hints": G.graph.get("hints", [])}