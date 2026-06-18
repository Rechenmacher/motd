"""
motd — a tiny Python package that ships the MOTD message library

>>> import motd
>>> print(motd.random_message())
>>> print(motd.random_message(tag="funny"))
>>> print(motd.messages())  # all messages
"""

import json
import random
from pathlib import Path

_DATA = Path(__file__).parent / "messages.json"
_MESSAGES: list[dict] = json.loads(_DATA.read_text()).get("messages", [])


def messages(tag: str | None = None) -> list[dict]:
    """Return all messages, optionally filtered by tag."""
    msgs = _MESSAGES
    if tag:
        msgs = [m for m in msgs if m.get("tag") == tag]
    return msgs


def random_message(tag: str | None = None) -> dict:
    """Return one random message, optionally from a specific tag."""
    pool = messages(tag) or messages()
    return random.choice(pool)


def format_message(msg: dict) -> str:
    """Format a message dict as readable plain text."""
    return f'"{msg["text"]}"\n  — {msg["author"]}'


__all__ = ["messages", "random_message", "format_message"]
