#!/bin/zsh

set -u

WORKSPACE="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
HOST="127.0.0.1"
PORT="8787"
URL="http://${HOST}:${PORT}/"
STATUS_URL="${URL}api/status"
RUNTIME_DIR="$WORKSPACE/.human-ai/runtime"
LOG_PATH="$RUNTIME_DIR/gima-web.log"
PID_PATH="$RUNTIME_DIR/web_ui.pid"

cd "$WORKSPACE" || exit 1
mkdir -p "$RUNTIME_DIR"

if /usr/bin/curl -fsS --max-time 2 "$STATUS_URL" >/dev/null 2>&1; then
  echo "Gima is already running. Opening the upgraded interface..."
  /usr/bin/open "$URL"
  exit 0
fi

if /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  LISTENER_PID="$(/usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | /usr/bin/head -n 1)"
  SAVED_PID="$(/bin/cat "$PID_PATH" 2>/dev/null | /usr/bin/tr -dc '0-9')"
  PROCESS_COMMAND="$(/bin/ps -p "$LISTENER_PID" -o command= 2>/dev/null)"
  if [[ -n "$LISTENER_PID" && "$LISTENER_PID" == "$SAVED_PID" && "$PROCESS_COMMAND" == *"human_ai.gima"* ]]; then
    echo "Cleaning up an unresponsive older Gima process..."
    /bin/kill "$LISTENER_PID" >/dev/null 2>&1 || true
    for _ in {1..30}; do
      /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1 || break
      /bin/sleep 0.2
    done
  else
    echo "Port $PORT is in use by another program, so Gima cannot start."
    echo "Close that program and double-click Start Gima again."
    echo
    read "?Press Return to close..."
    exit 1
  fi
fi

echo "Starting upgraded Gima..."
/usr/bin/screen -S gima-web -X quit >/dev/null 2>&1 || true
/usr/bin/screen -dmS gima-web /bin/zsh -lc \
  "export PATH='$PATH'; cd '$WORKSPACE' && exec /usr/bin/python3 -u -m human_ai.gima --config '$WORKSPACE/config.local.json' web --host '$HOST' --port '$PORT' >>'$LOG_PATH' 2>&1"

for _ in {1..60}; do
  if /usr/bin/curl -fsS --max-time 2 "$STATUS_URL" >/dev/null 2>&1; then
    echo "Gima is ready at $URL"
    /usr/bin/open "$URL"
    exit 0
  fi
  if ! /usr/bin/screen -ls 2>/dev/null | /usr/bin/grep -q '[.]gima-web'; then
    break
  fi
  /bin/sleep 0.5
done

echo "Gima did not finish starting. Recent log output:"
echo "------------------------------------------------"
/usr/bin/tail -n 30 "$LOG_PATH" 2>/dev/null || true
echo "------------------------------------------------"
echo "Full log: $LOG_PATH"
echo
read "?Press Return to close..."
exit 1
