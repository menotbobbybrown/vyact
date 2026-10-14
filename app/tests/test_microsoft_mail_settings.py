from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from services.microsoft_workspace import auth, mail_settings


@pytest.mark.asyncio
async def test_same_email_in_different_slots_resolves_same_preferences():
    with patch.object(auth, 'account', AsyncMock(side_effect=[({}, {'id': 'old'}), ({}, {'id': 'new'})])), \
            patch.object(auth, 'read_token', AsyncMock(side_effect=[{'email': ' Alice@Example.com '}, {'email': 'alice@example.com'}])), \
            patch.object(auth, 'migrate_legacy_settings', AsyncMock()):
        assert await auth.mail_settings_document_id('old', 'signature') == await auth.mail_settings_document_id('new', 'signature')
    assert mail_settings.document_id('signature', 'alice@example.com') != mail_settings.document_id('signature', 'bob@example.com')


@pytest.mark.asyncio
async def test_missing_identity_does_not_use_slot_preferences():
    with patch.object(auth, 'account', AsyncMock(return_value=({}, {'id': 'slot'}))), \
            patch.object(auth, 'read_token', AsyncMock(return_value={})), \
            patch.object(auth, 'migrate_legacy_settings', AsyncMock()) as migrate:
        with pytest.raises(HTTPException) as error:
            await auth.mail_settings_document_id('slot', 'signature')
    assert error.value.status_code == 401
    migrate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('existing', [False, True])
async def test_migration_preserves_email_preferences_and_removes_slot_keys(existing):
    es = AsyncMock()
    es.exists.side_effect = [True, existing, True, existing]
    es.get.return_value = {'_source': {'key': 'legacy', 'value': {'saved': True}}}
    with patch.object(mail_settings, 'get_es', return_value=es):
        await mail_settings.migrate_legacy_settings('old', 'alice@example.com')
    assert es.index.await_count == (0 if existing else 2)
    assert es.delete.await_count == 2
    if not existing:
        keys = [call.kwargs['id'] for call in es.index.await_args_list]
        assert keys == [mail_settings.document_id(kind, 'alice@example.com') for kind in mail_settings.SETTING_PREFIXES]
        assert all(call.kwargs['document']['value'] == {'saved': True} for call in es.index.await_args_list)
