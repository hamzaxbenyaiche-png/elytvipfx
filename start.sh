#!/bin/bash
DIR="/Users/hamzaxbench/telegram_forwarder"
cd "$DIR"

# Attend que les anciens processus se terminent vraiment
sleep 8

# Tue tout processus Python encore accroché à la session
pkill -9 -f "forwarder.py" 2>/dev/null
sleep 2

# Nettoie les fichiers de lock SQLite de la session Telethon
rm -f "$DIR/session_forwarder.session-journal" \
      "$DIR/session_forwarder.session-wal" \
      "$DIR/session_forwarder.session-shm" 2>/dev/null

# Remet le journal_mode en DELETE pour éviter le lock WAL
python3 -c "
import sqlite3, os
db = '$DIR/session_forwarder.session'
if os.path.exists(db):
    try:
        c = sqlite3.connect(db, timeout=5)
        c.execute('PRAGMA journal_mode=DELETE;')
        c.execute('PRAGMA locking_mode=NORMAL;')
        c.commit()
        c.close()
    except Exception as e:
        print('PRAGMA warning:', e)
" 2>/dev/null

exec caffeinate -i python3 "$DIR/forwarder.py"
