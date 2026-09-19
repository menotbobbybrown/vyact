"""Serialize chat generation across desktop and extension clients."""
import asyncio


chat_request_lock = asyncio.Lock()
