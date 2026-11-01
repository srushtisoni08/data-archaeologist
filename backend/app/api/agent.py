from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.investigation.orchestrator import run_investigation, load_run, answer

router = APIRouter(tags=["agent"])


class Objective(BaseModel):
    objective: str = "Investigate how these datasets are connected and identify suspicious inconsistencies."


class Question(BaseModel):
    question: str


@router.post("/investigations")
def start(body: Objective):
    return run_investigation(body.objective)


@router.get("/investigations/{run_id}")
def get_run(run_id: str):
    run = load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/investigations/{run_id}/ask")
def ask(run_id: str, body: Question):
    run = load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return {"answer": answer(run, body.question)}