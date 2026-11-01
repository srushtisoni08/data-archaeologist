from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import uploads, relationships, investigations, agent, reports

app = FastAPI(title="Data Archaeologist")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(uploads.router, prefix="/api")
app.include_router(relationships.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}