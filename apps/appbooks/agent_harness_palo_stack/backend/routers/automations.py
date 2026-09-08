"""Automation control: list with live schedule state, run-now, start/stop, results.

Backs the Mission Control stage — the same DBMS_SCHEDULER jobs + materialized views
the agent itself builds via the create_automation tool, now drivable from the UI."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core import registries

router = APIRouter(prefix="/api/automations", tags=["automations"])


class NameReq(BaseModel):
    name: str


class ToggleReq(BaseModel):
    name: str
    enable: bool = True


class CreateReq(BaseModel):
    name: str
    select_sql: str
    cadence_hours: int = 24
    description: str = ""


@router.get("")
def list_automations():
    return {"automations": registries.automation_status()}


@router.post("/create")
def create(req: CreateReq):
    return registries.create_automation(
        req.name, req.select_sql, req.cadence_hours, req.description
    )


@router.post("/run")
def run(req: NameReq):
    return registries.run_automation_now(req.name)


@router.post("/toggle")
def toggle(req: ToggleReq):
    return registries.toggle_automation(req.name, req.enable)


@router.get("/results")
def results(name: str):
    return registries.automation_results(name)
