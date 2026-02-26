import requests
import json
import sys

url = "http://127.0.0.1:8088/v1/chat/completions"
text_in = " ".join(sys.argv[1:]).strip() or "Say hello."

payload = {
    "model": "local",
    "messages": [
    {"role": "system", "content": (
        "You are EV Core, a local offline assistant running on an NVIDIA Jetson AGX Orin. "
        "Never mention cloud, OpenAI, or being cloud-based. "
        "Keep replies to one short sentence."
    )},
    {"role": "user", "content": text_in}
],
    "temperature": 0.2,
    "stream": True
}

with requests.post(url, json=payload, stream=True, timeout=120) as r:
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break

        chunk = json.loads(data)
        delta = chunk["choices"][0].get("delta", {})
        out = delta.get("content")
        if out:
            print(out, end="", flush=True)

print()
