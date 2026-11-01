import { useState, type ReactNode } from "react";
import { api } from "./api";

const pct = (c: any) => (c == null ? "n/a" : Number(c).toFixed(2));
const Tag = ({ c = "bg-slate-700", children }: { c?: string; children: ReactNode }) => (
  <span className={`rounded px-1.5 py-0.5 ${c}`}>{children}</span>
);

function EdgeView({ title, d }: { title: string; d: any }) {
  return (
    <div className="mb-2 space-y-1 rounded border border-slate-700 p-2">
      <div className="break-all font-medium">{title}</div>
      <div className="flex flex-wrap gap-1 text-[11px]">
        <Tag>{d.rel}</Tag>
        <Tag c={d.provenance === "observed" ? "bg-emerald-800" : "bg-amber-800"}>{d.provenance}</Tag>
        <Tag>conf {pct(d.confidence)}</Tag>
        {d.status && <Tag>{d.status}</Tag>}
        {d.needs_review && <Tag c="bg-red-800">needs review</Tag>}
      </div>
      {d.notes?.map((n: string, i: number) => <p key={i} className="text-slate-300">• {n}</p>)}
      {d.transformations?.map((n: string, i: number) => <p key={i} className="text-slate-300">• {n}</p>)}
      {d.conflicts?.map((c: any, i: number) => (
        <p key={i} className="text-red-300">key {c.key}: {String(c.value_a)} vs {String(c.value_b)}</p>
      ))}
      {d.caveat && <p className="text-[11px] text-amber-300">{d.caveat}</p>}
      {d.evidence && (
        <details>
          <summary className="cursor-pointer text-slate-400">evidence</summary>
          <pre className="whitespace-pre-wrap text-[10px]">{JSON.stringify(d.evidence, null, 1)}</pre>
        </details>
      )}
    </div>
  );
}

function Inspector({ sel }: { sel: any }) {
  if (!sel) return <p className="text-slate-400">Click a node or edge to see its evidence.</p>;
  if (sel.type === "edge") return <EdgeView title={`${sel.source} → ${sel.target}`} d={sel.data} />;
  const d = sel.data;
  return (
    <>
      <div className="mb-2">
        <div className="text-sm font-semibold">{sel.id}</div>
        <div className="text-slate-400">
          {d.kind}{d.semantic_type ? ` · ${d.semantic_type}` : ""}{d.rows != null ? ` · ${d.rows} rows` : ""}
        </div>
        {d.anomalies?.map((a: any, i: number) => (
          <p key={i} className="text-red-300">⚠ [{a.severity}] {a.type}: {a.detail} {JSON.stringify(a.examples)}</p>
        ))}
        {d.issues?.map((s: string, i: number) => <p key={i} className="text-amber-300">• {s}</p>)}
      </div>
      {sel.relationships.map((r: any, i: number) => (
        <EdgeView key={i} title={`${r.from} → ${r.to}`} d={r} />
      ))}
    </>
  );
}

function Console({ runId }: { runId: string }) {
  const [log, setLog] = useState<{ q: string; a: string }[]>([]);
  const [q, setQ] = useState("");
  const ask = async (text: string) => {
    if (!text.trim()) return;
    setQ("");
    const { answer } = await api.ask(runId, text);
    setLog((l) => [...l, { q: text, a: answer }]);
  };
  const presets = ["Why do you think these datasets are related?", "What contradictions exist?", "Which entities need review?"];
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-auto">
        {log.map((m, i) => (
          <div key={i}>
            <div className="text-sky-300">› {m.q}</div>
            <pre className="whitespace-pre-wrap text-slate-200">{m.a}</pre>
          </div>
        ))}
      </div>
      <div className="my-2 flex flex-wrap gap-1">
        {presets.map((p) => (
          <button key={p} onClick={() => ask(p)} className="rounded bg-slate-800 px-2 py-1 text-[11px] hover:bg-slate-700">{p}</button>
        ))}
      </div>
      <input
        value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(q)}
        placeholder="Ask about a finding…" className="rounded border border-slate-700 bg-slate-900 px-2 py-1.5"
      />
    </div>
  );
}

function Steps({ run }: { run: any }) {
  return (
    <div className="space-y-2">
      {run.steps.map((s: any) => (
        <div key={s.step} className="rounded border border-slate-700 p-2">
          <div className="flex justify-between">
            <span className="font-medium">{s.step}. {s.tool}</span>
            <Tag c={s.planner === "llm" ? "bg-violet-800" : "bg-slate-700"}>{s.planner}</Tag>
          </div>
          <div className="text-slate-400">{s.reason}</div>
        </div>
      ))}
      <div className="pt-2 font-semibold">Open questions</div>
      {run.open_questions.map((q: string, i: number) => <p key={i} className="text-amber-300">• {q}</p>)}
    </div>
  );
}

export default function SidePanel({ run, sel }: { run: any; sel: any }) {
  const [tab, setTab] = useState("inspect");
  return (
    <aside className="flex h-full flex-col border-l border-slate-800 bg-slate-950 text-xs text-slate-100">
      <div className="flex border-b border-slate-800">
        {[["inspect", "Inspector"], ["console", "Console"], ["steps", "Investigation"]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex-1 py-2 ${tab === k ? "border-b-2 border-sky-400 text-sky-300" : "text-slate-400"}`}>{l}</button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-3">
        {!run ? <p className="text-slate-400">Upload files and run an investigation.</p>
          : tab === "inspect" ? <Inspector sel={sel} />
          : tab === "console" ? <Console runId={run.run_id} />
          : <Steps run={run} />}
      </div>
    </aside>
  );
}