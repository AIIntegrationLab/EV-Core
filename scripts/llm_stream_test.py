import requests
import json

url = "http://127.0.0.1:8088/v1/chat/completions"

payload = {
    "model": "local",
    "messages": [
        {"role": "system", "content": "Output only the numbers 1 to 5, separated by commas. No extra words."},
        {"role": "user", "content": "Go."}
    ],
    "temperature": 0.0,
    "stream": True
}

with requests.post(url, json=payload, stream=True, timeout=120) as r:
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if not line.startswith("data: "):
            continue

        data = line[6:]
        if data == "[DONE]":
            break

        chunk = json.loads(data)
        delta = chunk["choices"][0].get("delta", {})
        text = delta.get("content")

        if text:
            print(text, end="", flush=True)

print()
