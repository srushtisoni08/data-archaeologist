import re
from collections import defaultdict
from itertools import combinations
from rapidfuzz import fuzz
import pandas as pd
from app.discovery.common import get_df, completed

W = {"name": 0.50, "email": 0.35, "phone": 0.15}
SAME, UNSURE = 0.90, 0.60
BLOCK_MAX = 300


def _tok(v) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", " ", str(v).lower()).split() if v else []


def _val(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return str(v).strip() or None


def _records(profiles: list[dict]) -> list[dict]:
    recs = []
    for p in profiles:
        cols = {t: next((c["name"] for c in p["columns"] if c["semantic_type"] == t), None)
                for t in ("person_name", "email", "phone")}
        if not any(cols.values()):
            continue
        keys = p["fingerprint"]["candidate_keys"]
        for i, row in enumerate(get_df(p["dataset_id"]).to_dict("records")):
            name = _val(row.get(cols["person_name"])) if cols["person_name"] else None
            email = _val(row.get(cols["email"])) if cols["email"] else None
            phone = _val(row.get(cols["phone"])) if cols["phone"] else None
            digits = re.sub(r"\D", "", phone) if phone else ""
            r = {"dataset_id": p["dataset_id"], "key": str(row.get(keys[0], i)) if keys else str(i),
                 "name": name, "tok": _tok(name), "email": email.lower() if email else None,
                 "phone": digits[-10:] if len(digits) >= 8 else None}
            if r["tok"] or r["email"] or r["phone"]:
                recs.append(r)
    return recs


def _name_sim(a: list[str], b: list[str]):
    if not a or not b:
        return None
    s = fuzz.token_sort_ratio(" ".join(a), " ".join(b)) / 100
    if a[-1] == b[-1] and a[0][0] == b[0][0] and (len(a[0]) == 1 or len(b[0]) == 1 or a[0] == b[0]):
        s = max(s, 0.9)  # "A. Patel" ~ "Asha Patel"
    return s


def _score(a: dict, b: dict):
    sig = {"name": _name_sim(a["tok"], b["tok"])}
    if a["email"] and b["email"]:
        sig["email"] = 1.0 if a["email"] == b["email"] else \
            fuzz.ratio(a["email"].split("@")[0], b["email"].split("@")[0]) / 100 * 0.8
    if a["phone"] and b["phone"]:
        sig["phone"] = 1.0 if a["phone"] == b["phone"] else 0.0
    sig = {k: round(v, 3) for k, v in sig.items() if v is not None}
    if not sig:
        return None
    return sum(W[k] * v for k, v in sig.items()) / sum(W[k] for k in sig), sig


def resolve_entities(profiles: list[dict]) -> dict:
    recs = _records(completed(profiles))
    blocks = defaultdict(list)
    for i, r in enumerate(recs):
        if r["email"]: blocks["e:" + r["email"]].append(i)
        if r["phone"]: blocks["p:" + r["phone"]].append(i)
        if r["tok"]: blocks["n:" + r["tok"][-1]].append(i)
    pairs, skipped = set(), 0
    for ids in blocks.values():
        if len(ids) > BLOCK_MAX:
            skipped += 1
            continue
        pairs.update(combinations(ids, 2))

    links = []
    for i, j in pairs:
        res = _score(recs[i], recs[j])
        if not res:
            continue
        score, sig = res
        exact_id = sig.get("email") == 1.0 or sig.get("phone") == 1.0
        if score >= SAME and len(sig) >= 2:
            decision, reason = "same_entity", "strong agreement across multiple signals"
        elif score >= UNSURE:
            decision, reason = "uncertain", "single signal or moderate similarity"
        elif exact_id:
            decision, reason = "uncertain", "shared identifier but names differ (shared mailbox?)"
        else:
            continue  # different_entity: not reported
        links.append({"i": i, "j": j, "score": round(score, 3), "signals": sig,
                      "decision": decision, "reason": reason})

    parent = list(range(len(recs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for l in links:
        parent[find(l["i"])] = find(l["j"])
    groups = defaultdict(list)
    for l in links:
        groups[find(l["i"])].append(l)

    entities = []
    for ls in sorted(groups.values(), key=len, reverse=True):
        idx = sorted({x for l in ls for x in (l["i"], l["j"])})
        entities.append({
            "records": [{k: recs[x][k] for k in ("dataset_id", "key", "name", "email")} for x in idx],
            "datasets": sorted({recs[x]["dataset_id"] for x in idx}),
            "status": "same_entity" if all(l["decision"] == "same_entity" for l in ls) else "needs_review",
            "links": [{"a": f"{recs[l['i']]['dataset_id']}:{recs[l['i']]['key']}",
                       "b": f"{recs[l['j']]['dataset_id']}:{recs[l['j']]['key']}",
                       "score": l["score"], "signals": l["signals"],
                       "decision": l["decision"], "reason": l["reason"]} for l in ls],
        })
    for n, e in enumerate(entities, 1):
        e["entity_id"] = f"E-{n:03d}"
    return {"entities": entities, "records_compared": len(recs), "candidate_pairs": len(pairs),
            "skipped_oversized_blocks": skipped}