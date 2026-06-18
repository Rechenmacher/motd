#!/usr/bin/env python3
"""
generator/today.py — AI-powered Message of the Day

Fetches today's top news headlines from free RSS feeds (no API key needed),
then asks an AI to write a funny, warm, or witty MOTD inspired by what's
actually happening in the world right now.

Supports multiple AI providers — use whichever you have access to:

  Provider       | Env var           | Free?
  ───────────────┼───────────────────┼──────────────────────────────
  Anthropic      | ANTHROPIC_API_KEY | No (paid, best quality)
  Google Gemini  | GEMINI_API_KEY    | Yes — 1500 req/day free
  Groq           | GROQ_API_KEY      | Yes — very generous free tier
  Ollama         | OLLAMA_URL        | Yes — fully local, no key
  (none)         | —                 | Picks a random message instead

Provider is auto-detected from which env var is set. Override with:
  MOTD_AI_PROVIDER=gemini python3 generator/today.py

Usage:
  python3 generator/today.py               # generate and print
  python3 generator/today.py --force       # ignore cache, regenerate
  python3 generator/today.py --dry-run     # show headlines only, no AI call
  python3 generator/today.py --output PATH # write result to PATH instead of cache
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "cache.json"
CACHE_TTL  = 12 * 3600  # 12 hours
MESSAGES_FILE = Path(__file__).parent.parent / "messages.json"

RSS_FEEDS = [
    ("BBC World News",  "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Hacker News Top", "https://hnrss.org/frontpage?count=10"),
    ("Reuters World",   "https://feeds.reuters.com/reuters/worldNews"),
]

MAX_HEADLINES = 12

SYSTEM_PROMPT = """You write the Message of the Day for a developer community.
Your tone is warm, witty, and human — not corporate, not preachy.
You're allowed to be funny. You're allowed to be a little absurd.
You care about people, and you acknowledge that the world can be genuinely strange.

Your job: read today's headlines and write ONE message of the day.
The message should:
  - Be 1-3 sentences, max 200 characters
  - Be inspired by (but not directly quote) one or two real headlines
  - Make the reader feel something: a smile, a moment of recognition, a breath
  - Be suitable for all audiences
  - Not be doom-and-gloom, even when the news is hard

Return ONLY a JSON object with exactly these fields, nothing else:
{
  "text": "the message",
  "author": "a short witty attribution (not 'AI' — be creative: 'The Algorithm', 'Your Terminal', 'A Concerned Robot', etc.)",
  "tag": "one of: funny, motivation, kindness, wisdom, courage, tech"
}"""


# ── RSS parsing ────────────────────────────────────────────────────────────────

def fetch_headlines(max_total: int = MAX_HEADLINES) -> list[str]:
    headlines: list[str] = []
    for name, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "motd-generator/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                content = r.read()
            root = ET.fromstring(content)
            for item in root.iter("item"):
                title = item.findtext("title", "").strip()
                if title and len(title) > 10:
                    headlines.append(title)
                    if len(headlines) >= max_total:
                        return headlines
            for entry in root.iter("entry"):
                title = entry.findtext("{http://www.w3.org/2005/Atom}title", "").strip()
                if title and len(title) > 10:
                    headlines.append(title)
                    if len(headlines) >= max_total:
                        return headlines
        except Exception as e:
            print(f"  [warn] {name}: {e}", file=sys.stderr)
    return headlines


# ── cache ─────────────────────────────────────────────────────────────────────

def load_cache(cache_file: Path = CACHE_FILE) -> dict | None:
    try:
        data = json.loads(cache_file.read_text())
        if time.time() - data.get("generated_at", 0) < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def save_cache(entry: dict, cache_file: Path = CACHE_FILE) -> None:
    try:
        cache_file.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"  [warn] could not write cache: {e}", file=sys.stderr)


# ── provider detection ─────────────────────────────────────────────────────────

def detect_provider() -> str:
    forced = os.environ.get("MOTD_AI_PROVIDER", "").lower()
    if forced:
        return forced
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("OLLAMA_URL") or _ollama_running():
        return "ollama"
    return "none"


def _ollama_running() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=1)
        return True
    except Exception:
        return False


# ── JSON parsing (shared) ──────────────────────────────────────────────────────

def parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    msg = json.loads(raw)
    for field in ("text", "author", "tag"):
        if field not in msg:
            raise ValueError(f"missing field: {field}")
    return msg


# ── providers ─────────────────────────────────────────────────────────────────

def call_anthropic(headlines: list[str]) -> dict:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("pip install anthropic")

    headline_block = "\n".join(f"- {h}" for h in headlines)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Today's headlines:\n{headline_block}\n\nWrite the Message of the Day."}],
    )
    raw = next(b.text for b in response.content if b.type == "text")
    return parse_json_response(raw)


def call_gemini(headlines: list[str]) -> dict:
    api_key = os.environ["GEMINI_API_KEY"]
    headline_block = "\n".join(f"- {h}" for h in headlines)
    prompt = f"{SYSTEM_PROMPT}\n\nToday's headlines:\n{headline_block}\n\nWrite the Message of the Day."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 256, "temperature": 0.9},
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_json_response(raw)


def call_groq(headlines: list[str]) -> dict:
    api_key = os.environ["GROQ_API_KEY"]
    headline_block = "\n".join(f"- {h}" for h in headlines)

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Today's headlines:\n{headline_block}\n\nWrite the Message of the Day."},
        ],
        "max_tokens": 256,
        "temperature": 0.9,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    raw = data["choices"][0]["message"]["content"]
    return parse_json_response(raw)


def call_ollama(headlines: list[str]) -> dict:
    base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    headline_block = "\n".join(f"- {h}" for h in headlines)
    prompt = f"{SYSTEM_PROMPT}\n\nToday's headlines:\n{headline_block}\n\nWrite the Message of the Day."

    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    raw = data["response"]
    return parse_json_response(raw)


def fallback_random() -> dict:
    """Pick a random message from messages.json — no AI required."""
    try:
        msgs = json.loads(MESSAGES_FILE.read_text()).get("messages", [])
        if msgs:
            m = random.choice(msgs)
            return {**m, "source": "curated", "generated_at": time.time()}
    except Exception:
        pass
    return {
        "text": "Keep going. You're doing better than you think.",
        "author": "Anonymous",
        "tag": "kindness",
        "source": "fallback",
        "generated_at": time.time(),
    }


# ── main generation ────────────────────────────────────────────────────────────

PROVIDER_FNS = {
    "anthropic": call_anthropic,
    "gemini":    call_gemini,
    "groq":      call_groq,
    "ollama":    call_ollama,
}


def generate(headlines: list[str]) -> dict:
    provider = detect_provider()
    print(f"  [provider] {provider}", file=sys.stderr)

    if provider == "none" or provider not in PROVIDER_FNS:
        print("  [info] no AI provider configured — using random curated message", file=sys.stderr)
        return fallback_random()

    try:
        msg = PROVIDER_FNS[provider](headlines)
        return {
            "text":         msg["text"],
            "author":       msg["author"],
            "tag":          msg["tag"],
            "generated_at": time.time(),
            "date":         time.strftime("%Y-%m-%d"),
            "source":       f"ai-{provider}",
        }
    except Exception as e:
        print(f"  [warn] {provider} failed: {e}", file=sys.stderr)
        return fallback_random()


def get_today_motd(force: bool = False, dry_run: bool = False,
                   cache_file: Path = CACHE_FILE) -> dict:
    if not force:
        cached = load_cache(cache_file)
        if cached:
            return cached

    headlines = fetch_headlines()
    if not headlines:
        print("  [warn] no headlines fetched — using fallback", file=sys.stderr)
        return fallback_random()

    if dry_run:
        print("Headlines:")
        for h in headlines:
            print(f"  {h}")
        return {}

    entry = generate(headlines)
    save_cache(entry, cache_file)
    return entry


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI-powered MOTD generator")
    parser.add_argument("--force",   action="store_true", help="Ignore cache, regenerate")
    parser.add_argument("--dry-run", action="store_true", help="Show headlines only, no AI call")
    parser.add_argument("--output",  help="Write result to this path instead of the default cache")
    args = parser.parse_args()

    cache_file = Path(args.output) if args.output else CACHE_FILE
    result = get_today_motd(force=args.force, dry_run=args.dry_run, cache_file=cache_file)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
