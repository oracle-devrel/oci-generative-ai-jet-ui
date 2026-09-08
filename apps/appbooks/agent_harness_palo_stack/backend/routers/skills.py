"""Layer 6 — Skills & Automations: the tool registry, the skill registry (with SHA +
source URL), workflow→skill promotion, and scheduled automations."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from backend.core import db, registries, scratch
from backend.schemas import AutomationReq, PromoteReq, SkillSourceReq, ToolQuery

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/tools")
async def tools(req: ToolQuery) -> dict:
    rows = await run_in_threadpool(registries.retrieve_tools, req.query, 5)
    return {
        "tools": [
            {
                "name": r["NAME"],
                "description": r["DESCRIPTION"],
                "schema": r["TOOL_SCHEMA"],
                "dist": r.get("DIST"),
            }
            for r in rows
        ]
    }


@router.post("/manifest")
async def manifest(req: ToolQuery) -> dict:
    rows = await run_in_threadpool(registries.retrieve_skills, req.query, 6)
    return {
        "manifest": "\n".join(f"- {r['NAME']}: {r['DESCRIPTION']}" for r in rows),
        "skills": [
            {
                "name": r["NAME"],
                "description": r["DESCRIPTION"],
                "sha": (r.get("SHA") or "")[:12],
                "source": r.get("SOURCE_URL"),
            }
            for r in rows
        ],
    }


@router.get("/load")
async def load(name: str) -> dict:
    return await run_in_threadpool(registries.load_skill, name)


@router.get("/list")
async def list_skills() -> dict:
    rows = await run_in_threadpool(
        db.q,
        "SELECT name, description, SUBSTR(sha,1,12) sha, source_url, updated_at FROM agent_skills ORDER BY name",
    )
    return {"skills": rows}


@router.post("/register_source")
async def register_source(req: SkillSourceReq) -> dict:
    name = req.name.strip().replace(" ", "_").lower()
    md = f"---\nname: {name}\ndescription: {req.description}\n---\n\n{req.body}"
    path = f"/skills/{name}.md"
    await run_in_threadpool(scratch.write, path, md)
    res = await run_in_threadpool(registries.register_skill_from_source, scratch._abs(path))
    return res


@router.post("/refresh")
async def refresh() -> dict:
    return {"updated": await run_in_threadpool(registries.refresh_skills_from_source)}


@router.get("/automations")
async def automations() -> dict:
    return {"automations": await run_in_threadpool(registries.list_automations)}


@router.post("/create_automation")
async def create_automation(req: AutomationReq) -> dict:
    return await run_in_threadpool(
        registries.create_automation, req.name, req.select_sql, req.cadence_hours, req.description
    )


@router.get("/workflows")
async def workflows() -> dict:
    rows = await run_in_threadpool(
        db.q,
        "SELECT RAWTOHEX(id) id, intent, occurrences, promoted FROM agent_workflow ORDER BY last_seen DESC FETCH FIRST 10 ROWS ONLY",
    )
    return {"workflows": rows}


@router.post("/promote")
async def promote(req: PromoteReq) -> dict:
    return await run_in_threadpool(registries.promote_workflow_to_skill, req.workflow_id)
