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

# the folder: the one this script sits in, or the default
DEST="${GREEKSOUP_HOME:-$HOME/GreekSoup}"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/server.py" ]; then DEST="$SELF_DIR"; fi
printf '\n  GreekSoup: uninstall\n  --------------------\n'
if [ ! -f "$DEST/server.py" ]; then
  say "No desk folder at $DEST. If it lives elsewhere, run: GREEKSOUP_HOME=/path/to/it bash uninstall.sh"
  exit 1
fi
say "Desk folder: $DEST"

# 1. stop it and remove the start-at-login entry
if [ "$OS" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.research-desk.plist"
  launchctl bootout "gui/$(id -u)/com.research-desk" >/dev/null 2>&1 || launchctl unload "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST" && say "Start-at-login entry removed."
else
  systemctl --user disable --now greeksoup-desk.service >/dev/null 2>&1 || true
  rm -f "$HOME/.config/systemd/user/greeksoup-desk.service" && systemctl --user daemon-reload >/dev/null 2>&1 || true
  say "Start-at-login entry removed."
fi
# stop only the desk that runs from THIS folder
pkill -f "$DEST/.venv/bin/python server.py" >/dev/null 2>&1 || pkill -f "python server.py" >/dev/null 2>&1 || true
say "The desk is stopped."

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
