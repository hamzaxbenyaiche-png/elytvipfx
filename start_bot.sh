#!/bin/bash
set -e

# Decode session file from environment variable (compressed)
if [ -n "$SESSION_GZ_B64" ]; then
    echo "$SESSION_GZ_B64" | base64 -d | gunzip > session_audit.session
    echo "✅ Session Telegram restaurée"
fi

# libstdc++ n'est pas résolu via RPATH pour les extensions C Python (ex: greenlet,
# dépendance de Playwright) — expose le chemin Nix réel, calculé au démarrage
# car le hash du store change à chaque build.
_stdcxx=$(find /nix/store -maxdepth 3 -name 'libstdc++.so.6' 2>/dev/null | head -1)
if [ -n "$_stdcxx" ]; then
    export LD_LIBRARY_PATH="$(dirname "$_stdcxx")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

echo "🚀 Démarrage du bot ELYT..."
exec python3 forwarder.py
