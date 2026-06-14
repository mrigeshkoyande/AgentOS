import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "moonshotai/kimi-k2-instruct"


class KimiClient:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=90.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.nvidia_nim_key}",
            "Content-Type": "application/json",
        }

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        for attempt in range(3):
            try:
                resp = await self._client.post(
                    f"{BASE_URL}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                if resp.status_code in (429, 500, 502, 503) and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if attempt == 2:
                    raise
                logger.warning(f"KimiClient.generate attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError("KimiClient.generate: all retries exhausted")

    async def stream_generate(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": True,
        }

        async with self._client.stream(
            "POST",
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=90.0,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


kimi = KimiClient()
