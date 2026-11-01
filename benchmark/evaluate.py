import itertools
import json
import re
import sys
from pathlib import Path
import httpx

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.discovery.schema_matching import name_sim  # noqa: E402

BASE = "http://localhost:8000/api"
T = json.loads((HERE / "ground_truth.json").read_text())
canon = lambda f: T["versions"].get(f, f)
OUT = {}


def prf(pred, truth, ignore=frozenset()):
    pred, truth = set(pred), set(truth)
    pred -= set(ignore) - truth
    tp, fp, fn = len(pred & truth), len(pred - truth), len(truth - pred)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3),
            "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}, sorted(pred - truth, key=str), sorted(truth - pred, key=str)


def table(title, rows):
    print(f"\n### {title}\n| method | TP | FP | FN | precision | recall | F1 |\n|---|---|---|---|---|---|---|")
    OUT[title] = {}
    for name, s in rows:
        OUT[title][name] = s
        print(f"| {name} | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']} | {s['recall']} | {s['f1']} |")


def main():
    cl = httpx.Client(timeout=900)
    r = cl.delete(f"{BASE}/datasets")
    if r.status_code != 200 or cl.get(f"{BASE}/datasets").json():
        sys.exit(f"reset failed ({r.status_code}); delete backend\\storage\\profiles\\* and originals\\* manually")
    files = [("files", (p.name, p.read_bytes(), "text/csv")) for p in sorted((HERE / "data").glob("*.csv"))]
    up = cl.post(f"{BASE}/uploads", files=files).json()
    bad = [u for u in up if u["ingestion_status"] != "completed"]
    if bad:
        sys.exit(f"ingestion failed: {bad}")
    id2f = {u["dataset_id"]: u["filename"] for u in up}
    cols = {f: [c["name"] for c in cl.get(f"{BASE}/datasets/{d}").json()["columns"]] for d, f in id2f.items()}

    analysis = cl.post(f"{BASE}/analyze").json()
    disc = cl.get(f"{BASE}/relationships").json()
    run = cl.post(f"{BASE}/investigations", json={"objective": "Investigate how these datasets are connected "
                                                  "and find inconsistencies"}).json()
    lin = cl.get(f"{BASE}/lineage/{run['run_id']}").json()
    ev = lambda tool, default: next((e["result"] for e in run["evidence"]
                                     if e["tool"] == tool and "error" not in e["result"]), default)

    # ---- A. schema matching
    truth_cols = {frozenset(map(tuple, p)) for g in T["column_groups"] for p in itertools.combinations(g, 2)}
    allpairs = [frozenset({(fa, ca), (fb, cb)}) for fa, fb in itertools.combinations(sorted(cols), 2)
                for ca in cols[fa] for cb in cols[fb]]
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    exact = [p for p in allpairs if len({norm(c) for _, c in p}) == 1]
    fuzzy = []
    for p in allpairs:
        (_, a), (_, b) = sorted(p)
        if name_sim(a, b) >= 0.8:
            fuzzy.append(p)
    rows = [("exact name", prf(exact, truth_cols)[0]), ("fuzzy name >=0.8", prf(fuzzy, truth_cols)[0])]
    shown = {}
    for t in (0.6, 0.7, 0.8, 0.9):
        h = [frozenset({(id2f[m["source_dataset"]], m["source_column"]), (id2f[m["target_dataset"]], m["target_column"])})
             for m in disc["column_matches"] if m["confidence"] >= t]
        s, fp_, fn_ = prf(h, truth_cols)
        rows.append((f"hybrid >={t}", s))
        shown[t] = (fp_, fn_)
    table("A. Schema matching", rows)
    fmt = lambda xs: [" ~ ".join(f"{f}.{c}" for f, c in sorted(x)) for x in xs[:8]]
    print("  @0.8 missed:", fmt(shown[0.8][1]), "\n  @0.7 false matches:", fmt(shown[0.7][0]))

    # ---- FK discovery: fixed pipeline vs validating agent
    key = lambda s, sc, t, tc: (canon(id2f[s]), sc, canon(id2f[t]), tc)
    truth_fk = {tuple([canon(a), b, canon(c), d]) for a, b, c, d in T["fks"]}
    acc = {tuple([canon(a), b, canon(c), d]) for a, b, c, d in T["acceptable_fks"]}
    fixed = {key(r["source_dataset"], r["source_column"], r["target_dataset"], r["target_column"])
             for r in disc["relationships"]}
    agent = set()
    for h in run["hypotheses"]:
        d = h.get("details") or {}
        if h["type"] == "foreign_key" and d.get("source") and h["status"] in ("supported", "partially_supported"):
            (s, sc), (t, tc) = d["source"].split(".", 1), d["target"].split(".", 1)
            agent.add(key(s, sc, t, tc))
    fixed = {k for k in fixed if k[0] != k[2]}
    agent = {k for k in agent if k[0] != k[2]}
    sf, fpf, fnf = prf(fixed, truth_fk, acc)
    sa, fpa, fna = prf(agent, truth_fk, acc)
    table("B. Foreign-key discovery", [("fixed pipeline (all candidates)", sf), ("agent (validated only)", sa)])
    print("  FP fixed:", fpf[:6], "\n  FN fixed:", fnf[:6], "\n  FP agent:", fpa[:6], "\n  FN agent:", fna[:6])

    # ---- entity resolution (same_entity links, transitive)
    def pairs(res):
        par = {}

        def find(x):
            par.setdefault(x, x)
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        rec = lambda s: f"{id2f[s.split(':', 1)[0]]}:{s.split(':', 1)[1]}"
        for e in res.get("entities", []):
            for l in e["links"]:
                if l["decision"] == "same_entity":
                    par[find(rec(l["a"]))] = find(rec(l["b"]))
        g = {}
        for x in list(par):
            g.setdefault(find(x), []).append(x)
        return {frozenset(p) for m in g.values() for p in itertools.combinations(sorted(m), 2)}
    truth_ent = {frozenset(p) for c in T["entity_clusters"] for p in itertools.combinations(sorted(c), 2)}
    se, fpe, fne = prf(pairs(analysis["entities"]), truth_ent)
    sg, _, _ = prf(pairs(ev("resolve_entities", {})), truth_ent)
    table("C. Entity resolution (pairwise)", [("fixed pipeline", se), ("agent run", sg)])
    print("  FP examples:", [sorted(x) for x in fpe[:4]], "\n  FN examples:", [sorted(x) for x in fne[:4]])
    uncertain = sum(l["decision"] == "uncertain" for e in analysis["entities"]["entities"] for l in e["links"])
    print(f"  links flagged for human review: {uncertain}")

    # ---- anomalies
    truth_an = {tuple(a) for a in T["anomalies"]}
    an = lambda lst: {(id2f[a["dataset_id"]], a["column"], a["type"]) for a in lst}
    sa1, fp1, fn1 = prf(an(analysis["anomalies"]), truth_an)
    sa2, _, _ = prf(an(run["anomalies"]), truth_an)
    table("D. Anomaly detection (file, column, type)", [("fixed pipeline", sa1), ("agent run", sa2)])
    print("  FP:", fp1[:8], "\n  FN:", fn1)

    # ---- contradictions
    found = {}
    for c in analysis["contradictions"]:
        found[c["column_a"]] = found.get(c["column_a"], 0) + c["conflict_count"]
    print("\n### E. Contradictions (injected vs found)\n| column | injected | found |\n|---|---|---|")
    for c_ in sorted(set(T["conflicts"]) | set(found)):
        print(f"| {c_} | {T['conflicts'].get(c_, 0)} | {found.get(c_, 0)} |")

    # ---- lineage
    edges = [(id2f[e["source"]], id2f[e["target"]]) for e in lin["edges"]]
    sl, fpl, fnl = prf({frozenset(e) for e in edges}, {frozenset(e) for e in T["lineage"]})
    table("F. Lineage (undirected pair detection)", [("evidence-based", sl)])
    hit = [e for e in edges if frozenset(e) in {frozenset(x) for x in T["lineage"]}]
    ok = sum(list(e) in T["lineage"] for e in hit)
    print(f"  direction correct: {ok}/{len(hit)} | extra edges: {[sorted(x) for x in fpl]}")

    # ---- agent stats
    pl = {}
    for s in run["steps"]:
        pl[s["planner"]] = pl.get(s["planner"], 0) + 1
    print(f"\nAgent: {len(run['steps'])} tool calls, planners {pl}, open questions {len(run['open_questions'])}")
    (HERE / "results.json").write_text(json.dumps(OUT, indent=1))


main()