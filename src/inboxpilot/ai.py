"""Summary: AI provider abstraction and implementations.

Importance: Centralizes LLM access for portability and auditability.
Alternatives: Call provider SDKs directly in each service.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from inboxpilot.config import AppConfig


class AiProvider(ABC):
    """Summary: Abstract interface for AI text generation.

    Importance: Allows switching between local and cloud LLMs without refactors.
    Alternatives: Use a single vendor SDK and accept lock-in risk.
    """

    @abstractmethod
    def generate_text(self, prompt: str, purpose: str) -> tuple[str, int]:
        """Summary: Generate a response for a prompt.

        Importance: Standardizes AI outputs for downstream services.
        Alternatives: Return provider-specific response objects directly.
        """


@dataclass(frozen=True)
class AiResult:
    """Summary: Captures AI output and metadata.

    Importance: Normalizes downstream handling of AI responses.
    Alternatives: Use dicts or provider response objects.
    """

    text: str
    latency_ms: int


class MockAiProvider(AiProvider):
    """Summary: Deterministic AI provider for local testing.

    Importance: Enables offline workflows and repeatable tests.
    Alternatives: Use a small local LLM for all development tasks.
    """

    def generate_text(self, prompt: str, purpose: str) -> tuple[str, int]:
        """Summary: Return a canned response echoing the prompt.

        Importance: Allows core flows without external dependencies.
        Alternatives: Use fixture-based responses loaded from files.
        """

        started = time.time()
        response = f"[mock:{purpose}] {prompt[:240]}"
        latency_ms = int((time.time() - started) * 1000)
        return response, latency_ms


class OllamaProvider(AiProvider):
    """Summary: AI provider that targets a local Ollama server.

    Importance: Supports privacy-sensitive workflows on local hardware.
    Alternatives: Use llama.cpp directly with a Python binding.
    """

    def __init__(self, base_url: str, model: str) -> None:
        """Summary: Initialize the Ollama provider.

        Importance: Stores connection details for repeated requests.
        Alternatives: Lazily resolve URLs per request.
        """

        self._base_url = base_url.rstrip("/")
        self._model = model

    def generate_text(self, prompt: str, purpose: str) -> tuple[str, int]:
        """Summary: Generate text using the Ollama HTTP API.

        Importance: Enables local inference for summaries and drafts.
        Alternatives: Use Ollama's CLI and parse its output.
        """

        payload = json.dumps({"model": self._model, "prompt": prompt, "stream": False})
        request = urllib.request.Request(
            url=f"{self._base_url}/api/generate",
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        latency_ms = int((time.time() - started) * 1000)
        return raw.get("response", ""), latency_ms


class OpenAiProvider(AiProvider):
    """Summary: AI provider using OpenAI's chat completion API.

    Importance: Enables higher-quality drafts and summaries when configured.
    Alternatives: Use other cloud providers or a local model.
    """

    def __init__(self, api_key: str, model: str) -> None:
        """Summary: Initialize the OpenAI provider.

        Importance: Stores credentials for future requests.
        Alternatives: Pass the API key per request from a caller.
        """

        self._api_key = api_key
        self._model = model

    def generate_text(self, prompt: str, purpose: str) -> tuple[str, int]:
        """Summary: Generate text using OpenAI chat completions.

        Importance: Enables cloud-grade reasoning for key workflows.
        Alternatives: Use the responses API or a different provider.
        """

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": f"You are InboxPilot. Task: {purpose}."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            url="https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
        latency_ms = int((time.time() - started) * 1000)
        content = raw["choices"][0]["message"]["content"]
        return content, latency_ms


@dataclass(frozen=True)
class AiProviderFactory:
    """Summary: Factory for selecting AI providers from configuration.

    Importance: Keeps provider selection logic centralized.
    Alternatives: Wire providers manually at the application entrypoint.
    """

    config: AppConfig

    def build(self) -> AiProvider:
        """Summary: Construct the configured AI provider.

        Importance: Ensures consistent provider selection across services.
        Alternatives: Use dependency injection frameworks.
        """

        if self.config.ai_provider == "ollama":
            return OllamaProvider(self.config.ollama_url, self.config.ollama_model)
        if self.config.ai_provider == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for openai provider")
            return OpenAiProvider(self.config.openai_api_key, self.config.openai_model)
        return MockAiProvider()


def estimate_tokens(text: str) -> int:
    """Summary: Estimate tokens from text length.

    Importance: Provides a rough metric for AI usage auditing.
    Alternatives: Use provider token counters or tiktoken.
    """

    return max(1, len(text) // 4)


def ai_request_payload(prompt: str, purpose: str) -> dict[str, Any]:
    """Summary: Build a normalized AI request payload.

    Importance: Aligns audit logging across providers.
    Alternatives: Log provider-specific request bodies directly.
    """

    return {"prompt": prompt, "purpose": purpose}
