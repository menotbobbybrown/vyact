from unittest.mock import AsyncMock, MagicMock

import pytest

from services.google_workspace import calendar
from services.google_workspace.calendar import _event_timezone


def test_explicit_timezone_wins():
    service = MagicMock()
    assert _event_timezone(service, "primary", "Europe/Paris", {"start": {"timeZone": "Asia/Tokyo"}}) == "Europe/Paris"
    service.calendars.assert_not_called()


def test_existing_event_timezone_is_preserved():
    service = MagicMock()
    assert _event_timezone(service, "primary", "", {"start": {"timeZone": "America/New_York"}}) == "America/New_York"
    service.calendars.assert_not_called()


def test_calendar_timezone_used_when_unspecified():
    service = MagicMock()
    service.calendars.return_value.get.return_value.execute.return_value = {"timeZone": "Europe/Berlin"}
    assert _event_timezone(service, "work", "") == "Europe/Berlin"
    service.calendars.return_value.get.assert_called_once_with(calendarId="work")


def test_missing_timezone_does_not_silently_use_seoul():
    service = MagicMock()
    service.calendars.return_value.get.return_value.execute.return_value = {}
    with pytest.raises(ValueError):
        _event_timezone(service, "primary", "")


@pytest.mark.asyncio
@pytest.mark.parametrize('zone', ['America/New_York', 'Europe/Berlin', 'Asia/Tokyo'])
async def test_create_uses_calendar_zone_in_api_payload(monkeypatch, zone):
    service = MagicMock()
    service.calendars.return_value.get.return_value.execute.return_value = {'timeZone': zone}
    monkeypatch.setattr(calendar, '_build_service', AsyncMock(return_value=service))
    monkeypatch.setattr(calendar, '_format_event', lambda event: '')
    await calendar.create_calendar_event(summary='test', start='2026-11-02T09:00:00', end='2026-11-02T10:00:00')
    body = service.events.return_value.insert.call_args.kwargs['body']
    assert body['start'] == {'dateTime': '2026-11-02T09:00:00', 'timeZone': zone}
    assert body['end']['timeZone'] == zone


@pytest.mark.asyncio
async def test_update_preserves_existing_event_zone(monkeypatch):
    service = MagicMock()
    service.events.return_value.get.return_value.execute.return_value = {
        'start': {'dateTime': '2026-11-02T09:00:00', 'timeZone': 'America/New_York'},
        'end': {'dateTime': '2026-11-02T10:00:00', 'timeZone': 'America/New_York'},
    }
    monkeypatch.setattr(calendar, '_build_service', AsyncMock(return_value=service))
    monkeypatch.setattr(calendar, '_format_event', lambda event: '')
    await calendar.update_calendar_event(event_id='test', start='2026-11-03T09:00:00')
    body = service.events.return_value.update.call_args.kwargs['body']
    assert body['start']['timeZone'] == 'America/New_York'
    assert body['end']['dateTime'] == '2026-11-02T10:00:00'
    service.calendars.assert_not_called()


@pytest.mark.asyncio
async def test_all_day_event_remains_date_only(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(calendar, '_build_service', AsyncMock(return_value=service))
    monkeypatch.setattr(calendar, '_format_event', lambda event: '')
    await calendar.create_calendar_event(summary='test', start='2026-11-02', end='2026-11-03')
    body = service.events.return_value.insert.call_args.kwargs['body']
    assert body['start'] == {'date': '2026-11-02'}
    assert body['end'] == {'date': '2026-11-03'}
    service.calendars.assert_not_called()
