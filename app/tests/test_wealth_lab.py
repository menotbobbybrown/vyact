from unittest.mock import AsyncMock, patch

import pytest
from elasticsearch import NotFoundError
from pydantic import ValidationError

from routers.wealth_lab import (
    DOCUMENT_ID, WealthLabSnapshot, delete_wealth_lab, get_wealth_lab, save_wealth_lab,
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
