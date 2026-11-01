from fastapi import APIRouter, HTTPException
from app.investigation.orchestrator import load_run
from app.graph.graph_builder import build_graph
from app.graph.graph_analyzer import analyze, to_flow

router = APIRouter(tags=["graph"])


def _graph(run_id):
    run = load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return build_graph(run)


@router.get("/graph/{run_id}")
def graph(run_id: str, level: str = "all"):
    G = _graph(run_id)
    return {**to_flow(G, level), "analysis": analyze(G)}


@router.get("/graph/{run_id}/node/{node_id}")
def node(run_id: str, node_id: str):
    G = _graph(run_id)
    if node_id not in G:
        raise HTTPException(404, "Node not found")
    edges = [{"from": u, "to": v, **{k: d[k] for k in d if k != "evidence"}, "evidence": d.get("evidence")}
             for u, v, d in list(G.in_edges(node_id, data=True)) + list(G.out_edges(node_id, data=True))
             if d["rel"] != "contains"]
    return {"id": node_id, "data": dict(G.nodes[node_id]), "relationships": edges}