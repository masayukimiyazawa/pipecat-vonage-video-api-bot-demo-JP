#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLOUDFLARED_LOG="/tmp/cloudflared.log"
ENV_FILE="$SCRIPT_DIR/.env"

echo "=== Starting cloudflared tunnel ==="

# Kill existing cloudflared
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

# Start cloudflared in background
cloudflared tunnel --url http://localhost:8005 > "$CLOUDFLARED_LOG" 2>&1 &
CLOUDFLARED_PID=$!
echo "cloudflared PID: $CLOUDFLARED_PID"

# Wait for the tunnel URL to appear in logs
TUNNEL_URL=""
echo "Waiting for tunnel URL..."
for i in $(seq 1 30); do
    # Improved grep to find the URL more reliably
    TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$CLOUDFLARED_LOG" | head -n 1 || true)
    if [ -n "$TUNNEL_URL" ]; then
        echo "Found URL: $TUNNEL_URL"
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "Failed to get tunnel URL. Last 10 lines of cloudflared log:"
    tail -n 10 "$CLOUDFLARED_LOG"
    exit 1
fi

echo "Tunnel URL: $TUNNEL_URL"

# Update .env
WS_URI="wss://${TUNNEL_URL#https://}/ws"
if grep -q "^WS_URI=" "$ENV_FILE"; then
    sed -i '' "s|^WS_URI=.*|WS_URI=$WS_URI|" "$ENV_FILE"
else
    echo "WS_URI=$WS_URI" >> "$ENV_FILE"
fi
echo "Updated .env: WS_URI=$WS_URI"

# Restart server
echo "=== Restarting server ==="
# Kill anything listening on 8005
fuser -k 8005/tcp || lsof -ti:8005 | xargs kill -9 2>/dev/null || true
sleep 2

cd "$SCRIPT_DIR" && nohup .venv/bin/python3 server.py > /tmp/server.log 2>&1 &
echo "Server PID: $!"
sleep 3

if curl -s http://localhost:8005/health > /dev/null; then
    echo "Server is UP!"
else
    echo "Server failed to start. Check /tmp/server.log"
    tail -n 20 /tmp/server.log
    exit 1
fi

echo "=== Done ==="
echo "Open https://${TUNNEL_URL#https://} in your browser"
