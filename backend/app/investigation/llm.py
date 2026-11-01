import json
import os
import re
import httpx


def enabled() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def chat(system: str, user: str, max_tokens: int = 700) -> str | None:
    if not enabled():
        return None
    base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
            json={"model": os.getenv("LLM_MODEL", "gpt-4o-mini"), "temperature": 0,
                  "max_tokens": max_tokens,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]},
            timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def chat_json(system: str, user: str) -> dict | None:
    txt = chat(system, user, 400)
    if not txt:
        return None
    try:
        return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception:
        return None