#!/usr/bin/env bash
# GreekSoup: the one-person equity research desk. Uninstall for Mac and Linux.
#
#   curl -fsSL https://greeksoup.ai/uninstall.sh | bash
#   or double-click "Uninstall Desk.command" in the desk folder.
#
# Stops the desk, removes the start-at-login entry, offers a backup of your
# lists, and then asks before deleting the folder. Nothing else was ever
# installed outside the folder. Python stays; it is yours.
set -u
OS="$(uname -s)"
say() { printf '  %s\n' "$*"; }

# Which folder to remove: what you named, else the folder this file sits in, else the
# one the install line makes. What you named always wins, so this can never walk off
# to a different copy of the desk than the one you meant.
DEST="${GREEKSOUP_HOME:-}"
if [ -z "$DEST" ]; then
  SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
  if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/server.py" ]; then DEST="$SELF_DIR"; else DEST="$HOME/GreekSoup"; fi
fi
printf '\n  GreekSoup: uninstall\n  --------------------\n'
if [ ! -f "$DEST/server.py" ]; then
  say "No desk folder at $DEST. If it lives elsewhere, run: GREEKSOUP_HOME=/path/to/it bash uninstall.sh"
  exit 1
fi
say "Desk folder: $DEST"

# 1. remove the start-at-login entry, but only when it is this folder's own. Somebody
# with a second copy of the desk keeps that copy's entry exactly as it is.
names_this_folder() { [ -f "$1" ] && grep -Fq "$DEST" "$1"; }
if [ "$OS" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.research-desk.plist"
  if names_this_folder "$PLIST"; then
    launchctl bootout "gui/$(id -u)/com.research-desk" >/dev/null 2>&1 || launchctl unload "$PLIST" >/dev/null 2>&1 || true
    rm -f "$PLIST" && say "Start-at-login entry removed."
  elif [ -f "$PLIST" ]; then
    say "Left the start-at-login entry alone: it starts another copy of the desk, not this one."
  else
    say "No start-at-login entry to remove."
  fi
else
  UNIT="$HOME/.config/systemd/user/greeksoup-desk.service"
  if names_this_folder "$UNIT"; then
    systemctl --user disable --now greeksoup-desk.service >/dev/null 2>&1 || true
    rm -f "$UNIT" && systemctl --user daemon-reload >/dev/null 2>&1 || true
    say "Start-at-login entry removed."
  elif [ -f "$UNIT" ]; then
    say "Left the start-at-login entry alone: it starts another copy of the desk, not this one."
  else
    say "No start-at-login entry to remove."
  fi
fi
# Stop only the desk that runs from THIS folder. A running desk is found by the door
# number in its own settings file, and it is closed only when the program answering
# there is working inside this folder, so another copy on the same computer is never
# touched. (Its own command line does not carry the folder's name, so matching on the
# name would either miss this desk or close somebody else's.)
PORT="$(sed -n 's/^[[:space:]]*DESK_PORT[[:space:]]*=[[:space:]]*//p' "$DEST/.env" 2>/dev/null | tr -d '"'"'"' ' | head -1)"
[ -n "$PORT" ] || PORT=8765
STOPPED=0
if command -v lsof >/dev/null 2>&1; then
  for PID in $(lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null); do
    CWD="$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
    case "$CWD" in
      "$DEST"|"$DEST"/*) kill "$PID" 2>/dev/null && STOPPED=1 ;;
    esac
  done
fi
sleep 1
if curl -s -m 2 -o /dev/null "http://localhost:$PORT/api/ping" 2>/dev/null; then
  say "Something is still answering on door $PORT. If that is this desk, double-click Stop Desk in the folder, then run this again."
elif [ "$STOPPED" = "1" ]; then
  say "The desk is stopped."
else
  say "The desk was not running."
fi

# 2. a copy of your lists, keys excluded
STAMP="$(date +%Y-%m-%d)"
BACKUP="$HOME/Desktop/GreekSoup-backup-$STAMP.zip"
[ -d "$HOME/Desktop" ] || BACKUP="$HOME/GreekSoup-backup-$STAMP.zip"
if [ -d "$DEST/data" ] && command -v zip >/dev/null 2>&1; then
  (cd "$DEST" && zip -qr "$BACKUP" data research 2>/dev/null) && say "Your lists and data are saved at $BACKUP (your keys are not in it)."
fi

# 3. the folder itself, only if you say so
if [ -t 0 ]; then
  printf '  Delete the folder %s as well? [y/N] ' "$DEST"
  read -r ANSWER
else
  ANSWER="${GREEKSOUP_DELETE:-n}"
fi
case "$ANSWER" in
  y|Y|yes|YES)
    cd "$HOME" && rm -rf "$DEST" && say "Folder deleted. GreekSoup is gone from this computer." ;;
  *)
    say "Folder kept at $DEST. Delete it whenever you like; nothing else remains." ;;
esac
printf '\n'
