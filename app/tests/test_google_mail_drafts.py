import base64
import unittest
from email import message_from_bytes
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, UploadFile
from routers import google_workspace_browser as workspace


class GoogleMailDraftTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = MagicMock()
        self.drafts = self.service.users().drafts()
        self.message = {"id": "message-old", "threadId": "thread", "labelIds": ["DRAFT"], "payload": {"headers": [
            {"name": "From", "value": "me@example.com"},
            {"name": "In-Reply-To", "value": "<original@example.com>"},
            {"name": "References", "value": "<root@example.com> <original@example.com>"},
        ]}}
        self.drafts.get.return_value.execute.return_value = {"id": "draft", "message": self.message}
        self.drafts.update.return_value.execute.return_value = {"id": "draft", "message": {"id": "message-new", "threadId": "thread"}}
        self.drafts.send.return_value.execute.return_value = {"id": "sent", "threadId": "thread"}
        for name, replacement in [("_require_connection", AsyncMock()), ("_build_service", AsyncMock(return_value=self.service))]:
            patcher = patch.object(workspace, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_save_replaces_same_draft_preserving_reply_chain_and_attachment(self):
        upload = UploadFile(filename="notes.txt", file=BytesIO(b"attachment content"))
        result = await workspace.send_mail(to="to@example.com", subject="Re: hello", body="edited", attachments=[upload], draft_id="draft", draft_message_id="message-old", save_draft=True)
        self.assertEqual(result["id"], "message-new")
        call = self.drafts.update.call_args.kwargs
        self.assertEqual(call["id"], "draft")
        self.assertEqual(call["body"]["message"]["threadId"], "thread")
        mime = message_from_bytes(base64.urlsafe_b64decode(call["body"]["message"]["raw"]))
        self.assertEqual(mime["In-Reply-To"], "<original@example.com>")
        self.assertEqual(mime["References"], "<root@example.com> <original@example.com>")
        self.assertEqual(mime["From"], "me@example.com")
        self.assertTrue(any(part.get_payload(decode=True) == b"attachment content" for part in mime.walk()))
        self.drafts.send.assert_not_called()
        self.service.users().messages().send.assert_not_called()

    async def test_send_uses_existing_draft_and_updated_body(self):
        result = await workspace.send_mail(to="to@example.com", body="edited", draft_id="draft", draft_message_id="message-old")
        self.assertEqual(result["id"], "sent")
        self.assertEqual(self.drafts.send.call_args.kwargs["body"]["id"], "draft")
        self.service.users().messages().send.assert_not_called()

    async def test_changed_draft_is_not_overwritten_or_deleted(self):
        with self.assertRaises(HTTPException) as error:
            await workspace.send_mail(draft_id="draft", draft_message_id="stale", save_draft=True)
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(HTTPException):
            await workspace.delete_mail_draft("draft", "stale")
        self.drafts.update.assert_not_called()
        self.drafts.delete.assert_not_called()

    async def test_discard_deletes_only_the_draft(self):
        await workspace.delete_mail_draft("draft", "message-old")
        self.drafts.delete.assert_called_once_with(userId="me", id="draft")
        self.service.users().threads().delete.assert_not_called()
        self.service.users().messages().trash.assert_not_called()

    async def test_lookup_checks_later_pages_and_returns_current_draft(self):
        self.drafts.list.return_value.execute.side_effect = [{"drafts": [], "nextPageToken": "next"}, {"drafts": [{"id": "draft", "message": {"id": "message-old"}}]}]
        result = await workspace.get_mail_draft("message-old")
        self.assertEqual(result["draftId"], "draft")
        self.assertEqual(result["message"]["id"], "message-old")
        self.assertEqual(self.drafts.list.call_args.kwargs["pageToken"], "next")

    async def test_normal_send_is_unchanged(self):
        await workspace.send_mail(to="to@example.com", body="normal")
        self.service.users().messages().send.assert_called_once()
        self.drafts.send.assert_not_called()

    async def test_blank_draft_can_be_saved_without_sending(self):
        await workspace.send_mail(draft_id="draft", draft_message_id="message-old", save_draft=True)
        self.drafts.update.assert_called_once()
        self.drafts.send.assert_not_called()

    async def test_inline_image_and_html_survive_draft_save(self):
        image = UploadFile(filename="image.png", file=BytesIO(b"image bytes"))
        await workspace.send_mail(html_body='<p>edited<img src="cid:inline-image-1"></p>', inline_images=[image], draft_id="draft", draft_message_id="message-old", save_draft=True)
        raw = self.drafts.update.call_args.kwargs["body"]["message"]["raw"]
        mime = message_from_bytes(base64.urlsafe_b64decode(raw))
        parts = list(mime.walk())
        self.assertTrue(any(part.get("Content-ID") == "<inline-image-1>" and part.get_payload(decode=True) == b"image bytes" for part in parts))
        self.assertTrue(any(part.get_content_type() == "text/html" and b'cid:inline-image-1' in part.get_payload(decode=True) for part in parts))
