#!/bin/bash
# Installs a macOS LaunchAgent that backs up the database every night at 03:00.
# If the Mac is asleep at 03:00, launchd runs it when the Mac wakes. Keeps the newest 14 copies.
#   install:   deploy/install-nightly-backup.sh
#   remove:    deploy/install-nightly-backup.sh --remove
set -euo pipefail

LABEL="com.spincount.backup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${1:-}" == "--remove" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL"
  exit 0
fi

[[ -x "$ROOT/.venv/bin/python" ]] || { echo "Run 'make setup' first (no $ROOT/.venv)"; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/backend/backups"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/.venv/bin/python</string>
    <string>-m</string>
    <string>app.backup</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT/backend</string>
  <key>EnvironmentVariables</key>
  <dict><key>PYTHONPATH</key><string>$ROOT:$ROOT/backend</string></dict>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$ROOT/backend/backups/backup.log</string>
  <key>StandardErrorPath</key><string>$ROOT/backend/backups/backup.log</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Installed $LABEL: nightly backup at 03:00 into $ROOT/backend/backups (keeps 14)."
echo "Try it now with:  launchctl kickstart gui/$(id -u)/$LABEL"
