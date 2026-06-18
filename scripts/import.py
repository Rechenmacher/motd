#!/usr/bin/env python3
"""
import.py — build a big messages.json from multiple sources

Sources:
  --fortune PATH   Directory of fortune-mod plaintext files (% separated)
  --quotable N     Fetch N pages from quotable.io (150 quotes/page, free, no key)
  --hn             Fetch Show HN / Ask HN posts as "tech wisdom" messages
  --existing PATH  Merge an existing messages.json (default: ../messages.json)

Output: writes merged, deduplicated messages.json to the repo root.

Usage:
  python3 scripts/import.py --quotable 10
  python3 scripts/import.py --fortune /usr/share/games/fortunes
  python3 scripts/import.py --quotable 5 --fortune /usr/share/games/fortunes
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OUTPUT = REPO_ROOT / "messages.json"

# ── tag inference ──────────────────────────────────────────────────────────────
FUNNY_WORDS = {"laugh", "joke", "funny", "humor", "wit", "comic", "absurd",
               "silly", "irony", "sarcasm", "fool", "bug", "error", "crash"}
TECH_WORDS  = {"code", "program", "software", "computer", "debug", "algorithm",
               "engineer", "data", "linux", "unix", "kernel", "compiler", "git"}
KIND_WORDS  = {"kind", "compassion", "love", "heart", "gentle", "care", "friend",
               "empathy", "grace", "warm", "help", "support"}
COURAGE_WORDS = {"brave", "courage", "fear", "risk", "dare", "bold", "warrior",
                 "fight", "resilience", "persist", "overcome"}


def infer_tag(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r'\w+', lower))
    if words & TECH_WORDS:    return "tech"
    if words & FUNNY_WORDS:   return "funny"
    if words & KIND_WORDS:    return "kindness"
    if words & COURAGE_WORDS: return "courage"
    if any(w in lower for w in ("wisdom", "truth", "life", "mind", "soul", "nature")):
        return "wisdom"
    return "motivation"


def normalize(text: str, author: str, tag: str | None = None) -> dict | None:
    text = text.strip()
    author = author.strip() or "Anonymous"
    if len(text) < 10 or len(text) > 500:
        return None
    return {"text": text, "author": author, "tag": tag or infer_tag(text)}


# ── fortune-mod ───────────────────────────────────────────────────────────────
def parse_fortune_file(path: Path) -> list[dict]:
    """Parse a fortune-mod plaintext file (entries separated by %)."""
    messages = []
    try:
        content = path.read_text(errors="replace")
    except Exception:
        return []

    for block in content.split("\n%\n"):
        block = block.strip()
        if not block or len(block) > 500:
            continue
        # try to extract attribution on last line starting with -- or --
        lines = block.splitlines()
        author = "Anonymous"
        if len(lines) > 1:
            last = lines[-1].strip()
            if last.startswith("--") or last.startswith("—"):
                author = re.sub(r'^[-—\s]+', '', last).strip()
                block = "\n".join(lines[:-1]).strip()

        msg = normalize(block, author)
        if msg:
            messages.append(msg)
    return messages


def import_fortune(directory: str) -> list[dict]:
    d = Path(directory)
    messages = []
    for p in d.rglob("*"):
        if p.suffix in (".dat", ".u8", "") and p.is_file() and p.stat().st_size < 2_000_000:
            batch = parse_fortune_file(p)
            print(f"  fortune: {p.name}: {len(batch)} messages")
            messages.extend(batch)
    return messages


# ── quotable.io ───────────────────────────────────────────────────────────────
TAG_MAP = {
    "humor":       "funny",
    "technology":  "tech",
    "inspirational": "motivation",
    "motivational":  "motivation",
    "love":        "kindness",
    "wisdom":      "wisdom",
    "courage":     "courage",
    "business":    "motivation",
    "life":        "wisdom",
    "success":     "motivation",
}

def import_quotable(pages: int) -> list[dict]:
    messages = []
    for page in range(1, pages + 1):
        url = f"https://api.quotable.io/quotes?page={page}&limit=150"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            for q in data.get("results", []):
                raw_tags = q.get("tags", [])
                tag = next((TAG_MAP[t] for t in raw_tags if t in TAG_MAP), None)
                msg = normalize(q.get("content", ""), q.get("author", ""), tag)
                if msg:
                    messages.append(msg)
            print(f"  quotable page {page}: {len(data.get('results', []))} quotes")
            time.sleep(0.3)
        except Exception as e:
            print(f"  quotable page {page}: failed ({e})", file=sys.stderr)
            break
    return messages


# ── github public datasets ─────────────────────────────────────────────────────
def import_github_datasets() -> list[dict]:
    messages = []

    # Dataset 1: JamesFT JSON — 5400+ general quotes (windows-1252 encoded)
    url = "https://raw.githubusercontent.com/JamesFT/Database-Quotes-JSON/master/quotes.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            raw = r.read().decode("windows-1252", errors="replace")
        data = json.loads(raw)
        for q in data:
            msg = normalize(q.get("quoteText", ""), q.get("quoteAuthor") or "Anonymous")
            if msg:
                messages.append(msg)
        print(f"  github/JamesFT: {len(data)} quotes")
    except Exception as e:
        print(f"  github/JamesFT: failed ({e})", file=sys.stderr)

    # Dataset 2: manassaloi/goodreads-quotes — programming & wisdom
    url2 = "https://raw.githubusercontent.com/alvations/Quotables/master/author-quote.txt"
    try:
        with urllib.request.urlopen(url2, timeout=15) as r:
            lines = r.read().decode(errors="replace").splitlines()
        for line in lines:
            parts = line.split("\t", 1)
            if len(parts) == 2:
                author, text = parts[0].strip(), parts[1].strip()
                msg = normalize(text, author)
                if msg:
                    messages.append(msg)
        print(f"  github/alvations Quotables: {len(lines)} lines processed")
    except Exception as e:
        print(f"  github/alvations: failed ({e})", file=sys.stderr)

    return messages


# ── merge & deduplicate ───────────────────────────────────────────────────────
def deduplicate(messages: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for m in messages:
        key = re.sub(r'\W+', '', m["text"].lower())[:80]
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


def load_existing(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text()).get("messages", [])
    except Exception:
        return []


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fortune",   help="Path to fortune-mod data directory")
    parser.add_argument("--quotable",  type=int, default=0, metavar="PAGES",
                        help="Pages to fetch from quotable.io (150/page, may be offline)")
    parser.add_argument("--github", action="store_true",
                        help="Fetch from free public GitHub quote datasets (~6000+ quotes)")
    parser.add_argument("--existing",  default=str(OUTPUT),
                        help="Existing messages.json to merge (default: messages.json)")
    parser.add_argument("--output",    default=str(OUTPUT))
    parser.add_argument("--no-existing", action="store_true",
                        help="Don't merge existing messages")
    parser.add_argument("--limit-per-tag", type=int, default=0, metavar="N",
                        help="Cap each tag at N entries to keep the file balanced")
    args = parser.parse_args()

    messages = []

    if not args.no_existing:
        existing = load_existing(Path(args.existing))
        print(f"  existing: {len(existing)} messages")
        messages.extend(existing)

    if args.fortune:
        batch = import_fortune(args.fortune)
        print(f"  fortune total: {len(batch)}")
        messages.extend(batch)

    if args.quotable:
        batch = import_quotable(args.quotable)
        print(f"  quotable total: {len(batch)}")
        messages.extend(batch)

    if args.github:
        batch = import_github_datasets()
        print(f"  github datasets total: {len(batch)}")
        messages.extend(batch)

    messages = deduplicate(messages)

    if args.limit_per_tag:
        from collections import defaultdict
        import random as _random
        buckets = defaultdict(list)
        for m in messages:
            buckets[m["tag"]].append(m)
        messages = []
        for tag, bucket in buckets.items():
            _random.shuffle(bucket)
            chosen = bucket[:args.limit_per_tag]
            messages.extend(chosen)
            print(f"  tag '{tag}': {len(bucket)} → kept {len(chosen)}")
        _random.shuffle(messages)

    print(f"\n  Total after dedup: {len(messages)} messages")

    out = Path(args.output)
    out.write_text(json.dumps({"messages": messages}, indent=2, ensure_ascii=False))
    print(f"  Written to {out}")


if __name__ == "__main__":
    main()
