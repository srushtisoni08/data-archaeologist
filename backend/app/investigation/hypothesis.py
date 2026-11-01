def build_hypotheses(evidence: list[dict]) -> list[dict]:
    ok = [e for e in evidence if "error" not in e["result"]]
    vals = {(e["result"]["source"], e["result"]["target"]): e
            for e in ok if e["tool"] == "validate_hypothesis"}
    hyps = []

    def add(**h):
        h["id"] = f"H-{len(hyps) + 1:03d}"
        h.setdefault("provenance", "inferred")
        hyps.append(h)

    for e in ok:
        if e["tool"] == "detect_relationships":
            for r in e["result"]["relationships"]:
                key = (f"{r['source_dataset']}.{r['source_column']}", f"{r['target_dataset']}.{r['target_column']}")
                v = vals.get(key)
                sup, con, notes, d = [e["id"]], [], [], {}
                conf, status = r["confidence"], "untested"
                if v:
                    d, conf, status = v["result"], v["result"]["confidence"], v["result"]["verdict"]
                    sup.append(v["id"])
                    if d["orphan_count"]:
                        con.append(v["id"])
                        notes.append(f"{d['orphan_count']} child values have no parent, e.g. {d['orphan_examples']}")
                    for x in d["orphans_found_elsewhere"]:
                        notes.append(f"Those values exist in {x['dataset']}.{x['column']}; "
                                     f"possibly records added after the parent file was exported")
                add(type="foreign_key", claim=f"{key[1]} references {key[0]} ({r['cardinality']})",
                    confidence=conf, status=status, supporting_evidence=sup, contradicting_evidence=con,
                    notes=notes, details=d, needs_review=status != "supported")
        elif e["tool"] == "resolve_entities":
            for ent in e["result"]["entities"]:
                if len(ent["records"]) < 2:
                    continue
                add(type="entity_match",
                    claim=f"{ent['entity_id']}: {len(ent['records'])} records across {ent['datasets']} may be one entity",
                    confidence=min(l["score"] for l in ent["links"]), status=ent["status"],
                    supporting_evidence=[e["id"]], contradicting_evidence=[],
                    notes=[f"{l['a']} ~ {l['b']}: {l['signals']}" for l in ent["links"][:3]],
                    details={}, needs_review=ent["status"] != "same_entity")
        elif e["tool"] == "detect_contradictions":
            for c in e["result"]["contradictions"]:
                add(type="contradiction",
                    claim=(f"{c['file_a']} and {c['file_b']} disagree on '{c['column_a']}' "
                           f"for {c['conflict_count']} of {c['compared']} shared records"),
                    confidence=None, status="unresolved" if c["requires_human"] else "likely_update",
                    supporting_evidence=[e["id"]], contradicting_evidence=[],
                    notes=[c["assessment"]] + [f"key {x['key']}: {x['value_a']!r} vs {x['value_b']!r} "
                                               f"(other fields agreeing {x['other_fields_agreeing']})"
                                               for x in c["conflicts"][:3]],
                    details={}, needs_review=c["requires_human"])
    return hyps


def open_questions(hyps: list[dict]) -> list[str]:
    q = []
    for h in hyps:
        d = h.get("details") or {}
        if h["type"] == "foreign_key" and h["status"] == "untested":
            q.append(f"Untested: {h['claim']}")
        elif h["type"] == "foreign_key" and d.get("orphan_count"):
            if d["orphans_found_elsewhere"]:
                x = d["orphans_found_elsewhere"][0]
                q.append(f"Which file is the authoritative parent for {d['target']}? "
                         f"Orphans {d['orphan_examples']} exist in {x['dataset']}.{x['column']}.")
            else:
                q.append(f"{d['orphan_count']} values in {d['target']} have no parent anywhere: {d['orphan_examples']}")
        elif h["type"] in ("contradiction", "entity_match") and h["needs_review"]:
            q.append(f"Human review needed: {h['claim']}")
    return q