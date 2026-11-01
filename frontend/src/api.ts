const j = async (r: Response) => {
  if (!r.ok) throw new Error(await r.text());
  return r.json();
};
const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j);

export const api = {
  upload: (files: FileList) => {
    const f = new FormData();
    Array.from(files).forEach((x) => f.append("files", x));
    return fetch("/api/uploads", { method: "POST", body: f }).then(j);
  },
  datasets: () => fetch("/api/datasets").then(j),
  investigate: (objective: string) => post("/api/investigations", { objective }),
  graph: (id: string, level: string) => fetch(`/api/graph/${id}?level=${level}`).then(j),
  node: (id: string, n: string) => fetch(`/api/graph/${id}/node/${encodeURIComponent(n)}`).then(j),
  ask: (id: string, question: string) => post(`/api/investigations/${id}/ask`, { question }),
};