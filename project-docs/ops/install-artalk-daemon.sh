#!/bin/bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run with sudo: sudo bash project-docs/ops/install-artalk-daemon.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/ai.openclaw.artalk.daemon.plist"
PLIST_DST=/Library/LaunchDaemons/ai.openclaw.artalk.plist
USER_PLIST=/Users/mac/Library/LaunchAgents/ai.openclaw.artalk.plist

echo "== 1. stop user LaunchAgent =="
sudo -u mac launchctl bootout gui/501/ai.openclaw.artalk 2>/dev/null || true
if [ -f "$USER_PLIST" ]; then
  STAMP=$(date +%Y%m%d-%H%M%S)
  sudo -u mac mv "$USER_PLIST" "$USER_PLIST.disabled-by-daemon-$STAMP"
  echo "moved user plist to $USER_PLIST.disabled-by-daemon-$STAMP"
fi

echo "== 2. install daemon =="
install -o root -g wheel -m 644 "$PLIST_SRC" "$PLIST_DST"
plutil -lint "$PLIST_DST"

echo "== 3. load daemon =="
launchctl bootout system/ai.openclaw.artalk 2>/dev/null || true
launchctl bootstrap system "$PLIST_DST"
launchctl kickstart -k system/ai.openclaw.artalk
sleep 4

echo "== 4. verify =="
launchctl print system/ai.openclaw.artalk | grep -E "state =|pid =|runs =|user =|path ="
pgrep -fl "artalk server" || true
lsof -nP -iTCP:23366 -sTCP:LISTEN || true
curl -s -o /dev/null -w "local=%{http_code}\n" http://127.0.0.1:23366/sidebar/
curl -s -o /dev/null -w "public=%{http_code}\n" https://seres-ai.com/sidebar/
sqlite3 /Users/mac/artalk/data/artalk.db "select count(*) from comments;"

if ! lsof -nP -iTCP:23366 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "WARN: daemon did not open 23366; starting manual fallback"
  sudo -u mac bash -c 'cd /Users/mac/artalk && nohup ./artalk server -c config.yml >> server.log 2>&1 &'
  sleep 3
  lsof -nP -iTCP:23366 -sTCP:LISTEN || true
fi
