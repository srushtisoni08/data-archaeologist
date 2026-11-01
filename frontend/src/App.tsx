import { useState } from "react";
import { api } from "./api";
import GraphView from "./GraphView";
import SidePanel from "./SidePanel";

const OBJECTIVE = "Investigate how these datasets are connected and find inconsistencies";

export default function App() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [run, setRun] = useState<any>(null);
  const [graph, setGraph] = useState<any>(null);
  const [level, setLevel] = useState("all");
  const [objective, setObjective] = useState(OBJECTIVE);
  const [sel, setSel] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const guard = (label: string, fn: () => Promise<void>) => async () => {
    setBusy(label); setErr("");
    try { await fn(); } catch (e: any) { setErr(String(e.message ?? e).slice(0, 300)); }
    setBusy("");
  };

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    await guard("Uploading…", async () => {
      await api.upload(files);
      setDatasets(await api.datasets());
    })();
  };
  const investigate = guard("Investigating…", async () => {
    const r = await api.investigate(objective);
    setRun(r); setSel(null);
    setGraph(await api.graph(r.run_id, level));
  });
  const changeLevel = async (l: string) => {
    setLevel(l);
    if (run) await guard("Loading…", async () => setGraph(await api.graph(run.run_id, l)))();
  };

  return (
    <div className="grid h-full grid-cols-[1fr_400px] grid-rows-[auto_1fr] text-slate-100">
      <header className="col-span-2 flex flex-wrap items-center gap-2 border-b border-slate-800 bg-slate-950 px-3 py-2 text-xs">
        <b className="mr-2 text-sm text-sky-300">Data Archaeologist</b>
        <label className="cursor-pointer rounded bg-slate-800 px-3 py-1.5 hover:bg-slate-700">
          Upload files
          <input type="file" multiple hidden onChange={(e) => upload(e.target.files)} />
        </label>
        <span className="text-slate-400">{datasets.length} datasets</span>
        <input value={objective} onChange={(e) => setObjective(e.target.value)}
          className="min-w-64 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1.5" />
        <button onClick={investigate} disabled={!!busy || !datasets.length}
          className="rounded bg-sky-600 px-3 py-1.5 font-medium disabled:opacity-40">Investigate</button>
        <select value={level} onChange={(e) => changeLevel(e.target.value)}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1.5">
          <option value="all">Columns + datasets</option>
          <option value="datasets">Datasets only</option>
        </select>
        {run && ["pdf", "md", "json"].map((f) => (
          <a key={f} href={`/api/reports/${run.run_id}?format=${f}`} target="_blank"
            className="rounded bg-slate-800 px-2 py-1.5 hover:bg-slate-700">{f.toUpperCase()}</a>
        ))}
        {busy && <span className="text-amber-300">{busy}</span>}
        {err && <span className="text-red-400">{err}</span>}
      </header>
      <main className="relative">
        {graph
          ? <GraphView key={run.run_id + level} graph={graph}
              onNode={async (id: string) => setSel({ type: "node", id, ...(await api.node(run.run_id, id)) })}
              onEdge={(e: any) => setSel({ type: "edge", source: e.source, target: e.target, data: e.data })} />
          : <div className="grid h-full place-items-center text-slate-500">Upload datasets, then click Investigate.</div>}
      </main>
      <SidePanel run={run} sel={sel} />
    </div>
  );
}