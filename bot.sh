#!/bin/bash
# Gestion du bot ELYT

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/bot.log"
PID_FILE="$DIR/bot.pid"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ Bot déjà actif (PID $(cat $PID_FILE))"
        return
    fi
    pkill -9 -f "forwarder.py" 2>/dev/null
    sleep 1
    rm -f "$DIR/session_forwarder.session-journal" \
          "$DIR/session_forwarder.session-wal" \
          "$DIR/session_forwarder.session-shm" 2>/dev/null
    python3 -c "
import sqlite3
try:
    c = sqlite3.connect('$DIR/session_forwarder.session')
    c.execute('PRAGMA journal_mode=DELETE;')
    c.commit(); c.close()
except: pass
" 2>/dev/null
    caffeinate -i python3 "$DIR/forwarder.py" > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 14
    if tail -5 "$LOG" | grep -q "En écoute"; then
        echo "✅ Bot démarré"
    else
        echo "❌ Erreur au démarrage — affichage des logs :"
        tail -15 "$LOG"
    fi
}

stop() {
    pkill -9 -f "forwarder.py" 2>/dev/null
    pkill -9 -f "caffeinate" 2>/dev/null
    rm -f "$PID_FILE"
    echo "🛑 Bot arrêté"
}

status() {
    if pgrep -f "forwarder.py" > /dev/null; then
        PID=$(pgrep -f "python3.*forwarder.py" | head -1)
        UPTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
        echo "✅ Bot actif  |  PID $PID  |  Uptime $UPTIME"
        echo ""
        echo "── Dernières lignes du log ──"
        tail -8 "$LOG"
    else
        echo "🔴 Bot arrêté"
    fi
}

logs() {
    tail -f "$LOG"
}

send() {
    # Envoie le biais marché maintenant sans attendre 7h
    pkill -f "forwarder.py" 2>/dev/null; pkill -f "caffeinate" 2>/dev/null; sleep 2
    python3 -c "
import asyncio, sys
sys.path.insert(0, '$DIR')
from scheduler import send_market_bias
import config
from telethon import TelegramClient
async def main():
    c = TelegramClient('$DIR/session_forwarder', config.API_ID, config.API_HASH)
    await c.connect()
    await send_market_bias(c)
    await c.disconnect()
asyncio.run(main())
" 2>/dev/null && echo "✅ Analyse envoyée dans le groupe"
    sleep 1
    start
}

case "$1" in
    start)   start   ;;
    stop)    stop    ;;
    restart) stop; sleep 2; start ;;
    status)  status  ;;
    logs)    logs    ;;
    send)    send    ;;
    *)
        echo ""
        echo "  🤖 ELYT Bot — commandes disponibles"
        echo ""
        echo "  ./bot.sh start     → démarrer le bot"
        echo "  ./bot.sh stop      → arrêter le bot"
        echo "  ./bot.sh restart   → redémarrer"
        echo "  ./bot.sh status    → état + derniers logs"
        echo "  ./bot.sh logs      → logs en direct (Ctrl+C pour quitter)"
        echo "  ./bot.sh send      → envoyer l'analyse marché maintenant"
        echo ""
        ;;
esac
