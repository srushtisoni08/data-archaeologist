import json
import re
from datetime import datetime
from app.database import store
from app.investigation import llm, prompts
from app.investigation.tools import Ctx, REGISTRY
from app.investigation.evidence import EvidenceStore
from app.investigation.hypothesis import build_hypotheses, open_questions

MAX_STEPS = 45
PERSON_TYPES = {"person_name", "email", "phone"}


def _key(tool, args):
    return tool + json.dumps(args, sort_keys=True)


def _last(ev, tool):
    return next((e for e in reversed(ev.items) if e["tool"] == tool and "error" not in e["result"]), None)


def _rules_next(ctx, ev, done):
    for p in ctx.profiles:
        a = {"dataset_id": p["dataset_id"]}
        if _key("inspect_dataset", a) not in done:
            return "inspect_dataset", a, "Understand each dataset before comparing them"
    rels = None
    if len(ctx.profiles) > 1:
        for t, why in (("find_column_matches", "Find columns that may describe the same thing"),
                       ("detect_relationships", "Look for key relationships between datasets")):
            if _key(t, {}) not in done:
                return t, {}, why
        rels = _last(ev, "detect_relationships")
        cands = [r for r in rels["result"]["relationships"] if not r.get("dominated_by")][:25] if rels else []
        for r in cands:
            a = {"source_dataset": r["source_dataset"], "source_column": r["source_column"],
                 "target_dataset": r["target_dataset"], "target_column": r["target_column"]}
            if _key("validate_hypothesis", a) not in done:
                return "validate_hypothesis", a, (f"Test candidate {r['source_dataset']}.{r['source_column']} -> "
                                                  f"{r['target_dataset']}.{r['target_column']} with measured coverage")
    if any(c["semantic_type"] in PERSON_TYPES for p in ctx.profiles for c in p["columns"]) \
       and _key("resolve_entities", {}) not in done:
        return "resolve_entities", {}, "Person-like columns exist; check for duplicate entities"
    if _key("detect_anomalies", {}) not in done:
        return "detect_anomalies", {}, "Scan for invalid values and broken references"
    if rels and any(r["cardinality"] == "one_to_one" for r in rels["result"]["relationships"]) \
       and _key("detect_contradictions", {}) not in done:
        return "detect_contradictions", {}, "1:1 linked files exist; compare shared records for conflicts"
    return None


def _llm_next(objective, ctx, ev, done):
    out = llm.chat_json(prompts.PLANNER, prompts.planner_user(objective, ctx.profiles, ev.items, REGISTRY))
    if not out:
        return None
    tool, args = out.get("tool"), out.get("args") or {}
    if tool == "finish":
        return "finish", {}, out.get("reason", "")
    spec = REGISTRY.get(tool)
    if not spec or set(args) != set(spec["args"]) or _key(tool, args) in done:
        return None
    return tool, args, out.get("reason", "")


def _narrative(objective, hyps, questions):
    payload = json.dumps({"objective": objective, "hypotheses": [
        {k: h[k] for k in ("id", "claim", "confidence", "status", "notes")} for h in hyps],
        "open_questions": questions})
    txt = llm.chat(prompts.EXPLAIN, payload)
    if txt:
        return txt
    lines = [f"{h['id']} [{h['status']}, conf {h['confidence']}] {h['claim']}" for h in hyps]
    return "\n".join(lines + [f"OPEN: {q}" for q in questions]) or "No findings."


def run_investigation(objective: str) -> dict:
    ctx, ev, done, steps = Ctx(), EvidenceStore(), set(), []
    for n in range(1, MAX_STEPS + 1):
        pick, planner = _llm_next(objective, ctx, ev, done), "llm"
        if pick is None:
            pick, planner = _rules_next(ctx, ev, done), "rules"
        if pick is None or pick[0] == "finish":
            break
        tool, args, reason = pick
        done.add(_key(tool, args))
        try:
            result, summary = REGISTRY[tool]["fn"](ctx, **args)
        except Exception as e:
            result, summary = {"error": str(e)}, f"failed: {e}"
        e = ev.add(tool, args, result, summary)
        steps.append({"step": n, "tool": tool, "args": args, "reason": reason, "planner": planner,
                      "evidence_id": e["id"], "ok": "error" not in result})
    hyps = build_hypotheses(ev.items)
    questions = open_questions(hyps)
    anomalies = [a for e in ev.items if e["tool"] == "detect_anomalies" and "error" not in e["result"]
                 for a in e["result"]["anomalies"]]
    run = {"run_id": datetime.now().strftime("inv_%Y%m%d_%H%M%S"), "objective": objective,
           "llm_enabled": llm.enabled(), "steps": steps, "hypotheses": hyps, "anomalies": anomalies,
           "open_questions": questions, "narrative": _narrative(objective, hyps, questions),
           "evidence": ev.items}
    store.save_json(f"run_{run['run_id']}", run)
    return run


def load_run(run_id: str) -> dict | None:
    return store.load_json(f"run_{run_id}")


def answer(run: dict, question: str) -> str:
    hyps = run["hypotheses"]
    words = set(re.findall(r"[a-z0-9_]+", question.lower()))
    scored = sorted(hyps, key=lambda h: -len(words & set(re.findall(r"[a-z0-9_]+", (h["claim"] + " ".join(h["notes"])).lower()))))
    picked = [h for h in scored[:2] if words & set(re.findall(r"[a-z0-9_]+", h["claim"].lower()))] or scored[:3]
    ev = {e["id"]: e for e in run["evidence"]}
    ctx = json.dumps([{"claim": h["claim"], "confidence": h["confidence"], "status": h["status"], "notes": h["notes"],
                       "evidence": [ev[i]["summary"] for i in h["supporting_evidence"] + h["contradicting_evidence"]]}
                      for h in picked])
    txt = llm.chat(prompts.EXPLAIN, f"Question: {question}\nFindings: {ctx}")
    if txt:
        return txt
    out = []
    for h in picked:
        out.append(f"{h['claim']} — status: {h['status']}, confidence: {h['confidence']}")
        out += [f"  evidence: {ev[i]['summary']}" for i in h["supporting_evidence"]]
        out += [f"  contradicting: {ev[i]['summary']}" for i in h["contradicting_evidence"]]
        out += [f"  note: {n}" for n in h["notes"]]
    return "\n".join(out) or "No relevant findings yet."