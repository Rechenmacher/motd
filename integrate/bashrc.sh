# ── MOTD — add to ~/.bashrc or ~/.zshrc ──────────────────────────────────────
# Option A: local install (clone the repo, point to it)
source "$HOME/.local/share/motd/motd.sh" 2>/dev/null || true

# Option B: remote server — fetches with a 2-second timeout, silent on failure
# MOTD_URL=https://your-motd-server.example.com source <(curl -sf --max-time 2 https://your-motd-server.example.com/motd.sh) 2>/dev/null || true

# Option C: pure curl, no shell script needed — just prints plain text
# curl -sf --max-time 2 https://your-motd-server.example.com/motd 2>/dev/null || true
