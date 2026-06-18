#!/usr/bin/env python3
"""
generator/today.py — AI-powered Message of the Day

Fetches today's top news headlines from free RSS feeds (no API key needed),
then asks Claude to write a funny, warm, or witty MOTD inspired by what's
actually happening in the world right now.

The result is cached in generator/cache.json for 12 hours so Claude is only
called once per half-day regardless of how many people fetch /motd/today.

Usage:
  python3 generator/today.py               # generate and print
  python3 generator/today.py --force       # ignore cache, regenerate
  python3 generator/today.py --dry-run     # show headlines, no Claude call

Requires:
  pip install anthropic
  ANTHROPIC_API_KEY must be set in environment
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "cache.json"
CACHE_TTL  = 12 * 3600  # 12 hours

# Free RSS feeds — no auth, no rate limits worth worrying about
RSS_FEEDS = [
    ("BBC World News",   "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Hacker News Top",  "https://hnrss.org/frontpage?count=10"),
    ("Reuters World",    "https://feeds.reuters.com/reuters/worldNews"),
]

MAX_HEADLINES = 12  # how many we feed to Claude


# ── RSS parsing ────────────────────────────────────────────────────────────────

def fetch_headlines(feeds: list[tuple[str, str]], max_total: int) -> list[str]:
    headlines: list[str] = []
    for name, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "motd-generator/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                content = r.read()
            root = ET.fromstring(content)
            # RSS 2.0 and Atom both have <title> inside <item> or <entry>
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

def load_cache() -> dict | None:
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("generated_at", 0) < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def save_cache(entry: dict) -> None:
    try:
        CACHE_FILE.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"  [warn] could not write cache: {e}", file=sys.stderr)


# ── Claude call ───────────────────────────────────────────────────────────────

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


def generate_with_claude(headlines: list[str]) -> dict:
    try:
        import anthropic
    except ImportError:
        print("pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    headline_block = "\n".join(f"- {h}" for h in headlines)
    user_msg = f"Today's headlines:\n{headline_block}\n\nWrite the Message of the Day."

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5",          # fast + cheap for this use case
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = next(b.text for b in response.content if b.type == "text")

    # strip markdown fences if Claude added them
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    msg = json.loads(raw)
    # validate required fields
    for field in ("text", "author", "tag"):
        if field not in msg:
            raise ValueError(f"missing field: {field}")

    return {
        "text":         msg["text"],
        "author":       msg["author"],
        "tag":          msg["tag"],
        "generated_at": time.time(),
        "source":       "ai-generated",
    }


# ── main ──────────────────────────────────────────────────────────────────────

def get_today_motd(force: bool = False, dry_run: bool = False) -> dict:
    if not force:
        cached = load_cache()
        if cached:
            return cached

    headlines = fetch_headlines(RSS_FEEDS, MAX_HEADLINES)
    if not headlines:
        # graceful fallback — no network, no problem
        return {
            "text":   "The internet is quiet today. Make something good happen anyway.",
            "author": "Your Terminal",
            "tag":    "motivation",
            "source": "fallback",
        }

    if dry_run:
        print("Headlines:")
        for h in headlines:
            print(f"  {h}")
        return {}

    entry = generate_with_claude(headlines)
    save_cache(entry)
    return entry


def main():
    parser = argparse.ArgumentParser(description="AI-powered MOTD generator")
    parser.add_argument("--force",   action="store_true", help="Ignore cache")
    parser.add_argument("--dry-run", action="store_true", help="Show headlines only")
    args = parser.parse_args()

    result = get_today_motd(force=args.force, dry_run=args.dry_run)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
