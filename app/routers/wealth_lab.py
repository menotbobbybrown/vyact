"""Backup-compatible Wealth Lab input snapshots."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from elasticsearch import NotFoundError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from services.db import SETTINGS_INDEX, get_es

router = APIRouter()
DOCUMENT_ID = "wealth_lab"
INPUT_FIELDS = frozenset({
    "initialAmount", "annualContribution", "contributionYears", "annualWithdrawal",
    "withdrawalStartYear", "annualReturn", "inflationRate", "investmentYears",
    "profileName", "currentAge", "endAge", "withdrawalAge", "startYear", "birthYear",
    "monthlyIncome", "incomeStartAge", "comparisonReturn1", "comparisonReturn2", "incomeSources",
})


class IncomeSource(BaseModel):
    id: str = Field(max_length=80)
    name: str = Field(default="", max_length=80)
    monthlyAmount: str = Field(max_length=200)
    startAge: str = Field(max_length=200)
    endAge: str = Field(default="", max_length=200)


class WealthLabSnapshot(BaseModel):
    inputs: dict[str, str | list[IncomeSource]] = Field(max_length=len(INPUT_FIELDS))
    profileNameOverridden: bool = False

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, value):
        if set(value) - INPUT_FIELDS or any((len(item) > 200 if isinstance(item, str) else key != "incomeSources" or len(item) > 20) for key, item in value.items()):
            raise ValueError("Invalid Wealth Lab inputs")
        if "incomeSources" in value and not isinstance(value["incomeSources"], list):
            raise ValueError("Invalid income sources")
        return value


@router.get("/wealth-lab")
async def get_wealth_lab():
    es = get_es()
    try:
        result = await es.get(index=SETTINGS_INDEX, id=DOCUMENT_ID)
        return {"snapshot": result["_source"]["value"]}
    except NotFoundError:
        return {"snapshot": None}
    finally:
        await es.close()


@router.put("/wealth-lab")
async def save_wealth_lab(body: WealthLabSnapshot):
    es = get_es()
    try:
        await es.index(index=SETTINGS_INDEX, id=DOCUMENT_ID,
                       document={"key": DOCUMENT_ID, "value": body.model_dump()}, refresh="wait_for")
        return {"ok": True}
    finally:
        await es.close()


@router.delete("/wealth-lab")
async def delete_wealth_lab():
    es = get_es()
    try:
        try:
            await es.delete(index=SETTINGS_INDEX, id=DOCUMENT_ID, refresh="wait_for")
        except NotFoundError:
            pass
        return {"ok": True}
    finally:
        await es.close()


PLAN_PREFIX = "wealth_lab_plan:"


class SavedPlan(WealthLabSnapshot):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Plan name is required")
        return value.strip()


@router.get("/wealth-lab/plans")
async def list_plans():
    es = get_es()
    try:
        try:
            response = await es.search(index=SETTINGS_INDEX, query={"prefix": {"key": PLAN_PREFIX}}, size=1000)
        except NotFoundError:
            return {"plans": []}
        plans = [dict(hit["_source"]["value"], id=hit["_id"].removeprefix(PLAN_PREFIX)) for hit in response["hits"]["hits"]]
        return {"plans": sorted(plans, key=lambda plan: plan.get("updatedAt", ""), reverse=True)}
    finally:
        await es.close()


@router.post("/wealth-lab/plans")
async def create_plan(body: SavedPlan):
    return await put_plan(uuid4(), body)


@router.put("/wealth-lab/plans/{plan_id}")
async def put_plan(plan_id: UUID, body: SavedPlan):
    es = get_es()
    try:
        key = PLAN_PREFIX + str(plan_id)
        value = {**body.model_dump(), "updatedAt": datetime.now(timezone.utc).isoformat()}
        await es.index(index=SETTINGS_INDEX, id=key, document={"key": key, "value": value}, refresh="wait_for")
        return {"plan": {**value, "id": str(plan_id)}}
    finally:
        await es.close()


@router.delete("/wealth-lab/plans/{plan_id}")
async def remove_plan(plan_id: UUID):
    es = get_es()
    try:
        try:
            await es.delete(index=SETTINGS_INDEX, id=PLAN_PREFIX + str(plan_id), refresh="wait_for")
        except NotFoundError:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"ok": True}
    finally:
        await es.close()
