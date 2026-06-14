"""
APIA Registry — loads and searches the manifest index.
"""

from __future__ import annotations
import json
from typing import Any
import httpx

from .manifest import Manifest
from .exceptions import RegistryError, ManifestNotFoundError

REGISTRY_URL = (
    "https://raw.githubusercontent.com/Komsomol39/apia-standard/main/registry.json"
)
MANIFEST_BASE_URL = (
    "https://raw.githubusercontent.com/Komsomol39/apia-standard/main/manifests"
)


class Registry:
    """
    APIA manifest registry.

    Usage::

        registry = Registry()
        apis = registry.find("send telegram message")
        manifest = registry.get("telegram-bot")
        tools = manifest.to_openai_tools()
        prompt = manifest.to_system_prompt()
    """

    def __init__(self, registry_url: str = REGISTRY_URL) -> None:
        self._url = registry_url
        self._index: list[dict[str, Any]] = []
        self._cache: dict[str, Manifest] = {}

    def _ensure_loaded(self) -> None:
        if self._index:
            return
        try:
            response = httpx.get(self._url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            self._index = data.get("manifests", [])
        except Exception as exc:
            raise RegistryError(f"Failed to load APIA registry: {exc}") from exc

    def list(
        self,
        category: str | None = None,
        geo: str | None = None,
        free_only: bool = False,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List registry entries with optional filters.

        :param category: One of the 26 APIA categories e.g. "ai", "finance", "maps".
        :param geo: ISO country code or "GLOBAL" e.g. "RU", "US", "GLOBAL".
        :param free_only: Only return APIs with anonymous_access=True.
        :param language: Primary language e.g. "ru", "en".
        :returns: List of lightweight registry entries (not full manifests).
        """
        self._ensure_loaded()
        results = self._index
        if category:
            results = [m for m in results if m.get("category") == category]
        if geo:
            results = [m for m in results if geo in m.get("geo", []) or "GLOBAL" in m.get("geo", [])]
        if free_only:
            results = [m for m in results if m.get("anonymous_access")]
        if language:
            results = [m for m in results if m.get("language") == language]
        return results

    def categories(self) -> dict[str, int]:
        """Return a dict of {category: count} for all manifests."""
        self._ensure_loaded()
        from collections import Counter
        return dict(Counter(m.get("category", "") for m in self._index))

    def find(
        self,
        task: str,
        category: str | None = None,
        geo: str | None = None,
        top_k: int = 3,
    ) -> list[Manifest]:
        """
        Find the most relevant APIs for a natural language task.

        Searches intent phrases in capabilities. Returns full Manifest objects.

        :param task: Natural language description e.g. "send a telegram message".
        :param category: Narrow to a specific category.
        :param geo: Narrow to a specific geography.
        :param top_k: Maximum number of results.
        :returns: List of Manifest objects sorted by relevance.
        """
        self._ensure_loaded()
        task_lower = task.lower()
        scored: list[tuple[int, dict[str, Any]]] = []

        candidates = self._index
        if category:
            candidates = [m for m in candidates if m.get("category") == category]
        if geo:
            candidates = [m for m in candidates if geo in m.get("geo", []) or "GLOBAL" in m.get("geo", [])]

        for entry in candidates:
            score = 0
            # Match description
            if any(w in entry.get("description_for_ai", "").lower() for w in task_lower.split()):
                score += 1
            # Match capability intents (stronger signal)
            for cap in entry.get("capabilities", []):
                for intent in cap.get("intent", []):
                    if task_lower in intent.lower() or intent.lower() in task_lower:
                        score += 3
                        break
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: -x[0])
        top_entries = [e for _, e in scored[:top_k]]

        # Load full manifests for top results
        return [self.get(e["id"]) for e in top_entries]

    def get(self, api_id: str) -> Manifest:
        """
        Load a full manifest by API id.

        :param api_id: The manifest id e.g. "openai", "telegram-bot", "stripe".
        :raises ManifestNotFoundError: If the manifest cannot be found.
        :returns: Full Manifest object.
        """
        if api_id in self._cache:
            return self._cache[api_id]
        url = f"{MANIFEST_BASE_URL}/{api_id}/apia.json"
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 404:
                raise ManifestNotFoundError(f"Manifest not found: {api_id!r}")
            response.raise_for_status()
            manifest = Manifest.from_dict(response.json())
            self._cache[api_id] = manifest
            return manifest
        except ManifestNotFoundError:
            raise
        except Exception as exc:
            raise RegistryError(f"Failed to load manifest {api_id!r}: {exc}") from exc

    def build_system_prompt(
        self,
        apis: list[Manifest],
        header: str = "You are an AI agent with access to the following APIs:",
    ) -> str:
        """
        Build a system prompt containing multiple API manifests.

        :param apis: List of Manifest objects to include.
        :param header: Opening sentence for the system prompt.
        :returns: Complete system prompt string ready to pass to an LLM.
        """
        parts = [header, ""]
        for manifest in apis:
            parts.append(manifest.to_system_prompt())
            parts.append("---")
        parts.append(
            "\nWhen the user asks something, identify which API and capability to use, "
            "explain your reasoning, and provide the exact API call."
        )
        return "\n".join(parts)
