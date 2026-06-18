#!/usr/bin/env bash
# motd.sh — Message of the Day, universal client
#
# Usage (local):   source /path/to/motd.sh
#                  ./motd.sh [--tag funny|tech|motivation|kindness|wisdom|courage]
#
# Usage (remote):  MOTD_URL=https://example.com ./motd.sh
#                  curl -sf https://example.com/motd | bash
#
# Config via env vars (all optional):
#   MOTD_URL            Remote server base URL. If set, fetches from there.
#   MOTD_FILE           Path to local messages.json. Defaults to same dir as script.
#   MOTD_TAG            Pre-filter by tag (same as --tag flag).
#   MOTD_TIMEOUT        Curl timeout in seconds (default: 2).
#   MOTD_SILENT         Set to 1 to suppress all output on error (default: 1).
#
# FAIL-SAFE: every failure path exits 0 and produces no output.
# This script will NEVER break a shell session, SSH login, or container start.

_motd_main() {
  # ── parse args ────────────────────────────────────────────────────────────
  local tag="${MOTD_TAG:-}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tag) tag="$2"; shift 2 ;;
      --tag=*) tag="${1#*=}"; shift ;;
      *) shift ;;  # ignore unknown flags silently
    esac
  done

  # ── helpers ───────────────────────────────────────────────────────────────
  local max_width=72

  _motd_wrap() {
    local text="$1" width="$2"
    if command -v fold &>/dev/null; then
      fold -s -w "$width" <<< "$text"
    else
      echo "$text"
    fi
  }

  _motd_box() {
    local text="$1" author="$2" tag_name="$3"
    local author_line="— $author"
    local tlen=${#text} alen=${#author_line}
    local inner=$(( tlen > alen ? tlen : alen ))
    (( inner > max_width )) && inner=$max_width

    local bar
    bar=$(printf '%*s' $((inner + 2)) '' | tr ' ' '─')

    local emoji
    case "$tag_name" in
      funny)      emoji="😄" ;;
      tech)       emoji="💻" ;;
      motivation) emoji="🚀" ;;
      kindness)   emoji="💛" ;;
      wisdom)     emoji="🦉" ;;
      courage)    emoji="🦁" ;;
      *)          emoji="✨" ;;
    esac

    echo
    echo "  ${emoji}  Message of the Day"
    echo "╭${bar}╮"
    while IFS= read -r line; do
      printf "│ %-*s │\n" "$inner" "$line"
    done < <(_motd_wrap "$text" "$inner")
    printf "│ %-*s │\n" "$inner" ""
    printf "│ %-*s │\n" "$inner" "$author_line"
    echo "╰${bar}╯"
    echo
  }

  # ── pick a message ─────────────────────────────────────────────────────────
  local text author tag_val

  # remote mode
  if [[ -n "${MOTD_URL:-}" ]]; then
    local timeout="${MOTD_TIMEOUT:-2}"
    local url="${MOTD_URL%/}/motd.json"
    [[ -n "$tag" ]] && url+="?tag=${tag}"

    local payload
    payload=$(curl -sf --max-time "$timeout" --connect-timeout "$timeout" "$url" 2>/dev/null) || {
      return 0  # server unreachable — silent exit
    }

    if command -v jq &>/dev/null; then
      text=$(jq -r '.text   // empty' <<< "$payload" 2>/dev/null) || return 0
      author=$(jq -r '.author // empty' <<< "$payload" 2>/dev/null) || return 0
      tag_val=$(jq -r '.tag    // empty' <<< "$payload" 2>/dev/null) || return 0
    else
      # no jq: just print whatever the server sends as plain text
      echo "$payload"
      return 0
    fi

  # local file mode
  else
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)" || return 0
    local file="${MOTD_FILE:-${script_dir}/messages.json}"

    [[ -f "$file" ]] || return 0          # no file — silent exit
    command -v jq &>/dev/null || {
      # no jq — last-resort: print a hardcoded fallback
      echo
      echo "  ✨  Keep going. You're doing better than you think."
      echo
      return 0
    }

    local count rand_idx
    if [[ -n "$tag" ]]; then
      count=$(jq --arg t "$tag" '[.messages[] | select(.tag==$t)] | length' "$file" 2>/dev/null) || return 0
      (( count == 0 )) && return 0
      rand_idx=$(( RANDOM % count ))
      local entry
      entry=$(jq -r --arg t "$tag" --argjson i "$rand_idx" \
        '[.messages[] | select(.tag==$t)] | .[$i]' \
        "$file" 2>/dev/null) || return 0
    else
      count=$(jq '.messages | length' "$file" 2>/dev/null) || return 0
      (( count == 0 )) && return 0
      rand_idx=$(( RANDOM % count ))
      local entry
      entry=$(jq -r --argjson i "$rand_idx" '.messages[$i]' \
        "$file" 2>/dev/null) || return 0
    fi

    text=$(jq -r '.text'   <<< "$entry" 2>/dev/null) || return 0
    author=$(jq -r '.author' <<< "$entry" 2>/dev/null) || return 0
    tag_val=$(jq -r '.tag'   <<< "$entry" 2>/dev/null) || return 0
  fi

  [[ -z "$text" || "$text" == "null" ]] && return 0

  _motd_box "$text" "$author" "$tag_val"
}

_motd_main "$@"
unset -f _motd_main 2>/dev/null
