# motd — a resurrection of the message of the day

Simple, fail-safe, integrable everywhere. A warm message in your terminal, SSH login, container, or browser — without ever breaking anything if it's not available.

**Core rule: if MOTD fails, nothing breaks. Not your shell. Not your SSH session. Not your container start.**

---

## Quick start

```bash
git clone https://github.com/Rechenmacher/motd
cd motd
bash motd.sh
```

Requires `jq` for full rendering. Falls back gracefully without it.

---

## Integration

### Local shell — `.bashrc` / `.zshrc`

```bash
source /path/to/motd/motd.sh 2>/dev/null || true
```

### SSH server — dynamic MOTD on login

```bash
sudo cp integrate/99-motd /etc/update-motd.d/99-motd
sudo chmod +x /etc/update-motd.d/99-motd
```

Edit the script to point at your install path or remote server URL. On Debian/Ubuntu, `update-motd.d` scripts run automatically on SSH login.

### Remote server — curl from anywhere

Start the server:
```bash
python3 server.py --port 8000
```

Then from any machine:
```bash
# Plain text (curl-friendly, pipe-friendly)
curl -sf https://your-server/motd

# In .bashrc — silent on failure, 2-second timeout
curl -sf --max-time 2 https://your-server/motd 2>/dev/null || true

# motd.sh fetching from a remote server
MOTD_URL=https://your-server bash motd.sh
```

### Docker / containers

```dockerfile
COPY integrate/docker.sh /etc/profile.d/motd.sh
RUN chmod +x /etc/profile.d/motd.sh
```

Runs on every interactive shell start (`docker exec -it`, SSH, etc.).

### Any system — one-liner remote bootstrap

```bash
# Fetch and run in a subshell — fails silently if server is down
bash <(curl -sf --max-time 2 https://your-server/motd.sh) 2>/dev/null || true
```

---

## Server endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | HTML web portal |
| `GET /motd` | Random message, plain text |
| `GET /motd.json` | Random message, JSON |
| `GET /all.json` | Full message list |
| `GET /motd?tag=funny` | Filtered by tag |
| `GET /motd/today` | AI-generated message inspired by today's news (cached 12h) |

---

## Configuration

All via environment variables — no config file needed:

| Variable | Default | Description |
|---|---|---|
| `MOTD_URL` | _(unset)_ | Remote server base URL. If set, fetches remotely. |
| `MOTD_FILE` | `./messages.json` | Path to local messages file. |
| `MOTD_TAG` | _(unset)_ | Pre-filter messages by tag. |
| `MOTD_TIMEOUT` | `2` | Curl timeout in seconds for remote fetches. |

---

## AI-powered message of the day

`generator/today.py` fetches today's top headlines from free RSS feeds (BBC World, HackerNews, Reuters — no API keys) and asks Claude to write a funny, warm MOTD inspired by what's actually happening right now. The result is cached for 12 hours.

```bash
# standalone — print today's AI-generated message
pip install anthropic
export ANTHROPIC_API_KEY=sk-...
python3 generator/today.py

# dry run — see what headlines were fetched, no Claude call
python3 generator/today.py --dry-run

# force regeneration, ignore cache
python3 generator/today.py --force

# via server — GET /motd/today (requires ANTHROPIC_API_KEY at server start)
ANTHROPIC_API_KEY=sk-... python3 server.py
curl http://localhost:8000/motd/today
```

Model: `claude-haiku-4-5` — fast and cheap (~$0.0003 per generation, which at 2× per day is under $0.25/year).

---

## Bulk-import messages

`scripts/import.py` pulls from quotable.io (free, no key, ~150 quotes/page) and fortune-mod text files:

```bash
# import 10 pages ≈ 1500 quotes from quotable.io, merge with existing
python3 scripts/import.py --quotable 10

# import fortune-mod files (if installed)
python3 scripts/import.py --fortune /usr/share/games/fortunes

# both
python3 scripts/import.py --quotable 5 --fortune /usr/share/games/fortunes
```

---

## Adding messages

Edit `messages.json` — one object per message:

```json
{
  "text": "Your message here.",
  "author": "Someone",
  "tag": "wisdom"
}
```

**Available tags:** `funny` · `tech` · `motivation` · `kindness` · `wisdom` · `courage`

Tags are free-form strings — add your own. The web portal and `--tag` filter pick them up automatically.

---

## Fail-safe guarantees

- `motd.sh` wraps everything in a function; any error returns `0`
- Network fetches use `--max-time 2` and `--connect-timeout 2`
- Missing `jq` → hardcoded fallback message, no crash
- Missing `messages.json` → silent exit
- Malformed JSON → silent exit
- Server `99-motd` script runs `set +e` and ends with `exit 0`
- `server.py` ships a built-in fallback message; never returns 500

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
