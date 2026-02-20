from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class UpstreamError(RuntimeError):
    pass


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("status") in {"success", "error"}:
        return payload.get("data") if payload.get("status") == "success" else payload
    return payload


class UpstreamClient:
    def __init__(self) -> None:
        self.base_url = settings.upstream_api_base.rstrip("/")
        self.timeout = settings.request_timeout_seconds

    async def highlight_content(
        self,
        content: str,
        difficulty: str,
        custom_terms: list[str] | None = None,
    ) -> tuple[str, list[dict]]:
        payload = {
            "content": content,
            "difficulty": difficulty,
            "custom_terms": custom_terms or [],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/highlight", json=payload)

        if response.status_code >= 400:
            return content, []

        data = _unwrap(response.json())
        if not isinstance(data, dict):
            return content, []
        return str(data.get("content", content)), data.get("highlighted_terms", []) or []

    async def explain_term(self, term: str, difficulty: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/tutor/explain/{term}",
                params={"difficulty": difficulty},
            )

        if response.status_code >= 400:
            raise UpstreamError(f"term explain failed: {response.status_code}")

        data = _unwrap(response.json())
        if not isinstance(data, dict):
            raise UpstreamError("unexpected term explain response")
        return data

    async def visualize(self, description: str, data_context: str) -> dict[str, Any]:
        payload = {"description": description, "data_context": data_context}
        async with httpx.AsyncClient(timeout=max(self.timeout, 60)) as client:
            response = await client.post(f"{self.base_url}/tutor/visualize", json=payload)

        if response.status_code >= 400:
            raise UpstreamError(f"visualize failed: {response.status_code}")

        data = _unwrap(response.json())
        if not isinstance(data, dict):
            raise UpstreamError("unexpected visualize response")
        return data


upstream_client = UpstreamClient()
