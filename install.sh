#!/bin/bash
# GreekSoup: the one-person equity research desk. One-line install for Mac and Linux.
#
#   curl -fsSL https://greeksoup.ai/install.sh | bash
#
# What it does, in order: finds Python (installs it on a Mac if missing), downloads the
# desk into ~/GreekSoup, installs what it needs into its own folder, sets the desk to
# start with your computer and restart if it stops, starts it, and opens it in your
# browser at http://localhost:8765. Nothing is installed outside that folder except the
# small start-at-login entry. Run it again later and it only starts the desk; updates
# come through the strip inside the desk.
#
# Knobs (optional): GREEKSOUP_HOME=/some/folder  GREEKSOUP_PORT=8770  GREEKSOUP_NO_SERVICE=1
set -e

REPO="shubhamsborkar/one-person-equity-research-desk"
ZIP_URL="https://codeload.github.com/$REPO/zip/refs/heads/main"
DEST="${GREEKSOUP_HOME:-$HOME/GreekSoup}"
PORT="${GREEKSOUP_PORT:-8765}"
NO_SERVICE="${GREEKSOUP_NO_SERVICE:-}"
PY_VERSION="3.12.7"
OS="$(uname -s)"

say()  { printf '\n  %s\n' "$*"; }
fail() { printf '\n  %s\n\n' "$*"; exit 1; }

printf '\n  GreekSoup: the one-person equity research desk\n  ------------------------------------------------\n'

# ---------------------------------------------------------------- 1. Python
find_python() {
  for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
        command -v "$c"; return 0
      fi
    fi
  done
  return 1
}
PY="$(find_python || true)"
if [ -z "$PY" ]; then
  if [ "$OS" = "Darwin" ]; then
    say "Python is not on this Mac yet. Installing it from python.org (your Mac will ask for your password once)."
    PKG="/tmp/python-$PY_VERSION.pkg"
    curl -fsSL "https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-macos11.pkg" -o "$PKG"
    sudo installer -pkg "$PKG" -target / >/dev/null
    rm -f "$PKG"
    PY="$(find_python || true)"
    [ -n "$PY" ] || fail "Python was installed but could not be found. Close this window, open a new Terminal and run the same line again."
  else
    fail "Python 3.10 or newer is needed. On Ubuntu or Debian: sudo apt install python3 python3-venv   On Fedora: sudo dnf install python3   Then run this line again."
  fi
fi
say "Python found: $("$PY" --version 2>&1)"

# ---------------------------------------------------------------- 2. The folder
if [ -f "$DEST/server.py" ]; then
  say "The desk is already installed at $DEST. Starting it; new versions arrive through the strip inside the desk."
else
  say "Downloading the desk into $DEST ..."
  TMP="$(mktemp -d)"
  curl -fsSL "$ZIP_URL" -o "$TMP/desk.zip"
  ( cd "$TMP" && unzip -q desk.zip )
  SRC="$(find "$TMP" -maxdepth 1 -mindepth 1 -type d | head -1)"
  mkdir -p "$(dirname "$DEST")"
  mv "$SRC" "$DEST"
  rm -rf "$TMP"
fi
cd "$DEST"

# ---------------------------------------------------------------- 3. Its own environment
if [ ! -x ".venv/bin/python" ]; then
  say "Installing what the desk needs (into its own folder, nothing else on your computer changes) ..."
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --upgrade pip >/dev/null 2>&1 || true
.venv/bin/python -m pip install -q -r requirements.txt

# ---------------------------------------------------------------- 4. Settings file
if [ ! -f ".env" ]; then
  cp .env.example .env
  if [ "$PORT" != "8765" ]; then
    sed -i.bak "s/^DESK_PORT=.*/DESK_PORT=$PORT/" .env && rm -f .env.bak
  fi
fi
chmod +x *.command 2>/dev/null || true
mkdir -p logs

# ---------------------------------------------------------------- 5. Start it, and keep it running
already() { curl -s -m 2 -o /dev/null "http://localhost:$PORT/api/ping"; }
if already; then
  say "The desk is already running."
elif [ -n "$NO_SERVICE" ]; then
  nohup .venv/bin/python server.py </dev/null >logs/desk.log 2>&1 &
  say "Started the desk (this run only; not set to start at login)."
elif [ "$OS" = "Darwin" ]; then
  DESK_PORT="$PORT" zsh "Keep Desk Running.command" </dev/null | sed 's/^/  /' | grep -v "close this window" || true
else
  UNIT_DIR="$HOME/.config/systemd/user"; mkdir -p "$UNIT_DIR"
  cat > "$UNIT_DIR/greeksoup-desk.service" <<UNIT
[Unit]
Description=GreekSoup desk
[Service]
ExecStart=$DEST/.venv/bin/python server.py
WorkingDirectory=$DEST
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
UNIT
  systemctl --user daemon-reload && systemctl --user enable --now greeksoup-desk.service
  say "The desk starts at every login and restarts by itself if it stops."
fi

for _ in $(seq 1 30); do already && break; sleep 2; done
already || fail "The desk has not answered yet. Give it a minute, then open http://localhost:$PORT . If it stays blank, read $DEST/logs/desk-service.log or give it to your AI agent."

# ---------------------------------------------------------------- 6. Open it
URL="http://localhost:$PORT"
if [ "$OS" = "Darwin" ]; then open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true; fi

if [ -n "$NO_SERVICE" ]; then printf '\n  Done. The desk is at %s (this run only).\n' "$URL"
else printf '\n  Done. The desk is at %s and it starts with your computer from now on.\n' "$URL"; fi
printf '  Folder: %s\n' "$DEST"
printf '  Keys are optional: they go in the .env file in that folder, or ask your AI agent to add them.\n'
printf '  Newer versions: the desk tells you on every screen and updates with one click.\n\n'
