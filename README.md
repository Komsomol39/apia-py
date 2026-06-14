# apia-py

Python SDK for [APIA](https://github.com/Komsomol39/apia-standard) — the open standard for AI-native API manifests.

```bash
pip install apia
```

## Quickstart

```python
from apia import Registry

registry = Registry()

# Find APIs for a task
apis = registry.find("send a telegram message")
print(apis[0].name)        # → Telegram Bot API
print(apis[0].category)    # → social

# Get a specific manifest
manifest = registry.get("stripe")
print(manifest.service.description_for_ai)

# Convert to OpenAI tools
tools = manifest.to_openai_tools()

# Build a system prompt for an LLM
prompt = registry.build_system_prompt(apis)
```

## Core API

### `Registry`

```python
from apia import Registry

r = Registry()

# Search by intent (natural language)
r.find("track DHL package")              # → [Manifest, ...]
r.find("crypto price", category="finance") # → filtered

# Load a specific manifest
r.get("openai")                          # → Manifest

# List with filters
r.list(category="ai")                    # all AI APIs
r.list(geo="RU", free_only=True)        # free Russian APIs
r.list(language="ru")                    # Russian-language APIs

# Categories overview
r.categories()                           # → {"ai": 25, "finance": 17, ...}

# Build LLM system prompt from multiple manifests
prompt = r.build_system_prompt(apis)
```

### `Manifest`

```python
m = r.get("stripe")

m.id                     # "stripe"
m.name                   # "Stripe"
m.category               # "finance"
m.geo                    # ["GLOBAL"]
m.is_free                # False

# Find capability by task
cap = m.find_capability("charge a customer")
cap.id                   # "create_payment_intent"
cap.endpoint             # "POST https://api.stripe.com/v1/payment_intents"

# Export
m.to_openai_tools()      # list of OpenAI function definitions
m.to_system_prompt()     # formatted string for LLM system prompt
```

## Use with LLMs

### Anthropic Claude

```python
from apia import Registry
import anthropic

r = Registry()
apis = r.find("send telegram message")
system = r.build_system_prompt(apis)

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system=system,
    messages=[{"role": "user", "content": "Send 'Hello!' to chat 123456"}]
)
print(response.content[0].text)
```

### OpenAI function calling

```python
from apia import Registry
import openai

r = Registry()
manifest = r.get("openweathermap")
tools = manifest.to_openai_tools()

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=tools,
)
```

## Development

```bash
git clone https://github.com/Komsomol39/apia-py
cd apia-py
pip install -e ".[dev]"
pytest
```

## Related

- [apia-standard](https://github.com/Komsomol39/apia-standard) — manifest registry (257 APIs)
- [apia-js](https://github.com/Komsomol39/apia-js) — JavaScript/TypeScript SDK

## License

MIT
