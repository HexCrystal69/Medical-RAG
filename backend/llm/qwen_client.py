"""
Qwen Ollama Client
-------------------
Connects to a local Ollama instance running Qwen3 and provides
streaming generation with conversation history support.
"""

from __future__ import annotations

import json
import io
import sys
from typing import Generator, List, Optional
import requests

# Reconfigure stdout to UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_FALLBACK_MODEL,
    OLLAMA_PRIMARY_MODEL,
    OLLAMA_SYSTEM_PROMPT,
    OLLAMA_TIMEOUT,
    CONVERSATION_HISTORY_LIMIT,
)


class OllamaConnectionError(Exception):
    """Raised when Ollama is not reachable."""


class OllamaModelNotFoundError(Exception):
    """Raised when neither the primary nor fallback model is available."""


class QwenOllamaClient:
    """Ollama-backed Qwen3 client with streaming and conversation history."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        primary_model: str = OLLAMA_PRIMARY_MODEL,
        fallback_model: str = OLLAMA_FALLBACK_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
        system_prompt: str = OLLAMA_SYSTEM_PROMPT,
        history_limit: int = CONVERSATION_HISTORY_LIMIT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.system_prompt = system_prompt
        self.history_limit = history_limit
        self.conversation_history: List[dict] = []

        # Verify Ollama is running
        self._check_ollama_running()

        # Resolve model
        self.model = self._resolve_model(primary_model, fallback_model)
        print(f"[INFO] Ollama model selected: {self.model}")

    def _check_ollama_running(self) -> None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except requests.ConnectionError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Is `ollama serve` running?"
            )
        except requests.RequestException as exc:
            raise OllamaConnectionError(
                f"Ollama health-check failed: {exc}"
            )

    def _get_available_models(self) -> set[str]:
        resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {m["name"] for m in data.get("models", [])}

    def _resolve_model(self, primary: str, fallback: str) -> str:
        try:
            available = self._get_available_models()
        except Exception as exc:
            print(f"[WARNING] Could not retrieve models list: {exc}. Defaulting to primary.")
            return primary

        # Exact match or prefix match
        if primary in available or f"{primary}:latest" in available:
            return primary
        
        # Try finding a partial match for primary
        for av in available:
            if av.startswith(primary):
                return av

        print(f"[WARNING] Primary model '{primary}' not found in Ollama.")
        if fallback in available or f"{fallback}:latest" in available:
            print(f"[INFO] Falling back to '{fallback}'.")
            return fallback

        # Try finding a partial match for fallback
        for av in available:
            if av.startswith(fallback):
                return av

        # If we have models pulled but neither primary nor fallback matches, pick the first available one as fallback!
        if available:
            picked = sorted(list(available))[0]
            print(f"[WARNING] Neither model found. Autoselected available model: {picked}")
            return picked

        raise OllamaModelNotFoundError(
            f"Neither '{primary}' nor '{fallback}' is available in Ollama.\n"
            f"Available models: {sorted(available) or '(none)'}\n"
            f"Pull a model first:  ollama pull {fallback}"
        )

    def clear_history(self) -> None:
        self.conversation_history.clear()

    def _trim_history(self) -> None:
        max_msgs = self.history_limit * 2
        if len(self.conversation_history) > max_msgs:
            self.conversation_history = self.conversation_history[-max_msgs:]

    def _build_messages(self, user_content: str, system_prompt: Optional[str] = None) -> List[dict]:
        sys_prompt = system_prompt if system_prompt is not None else self.system_prompt
        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_content})
        return messages

    def generate(
        self,
        user_content: str,
        stream: bool = True,
        system_prompt: Optional[str] = None,
    ) -> str:
        messages = self._build_messages(user_content, system_prompt=system_prompt)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1024,
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.ConnectionError:
            raise OllamaConnectionError("Lost connection to Ollama during generation.")
        except requests.RequestException as exc:
            raise OllamaConnectionError(f"Ollama request failed: {exc}")

        if stream:
            full_response = self._consume_stream(resp)
        else:
            data = resp.json()
            full_response = data.get("message", {}).get("content", "")

        # Record in history (only standard prompt turns)
        self.conversation_history.append({"role": "user", "content": user_content})
        self.conversation_history.append({"role": "assistant", "content": full_response})
        self._trim_history()

        return full_response

    def _consume_stream(self, resp: requests.Response) -> str:
        chunks: list[str] = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            token = data.get("message", {}).get("content", "")
            if token:
                chunks.append(token)

            if data.get("done", False):
                break

        return "".join(chunks)
