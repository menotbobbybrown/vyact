"""Token round trips must use the backed-up index without exposing the secret."""
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from routers.vyvow import router
from services import vyvow_credentials
from services.db import INTEGRATION_SETTINGS_INDEX


@pytest.mark.asyncio
async def test_save_status_replace_and_clear(monkeypatch):
    documents = {}

    async def write(**kwargs):
        assert kwargs['index'] == INTEGRATION_SETTINGS_INDEX
        documents[kwargs['id']] = kwargs['document']

    async def read(**kwargs):
        assert kwargs['index'] == INTEGRATION_SETTINGS_INDEX
        return {'_source': documents.get(kwargs['id'], {})}

    es = AsyncMock()
    es.index.side_effect = write
    es.get.side_effect = read
    monkeypatch.setattr(vyvow_credentials, 'get_es', lambda: es)
    app = FastAPI()
    app.include_router(router, prefix='/api')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/vyvow/token')).json() == {'has_token': False}
        for token in ('first-token', 'replacement-token', ''):
            response = await client.put('/api/vyvow/token', json={'token': f' {token} '})
            assert response.status_code == 200
            assert response.json() == {'has_token': bool(token)}
            assert await vyvow_credentials.read_token() == token
            assert (await client.get('/api/vyvow/token')).json() == {'has_token': bool(token)}
    assert es.close.await_count == 10


@pytest.mark.asyncio
async def test_storage_failure_closes_client(monkeypatch):
    es = AsyncMock()
    es.index.side_effect = RuntimeError('storage unavailable')
    monkeypatch.setattr(vyvow_credentials, 'get_es', lambda: es)
    with pytest.raises(RuntimeError):
        await vyvow_credentials.save_token('example')
    es.close.assert_awaited_once()
