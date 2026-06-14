"""Data models for APIA manifests."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Auth:
    type: str
    anonymous_access: bool
    how_to_get: str = ""
    cost: str = ""
    header: str = ""
    param_name: str = ""
    param_location: str = ""
    token_url: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Auth":
        return cls(
            type=data.get("type", ""),
            anonymous_access=data.get("anonymous_access", False),
            how_to_get=data.get("how_to_get", ""),
            cost=data.get("cost", ""),
            header=data.get("header", ""),
            param_name=data.get("param_name", ""),
            param_location=data.get("param_location", ""),
            token_url=data.get("token_url", ""),
            note=data.get("note", ""),
        )


@dataclass
class Service:
    id: str
    name: str
    description_for_ai: str
    category: str
    geo: list[str]
    language: str = "en"
    url: str = ""
    api_base: str = ""
    docs: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Service":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description_for_ai=data.get("description_for_ai", ""),
            category=data.get("category", ""),
            geo=data.get("geo", []),
            language=data.get("language", "en"),
            url=data.get("url", ""),
            api_base=data.get("api_base", ""),
            docs=data.get("docs", ""),
        )


@dataclass
class Capability:
    id: str
    description_for_ai: str
    intent: list[str]
    endpoint: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    realtime: bool = False
    requires_auth: bool = True
    rate_limit: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capability":
        return cls(
            id=data.get("id", ""),
            description_for_ai=data.get("description_for_ai", ""),
            intent=data.get("intent", []),
            endpoint=data.get("endpoint", ""),
            input=data.get("input", {}),
            output=data.get("output", {}),
            realtime=data.get("realtime", False),
            requires_auth=data.get("requires_auth", True),
            rate_limit=data.get("rate_limit", ""),
        )

    def matches_intent(self, task: str) -> bool:
        """Return True if any intent phrase matches the task string."""
        task_lower = task.lower()
        return any(
            task_lower in phrase.lower() or phrase.lower() in task_lower
            for phrase in self.intent
        )

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert this capability to an OpenAI function/tool definition."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, spec in self.input.items():
            if not isinstance(spec, dict):
                continue
            properties[name] = {
                "type": spec.get("type", "string"),
                "description": spec.get("description", ""),
            }
            if spec.get("enum"):
                properties[name]["enum"] = spec["enum"]
            if spec.get("required"):
                required.append(name)
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description_for_ai,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class Manifest:
    service: Service
    auth: Auth
    capabilities: list[Capability]
    agent_hints: dict[str, str] = field(default_factory=dict)
    apia_version: str = "1.0"
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # Convenience aliases
    @property
    def id(self) -> str:
        return self.service.id

    @property
    def name(self) -> str:
        return self.service.name

    @property
    def category(self) -> str:
        return self.service.category

    @property
    def geo(self) -> list[str]:
        return self.service.geo

    @property
    def is_free(self) -> bool:
        return self.auth.anonymous_access

    def find_capability(self, task: str) -> Capability | None:
        """Return the first capability whose intent matches the task."""
        for cap in self.capabilities:
            if cap.matches_intent(task):
                return cap
        return None

    def to_system_prompt(self) -> str:
        """Format this manifest as a system prompt section for an LLM."""
        lines = [
            f"## {self.service.name}",
            f"{self.service.description_for_ai}",
            f"Auth: {self.auth.type} | Cost: {self.auth.cost}",
            f"Docs: {self.service.docs}",
            "",
            "### Capabilities",
        ]
        for cap in self.capabilities:
            lines.append(f"**[{cap.id}]** `{cap.endpoint}`")
            lines.append(f"When: {cap.description_for_ai}")
            lines.append(f"Intent: {', '.join(cap.intent[:5])}")
            lines.append("")
        if self.agent_hints:
            lines.append("### Hints")
            for k, v in self.agent_hints.items():
                lines.append(f"- **{k}**: {v}")
        return "\n".join(lines)

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Convert all capabilities to OpenAI tool definitions."""
        return [cap.to_openai_tool() for cap in self.capabilities]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        return cls(
            service=Service.from_dict(data.get("service", {})),
            auth=Auth.from_dict(data.get("auth", {})),
            capabilities=[Capability.from_dict(c) for c in data.get("capabilities", [])],
            agent_hints=data.get("agent_hints", {}),
            apia_version=data.get("apia", "1.0"),
            raw=data,
        )
