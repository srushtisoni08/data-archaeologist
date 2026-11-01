class EvidenceStore:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, tool: str, args: dict, result: dict, summary: str) -> dict:
        e = {"id": f"ev_{len(self.items) + 1:03d}", "tool": tool, "args": args,
             "summary": summary, "result": result}
        self.items.append(e)
        return e

    def get(self, eid: str) -> dict | None:
        return next((e for e in self.items if e["id"] == eid), None)