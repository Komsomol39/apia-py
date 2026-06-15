"""Tests for apia Python SDK."""
import pytest
from unittest.mock import patch, MagicMock
from apia import Registry, Manifest, Capability, Service, Auth
from apia.exceptions import ManifestNotFoundError, RegistryError

# ── Fixtures ────────────────────────────────────────────────────────────────

SAMPLE_MANIFEST = {
    "apia": "1.0",
    "service": {
        "id": "telegram-bot",
        "name": "Telegram Bot API",
        "description_for_ai": "Send messages via Telegram. 950M users.",
        "category": "social",
        "geo": ["GLOBAL"],
        "language": "en",
        "url": "https://telegram.org",
        "api_base": "https://api.telegram.org/bot{token}",
        "docs": "https://core.telegram.org/bots/api",
    },
    "auth": {"type": "apikey", "anonymous_access": False, "cost": "Free"},
    "capabilities": [
        {
            "id": "send_message",
            "description_for_ai": "Send a text message to a user or group.",
            "intent": ["send telegram message", "telegram notify", "telegram bot send"],
            "endpoint": "POST https://api.telegram.org/bot{token}/sendMessage",
            "input": {
                "chat_id": {"type": "string", "required": True, "description": "Telegram chat ID"},
                "text": {"type": "string", "required": True, "description": "Message text"},
                "parse_mode": {"type": "string", "required": False, "description": "HTML or Markdown"},
            },
            "output": {"type": "message", "fields": ["message_id", "chat.id", "text"]},
            "realtime": True,
            "requires_auth": True,
        }
    ],
    "agent_hints": {"bot_father": "Get token from @BotFather on Telegram"},
    "meta": {"apia_version": "1.0", "last_verified": "2026-06-14"},
}

SAMPLE_REGISTRY = {
    "_meta": {"total": 1, "generated": "2026-06-14"},
    "manifests": [
        {
            "id": "telegram-bot",
            "name": "Telegram Bot API",
            "description_for_ai": "Send messages via Telegram. 950M users.",
            "category": "social",
            "geo": ["GLOBAL"],
            "language": "en",
            "auth_type": "apikey",
            "anonymous_access": False,
            "cost": "Free",
            "capabilities": [
                {
                    "id": "send_message",
                    "description_for_ai": "Send a text message.",
                    "intent": ["send telegram message", "telegram notify"],
                    "endpoint": "POST https://api.telegram.org/bot{token}/sendMessage",
                    "realtime": True,
                    "requires_auth": True,
                }
            ],
            "manifest_url": "https://raw.githubusercontent.com/Komsomol39/apia-standard/main/manifests/telegram-bot/apia.json",
        }
    ],
}


# ── Manifest tests ───────────────────────────────────────────────────────────

class TestManifest:
    def test_from_dict(self):
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        assert m.id == "telegram-bot"
        assert m.name == "Telegram Bot API"
        assert m.category == "social"
        assert m.is_free is False
        assert len(m.capabilities) == 1

    def test_find_capability_match(self):
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        cap = m.find_capability("send telegram message")
        assert cap is not None
        assert cap.id == "send_message"

    def test_find_capability_no_match(self):
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        cap = m.find_capability("book a hotel room")
        assert cap is None

    def test_to_openai_tools(self):
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        tools = m.to_openai_tools()
        assert len(tools) == 1
        tool = tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "send_message"
        assert "chat_id" in tool["function"]["parameters"]["properties"]
        assert "chat_id" in tool["function"]["parameters"]["required"]
        assert "parse_mode" not in tool["function"]["parameters"]["required"]

    def test_to_system_prompt(self):
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        prompt = m.to_system_prompt()
        assert "Telegram Bot API" in prompt
        assert "send_message" in prompt
        assert "POST" in prompt


# ── Capability tests ─────────────────────────────────────────────────────────

class TestCapability:
    def test_matches_intent(self):
        cap = Capability.from_dict(SAMPLE_MANIFEST["capabilities"][0])
        assert cap.matches_intent("send telegram message") is True
        assert cap.matches_intent("telegram notify") is True
        assert cap.matches_intent("book flight") is False


# ── Registry tests ───────────────────────────────────────────────────────────

class TestRegistry:
    def _registry_with_mock_index(self):
        registry = Registry()
        registry._index = SAMPLE_REGISTRY["manifests"]
        return registry

    def test_list_all(self):
        r = self._registry_with_mock_index()
        entries = r.list()
        assert len(entries) == 1

    def test_list_by_category(self):
        r = self._registry_with_mock_index()
        assert len(r.list(category="social")) == 1
        assert len(r.list(category="finance")) == 0

    def test_list_by_geo(self):
        r = self._registry_with_mock_index()
        assert len(r.list(geo="RU")) == 1   # GLOBAL includes RU
        assert len(r.list(geo="US")) == 1

    def test_list_free_only(self):
        r = self._registry_with_mock_index()
        assert len(r.list(free_only=True)) == 0  # telegram-bot is not anonymous

    def test_categories(self):
        r = self._registry_with_mock_index()
        cats = r.categories()
        assert cats == {"social": 1}

    def test_find_by_intent(self):
        r = self._registry_with_mock_index()
        with patch.object(r, "get", return_value=Manifest.from_dict(SAMPLE_MANIFEST)):
            results = r.find("send telegram message")
            assert len(results) == 1
            assert results[0].id == "telegram-bot"

    def test_find_no_results(self):
        r = self._registry_with_mock_index()
        results = r.find("xyzzy-nonexistent-quantum-blockchain")
        assert results == []

    def test_get_manifest(self):
        r = self._registry_with_mock_index()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MANIFEST
        with patch("httpx.get", return_value=mock_response):
            m = r.get("telegram-bot")
            assert m.id == "telegram-bot"

    def test_get_not_found(self):
        r = self._registry_with_mock_index()
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("httpx.get", return_value=mock_response):
            with pytest.raises(ManifestNotFoundError):
                r.get("nonexistent-api")

    def test_get_cached(self):
        r = self._registry_with_mock_index()
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        r._cache["telegram-bot"] = m
        with patch("httpx.get") as mock_get:
            result = r.get("telegram-bot")
            mock_get.assert_not_called()
        assert result is m

    def test_build_system_prompt(self):
        r = self._registry_with_mock_index()
        m = Manifest.from_dict(SAMPLE_MANIFEST)
        prompt = r.build_system_prompt([m])
        assert "You are an AI agent" in prompt
        assert "Telegram Bot API" in prompt
