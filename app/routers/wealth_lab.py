"""Backup-compatible Wealth Lab input snapshots."""
from elasticsearch import NotFoundError
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from services.db import SETTINGS_INDEX, get_es

router = APIRouter()
DOCUMENT_ID = "wealth_lab"
INPUT_FIELDS = frozenset({
    "initialAmount", "annualContribution", "contributionYears", "annualWithdrawal",
    "withdrawalStartYear", "annualReturn", "inflationRate", "investmentYears",
    "profileName", "currentAge", "endAge", "withdrawalAge", "startYear", "birthYear",
    "monthlyIncome", "incomeStartAge", "comparisonReturn1", "comparisonReturn2",
})


class WealthLabSnapshot(BaseModel):
    inputs: dict[str, str] = Field(max_length=len(INPUT_FIELDS))
    profileNameOverridden: bool = False

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, value):
        if set(value) - INPUT_FIELDS or any(len(text) > 200 for text in value.values()):
            raise ValueError("Invalid Wealth Lab inputs")
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
