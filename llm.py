# llm.py
import hashlib, json, os, time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CACHE = Path("cache"); CACHE.mkdir(exist_ok=True)
client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ["LLM_MODEL"]


def complete(system: str, user: str, temperature: float = 0.2) -> str:
    key = hashlib.sha256(f"{MODEL}|{temperature}|{system}|{user}".encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["text"]
    last_error = None
    for attempt in range(5):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                temperature=temperature,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
            )
            text = r.choices[0].message.content.strip()
            f.write_text(json.dumps({"model": MODEL, "text": text}), encoding="utf-8")
            return text
        except Exception as e:
            last_error = e
            time.sleep(2 ** attempt)   # backoff for rate limits
    raise RuntimeError(f"LLM call failed: {last_error}")