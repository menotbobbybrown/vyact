from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from elasticsearch import NotFoundError
from pydantic import ValidationError

from routers.wealth_lab import (
    DOCUMENT_ID, WealthLabSnapshot, delete_wealth_lab, get_wealth_lab, save_wealth_lab,
    SavedPlan, PLAN_PREFIX, create_plan, put_plan, list_plans, remove_plan,
)
from services.db import SETTINGS_INDEX


@pytest.mark.asyncio
async def test_snapshot_round_trip_in_backed_up_settings_index():
    body = WealthLabSnapshot(inputs={"monthlyIncome": "100", "incomeStartAge": "65"}, profileNameOverridden=True)
    es = AsyncMock()
    es.get.return_value = {"_source": {"value": body.model_dump()}}
    with patch("routers.wealth_lab.get_es", return_value=es):
        await save_wealth_lab(body)
        assert await get_wealth_lab() == {"snapshot": body.model_dump()}
    es.index.assert_awaited_once_with(index=SETTINGS_INDEX, id=DOCUMENT_ID,
                                     document={"key": DOCUMENT_ID, "value": body.model_dump()}, refresh="wait_for")
    assert es.close.await_count == 2


@pytest.mark.asyncio
async def test_missing_snapshot_and_reset_are_safe():
    es = AsyncMock()
    error = NotFoundError("missing", meta=None, body=None)
    es.get.side_effect = error
    es.delete.side_effect = error
    with patch("routers.wealth_lab.get_es", return_value=es):
        assert await get_wealth_lab() == {"snapshot": None}
        assert await delete_wealth_lab() == {"ok": True}
    assert es.close.await_count == 2


def test_rejects_unknown_or_oversized_input_fields():
    for inputs in ({"unknown": "1"}, {"profileName": "x" * 201}):
        with pytest.raises(ValidationError):
            WealthLabSnapshot(inputs=inputs)


@pytest.mark.asyncio
async def test_named_plans_use_separate_backup_documents_and_support_overwrite():

    es = AsyncMock()
    body = SavedPlan(name="  Retirement  ", inputs={"annualReturn": "10"})
    with patch("routers.wealth_lab.get_es", return_value=es):
        created = (await create_plan(body))["plan"]
        plan_id = UUID(created["id"])
        assert created["name"] == "Retirement"
        updated = (await put_plan(plan_id, SavedPlan(name="Updated", inputs={"annualReturn": "8"})))["plan"]
        assert updated["id"] == created["id"]
        assert updated["inputs"]["annualReturn"] == "8"
        es.search.return_value = {"hits": {"hits": [{"_id": PLAN_PREFIX + str(plan_id), "_source": {"value": updated}}]}}
        assert (await list_plans())["plans"] == [updated]
        await remove_plan(plan_id)
    assert es.index.await_args.kwargs["id"] == PLAN_PREFIX + str(plan_id)
    assert es.index.await_args.kwargs["index"] == SETTINGS_INDEX
    es.delete.assert_awaited_once_with(index=SETTINGS_INDEX, id=PLAN_PREFIX + str(plan_id), refresh="wait_for")


def test_named_plan_requires_a_nonblank_bounded_name():
    for name in ("   ", "x" * 81):
        with pytest.raises(ValidationError):
            SavedPlan(name=name, inputs={})


def test_multiple_income_sources_round_trip_and_bounds():
    sources = [{"id": "pension", "name": "Pension", "monthlyAmount": "100", "startAge": "65", "endAge": ""},
               {"id": "private", "name": "Private", "monthlyAmount": "200", "startAge": "60", "endAge": "80"}]
    assert WealthLabSnapshot(inputs={"incomeSources": sources}).model_dump()["inputs"]["incomeSources"] == sources
    assert SavedPlan(name="Plan", inputs={"incomeSources": sources}).model_dump()["inputs"]["incomeSources"] == sources
    for inputs in ({"incomeSources": "invalid"}, {"incomeSources": sources * 11}, {"annualReturn": sources}):
        with pytest.raises(ValidationError):
            WealthLabSnapshot(inputs=inputs)
