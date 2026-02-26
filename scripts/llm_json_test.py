import requests
import json

url = "http://127.0.0.1:8088/v1/chat/completions"

payload = {
    "model": "local",
    "messages": [
        {
            "role": "system",
            "content": (
                "You MUST respond with valid JSON only. "
                "Format: {\"intent\": string, \"reply\": string}"
            )
        },
        {
            "role": "user",
            "content": "Say hello."
        }
    ],
    "temperature": 0.0
}

r = requests.post(url, json=payload, timeout=60)
r.raise_for_status()

data = r.json()
text = data["choices"][0]["message"]["content"]

print("Raw model output:")
print(text)

print("\nParsed JSON:")
parsed = json.loads(text)
print(parsed)
