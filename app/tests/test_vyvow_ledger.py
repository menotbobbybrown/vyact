from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from services import vyvow_ledger as ledger


@pytest.mark.asyncio
async def test_no_token_never_calls_upstream(monkeypatch):
    monkeypatch.setattr(ledger, 'read_token', AsyncMock(return_value=''))
    with pytest.raises(HTTPException) as error:
        await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 1)))
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_fixed_origin_and_header_auth(monkeypatch):
    monkeypatch.setattr(ledger, 'read_token', AsyncMock(return_value='private-test-token'))
    captured = []

    async def handle(request):
        captured.append(request)
        return httpx.Response(200, json={'code': 200, 'result': {'hledgers': [{'id': 3}], 'hledgerTags': ['food']}})

    client_class = httpx.AsyncClient
    monkeypatch.setattr(ledger.httpx, 'AsyncClient', lambda **kwargs: client_class(transport=httpx.MockTransport(handle), **kwargs))
    result = await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 1)))
    assert result == {'entries': [{'id': 3}], 'currencies': [], 'tags': ['food']}
    assert str(captured[0].url) == 'https://api.vyvow.com/api/member_place/searchHouseholdLedger'
    assert captured[0].headers['X-Api-Key'] == 'private-test-token'
    assert 'private-test-token' not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize('status,payload', [(401, {}), (200, {'code': 403}), (200, {'code': 901}), (500, {})])
async def test_upstream_errors_are_sanitized(monkeypatch, status, payload):
    monkeypatch.setattr(ledger, 'read_token', AsyncMock(return_value='secret'))
    client_class = httpx.AsyncClient
    monkeypatch.setattr(ledger.httpx, 'AsyncClient', lambda **kwargs: client_class(transport=httpx.MockTransport(lambda request: httpx.Response(status, json=payload)), **kwargs))
    with pytest.raises(HTTPException) as error:
        await ledger.request_api('POST', 'searchHouseholdLedger')
    assert error.value.status_code == (401 if status == 401 or payload.get('code') == 403 else 502)
    assert 'secret' not in error.value.detail


@pytest.mark.asyncio
async def test_foreign_entry_cannot_be_modified(monkeypatch):
    request = AsyncMock(return_value={'result': {'hledgers': []}})
    monkeypatch.setattr(ledger, 'request_api', request)
    entry = ledger.LedgerEntry(id=10, txType='EXPENSE', houseLedgerOptionId=1, currency='KRW', amount=12000, createdAt=date(2026, 10, 18))
    with pytest.raises(HTTPException) as error:
        await ledger.save_entry(entry)
    assert error.value.status_code == 404
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_edit_preserves_attachment_and_tag(monkeypatch):
    request = AsyncMock(side_effect=[{'result': {'hledgers': [{'id': 10}]}}, {'code': 200}])
    monkeypatch.setattr(ledger, 'request_api', request)
    entry = ledger.LedgerEntry(id=10, txType='EXPENSE', houseLedgerOptionId=1, currency='KRW', amount=12000, memberBoardFileId=77, tag='trip', createdAt=date(2026, 10, 18))
    await ledger.save_entry(entry)
    sent = request.call_args.kwargs['json']['houseLedger']
    assert sent['memberBoardFileId'] == 77
    assert sent['tag'] == 'trip'
    assert sent['createdAt'] == '2026-10-18'


@pytest.mark.asyncio
async def test_week_view_includes_full_boundary_weeks(monkeypatch):
    request = AsyncMock(return_value={'result': {}})
    monkeypatch.setattr(ledger, 'request_api', request)
    await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 1), period='weekly'))
    params = request.call_args.kwargs['json']
    assert params['customPeriod'] is True
    assert params['fromDate'] == '2026-09-28'
    assert params['toDate'] == '2026-11-01'


@pytest.mark.asyncio
async def test_custom_range_is_not_expanded_to_week_boundary(monkeypatch):
    request = AsyncMock(return_value={'result': {}})
    monkeypatch.setattr(ledger, 'request_api', request)
    await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 3), toDate=date(2026, 10, 9), period='weekly'))
    params = request.call_args.kwargs['json']
    assert params['fromDate'] == '2026-10-03'
    assert params['toDate'] == '2026-10-09'
    assert params['customPeriod'] is True


@pytest.mark.asyncio
async def test_tag_query_preserves_vyvow_weekly_request_dates(monkeypatch):
    request = AsyncMock(return_value={'result': {}})
    monkeypatch.setattr(ledger, 'request_api', request)
    await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 1), tag='trip', period='weekly'))
    params = request.call_args.kwargs['json']
    assert params['tag'] == 'trip'
    assert params['customPeriod'] is True
    assert params['fromDate'] == '2026-09-28'
    assert params['toDate'] == '2026-11-01'


@pytest.mark.parametrize('end,tag', [('2026-09-01', ''), ('2028-01-01', '')])
def test_invalid_and_conflicting_ranges_rejected(end, tag):
    with pytest.raises(ValueError):
        ledger.LedgerQuery(fromDate=date(2026, 10, 1), toDate=end, tag=tag)


@pytest.mark.asyncio
async def test_tag_results_exclude_other_tags_and_untagged_entries(monkeypatch):
    request = AsyncMock(return_value={'result': {'hledgers': [
        {'id': 1, 'tag': 'trip'}, {'id': 2, 'tag': ''},
        {'id': 3, 'tag': 'work'}, {'id': 4, 'tag': 'trip'},
    ]}})
    monkeypatch.setattr(ledger, 'request_api', request)
    result = await ledger.search_ledger(ledger.LedgerQuery(fromDate=date(2026, 10, 1), tag='trip'))
    assert request.call_args.kwargs['json']['tag'] == 'trip'
    assert [entry['id'] for entry in result['entries']] == [1, 4]


@pytest.mark.asyncio
async def test_tag_request_matches_existing_vyvow_flow(monkeypatch):
    request = AsyncMock(return_value={'result': {}})
    monkeypatch.setattr(ledger, 'request_api', request)
    await ledger.search_ledger(ledger.LedgerQuery(fromDate='2026-10-01', period='weekly', init=False,
                                                tag='바트 마지막 소비', tempTargetCurrency='THB'))
    params = request.call_args.kwargs['json']
    assert params == {'fromDate': '2026-09-28', 'toDate': '2026-11-01', 'init': False,
                      'period': 'weekly', 'tag': '바트 마지막 소비', 'tempTargetCurrency': 'THB',
                      'customPeriod': True, 'requiredLedger': False}
