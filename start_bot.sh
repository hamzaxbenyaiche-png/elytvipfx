#!/bin/bash
set -e

# Decode session file from environment variable (compressed)
if [ -n "$SESSION_GZ_B64" ]; then
    echo "$SESSION_GZ_B64" | base64 -d | gunzip > session_audit.session
    echo "✅ Session Telegram restaurée"
fi

echo "🚀 Démarrage du bot ELYT..."
exec python3 forwarder.py
