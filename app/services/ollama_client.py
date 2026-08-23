"""Thin Ollama HTTP client."""

import json
from typing import Any

import httpx

from app.config import settings


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.host = (host or settings.ollama_host).rstrip("/")
        self.model = model or settings.ollama_model
        self._client = client

    def chat(self, system: str, user: str, format_json: bool = True) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        if format_json:
            payload["format"] = "json"

        if self._client is not None:
            response = self._client.post(f"{self.host}/api/chat", json=payload)
        else:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(f"{self.host}/api/chat", json=payload)

        if response.status_code != 200:
            raise OllamaError(f"Ollama returned {response.status_code}: {response.text}")

        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content:
            raise OllamaError("Empty response from Ollama")
        return content

    def parse_json_response(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```" in content:
                parts = content.split("```")
                for part in parts:
                    cleaned = part.strip()
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:].strip()
                    if cleaned.startswith("{") or cleaned.startswith("["):
                        return json.loads(cleaned)
            raise OllamaError(f"Invalid JSON from Ollama: {content[:200]}")
