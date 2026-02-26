import requests
import json

url = "http://127.0.0.1:8088/v1/chat/completions"

SYSTEM = """
You MUST respond with valid JSON ONLY (no markdown, no extra text).

Schema:
{
  "intent": "greeting|question|command|unknown",
  "reply": "string",
  "should_speak": true|false,
  "should_listen": true|false,
  "interruptible": true|false,
  "actions": [
    {"type":"none|vector_anim|vector_move|set_mode", "value":"string"}
  ]
}

Rules:
- If user greets: intent=greeting, should_speak=true, should_listen=true
- If user asks a question: intent=question, should_speak=true, should_listen=true
- If uncertain: intent=unknown, should_speak=true, should_listen=true, actions=[{"type":"none","value":""}]
- actions must ALWAYS be a list
- Keep reply short (max 1 sentence)
- Actions MUST ALWAYS contain at least one object; if no action, use [{"type":"none","value":""}]
- Interruptible should be true for normal speech replies
"""

payload = {
    "model": "local",
    "messages": [
        {"role": "system", "content": SYSTEM.strip()},
        {"role": "user", "content": "Hey EV, are you awake?"}
    ],
    "temperature": 0.0
}

r = requests.post(url, json=payload, timeout=60)
r.raise_for_status()

text = r.json()["choices"][0]["message"]["content"]

print("Raw model output:")
print(text)

print("\nParsed JSON:")
obj = json.loads(text)

# Basic validation (cheap but effective)
required = ["intent","reply","should_speak","should_listen","interruptible","actions"]
missing = [k for k in required if k not in obj]
if missing:
    raise SystemExit(f"Missing keys: {missing}")

if not isinstance(obj["actions"], list):
    raise SystemExit("actions is not a list")

print(obj)
