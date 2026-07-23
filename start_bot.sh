#!/bin/bash
set -e

# Decode session file from environment variable
if [ -n "$SESSION_B64" ]; then
    echo "$SESSION_B64" | base64 -d > session_audit.session
    echo "✅ Session Telegram restaurée"
fi

# Install Playwright browsers if needed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "📦 Installation Chromium..."
    python3 -m playwright install chromium
    python3 -m playwright install-deps chromium 2>/dev/null || true
fi

echo "🚀 Démarrage du bot ELYT..."
exec python3 forwarder.py
