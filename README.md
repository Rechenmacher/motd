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

## Dynamic daily message — works on GitHub Pages, free options included

The site shows a **"Today's message"** card that updates every day via GitHub Actions. No server required — the workflow generates `today.json` and commits it back to the repo, then GitHub Pages serves it as a static file.

### How it works

```
GitHub Actions (daily cron)
  → fetch RSS headlines (BBC, HN, Reuters — no key needed)
  → call AI provider (your choice, several are free)
  → write today.json
  → commit & push → GitHub Pages serves it instantly
```

### Setup: add one secret to your repo

Go to **Settings → Secrets and variables → Actions → New repository secret** and add whichever key you have:

| Secret name | Provider | Free? | Sign up |
|---|---|---|---|
| `GROQ_API_KEY` | Groq (Llama 3) | **Yes — generous free tier** | [console.groq.com](https://console.groq.com) |
| `GEMINI_API_KEY` | Google Gemini | **Yes — 1500 req/day free** | [aistudio.google.com](https://aistudio.google.com) |
| `ANTHROPIC_API_KEY` | Claude | Paid (best quality) | [console.anthropic.com](https://console.anthropic.com) |

No secret set? The workflow still runs — it just picks a random message from the curated library instead. Nothing breaks.

### Trigger the first run manually

After adding a secret, go to **Actions → Generate daily MOTD → Run workflow**.
The result is committed to `today.json` and live on your GitHub Pages site within seconds.

### Run locally with any provider

```bash
# Groq (free)
GROQ_API_KEY=gsk_... python3 generator/today.py --force

# Gemini (free)
GEMINI_API_KEY=... python3 generator/today.py --force

# Anthropic Claude (paid)
ANTHROPIC_API_KEY=sk-... python3 generator/today.py --force

# Ollama (fully local, no key needed)
OLLAMA_URL=http://localhost:11434 python3 generator/today.py --force

# No AI — picks a random curated message
python3 generator/today.py --force

# Dry run — show today's headlines without calling any AI
python3 generator/today.py --dry-run

# Write output to a specific file (used by the GitHub Actions workflow)
GROQ_API_KEY=... python3 generator/today.py --force --output today.json
```

Provider is auto-detected from whichever env var is set. Override with `MOTD_AI_PROVIDER=gemini`.

---

## AI-powered message of the day (self-hosted server)

When self-hosting `server.py`, the `GET /motd/today` endpoint calls the generator on demand and caches the result for 12 hours:

```bash
# with any provider
GROQ_API_KEY=gsk_... python3 server.py
curl http://localhost:8000/motd/today
```

Claude Haiku cost if using Anthropic: ~$0.0003 per generation, under $0.25/year at 2× per day.

---

## Message library

### What ships in the repo

`messages.json` contains **4,104 balanced entries** — the right size for GitHub Pages, browser demos, and quick installs. Tags are capped at ~800 each so no single category dominates.

| Tag | Count |
|---|---|
| motivation | ~808 |
| wisdom | ~805 |
| kindness | ~807 |
| courage | ~803 |
| funny | ~716 |
| tech | ~165 |

### Full 40k archive — GitHub Release

The full **40,337-quote** archive is published as a release asset (8.7MB). It is not committed to the repo, but is permanently available to download:

```bash
# download the full archive into data/ (gitignored)
curl -L -o data/messages-full.json \
  https://github.com/Rechenmacher/motd/releases/download/v1.0.0/messages-full.json

# run the server against it
python3 server.py --messages data/messages-full.json
```

Release page: [github.com/Rechenmacher/motd/releases/tag/v1.0.0](https://github.com/Rechenmacher/motd/releases/tag/v1.0.0)

Sources: [JamesFT/Database-Quotes-JSON](https://github.com/JamesFT/Database-Quotes-JSON) (5,421 quotes) + [alvations/Quotables](https://github.com/alvations/Quotables) (~39,000 quotes).

### Regenerate or extend the library locally

```bash
# rebuild the full 40k archive from scratch
python3 scripts/import.py --github --no-existing \
  --output data/messages-full.json

# rebuild balanced messages.json (4k entries, cap 800 per tag)
python3 scripts/import.py --github --no-existing --limit-per-tag 800

# import fortune-mod files (if installed)
python3 scripts/import.py --fortune /usr/share/games/fortunes

# merge everything, cap per tag
python3 scripts/import.py --github \
  --fortune /usr/share/games/fortunes \
  --limit-per-tag 800
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
