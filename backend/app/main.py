from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import uploads

app = FastAPI(title="Data Archaeologist")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(uploads.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}