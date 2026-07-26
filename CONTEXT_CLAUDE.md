# ELYT Bot — Contexte pour Claude Code

## C'est quoi ce projet
Bot Telegram de forwarding/signaux pour ELYT FX. Tourne en Python avec Telethon.
Dossier : `elytvipfx/` (cloné depuis https://github.com/hamzaxbenyaiche-png/elytvipfx)

## Fichiers clés
- `forwarder.py` — bot principal, écoute les canaux sources et relaie les signaux
- `scheduler.py` — envoie l'analyse du matin automatiquement à 7h (heure Paris)
- `signal_parser.py` — parse et formate les signaux en style ELYT
- `config.py` — groupes Telegram, API credentials (API_ID=2040)
- `session_audit.session` — session Telethon (auth Telegram) — NE PAS COMMITTER
- `scheduler_state.json` — état des tâches journalières (créé automatiquement)

## Lancer le bot
```bash
python forwarder.py
```
Sur Mac : `caffeinate -i python3 forwarder.py > /tmp/elyt_bot.log 2>&1 &`

## Groupes cibles
- `-5471330752` → elyt CFDs forex (groupe public)
- `-5266664273` → VIP // elyt fx
- `MORNING_TARGETS` = les deux groupes reçoivent l'analyse du matin

## Règles importantes
- Tous les messages Telegram envoyés par le bot utilisent `parse_mode='html'` (balises `<b>`, `<i>`, `<pre>`)
- Session Telethon = `'session_audit'` (pas session_audit2, pas session_forwarder)
- AnabelSignals = retiré de ALLOWED_GROUPS (commenté dans config.py)
- Signaux crypto (BTC, ETH, etc.) = ignorés automatiquement dans forwarder.py
- Après chaque modification de code → envoyer un message de confirmation dans le groupe Telegram

## Sources de données
- **Forces devises** : scraping Playwright de currencystrengthmeter.org (notes /10)
- **Biais Daily/H4** : ForexFactory (`/market/goldusd`, `/market/eurusd`, etc.)
- **Zones or XAUUSD** : ForexFactory D1 High/Low directement (pas de pivot calculé)

## Instruments suivis (scheduler.py)
```python
FF_INSTRUMENTS = [
    ('dxy', 'DXY', '💵'), ('goldusd', 'XAU/USD', '🪙'),
    ('eurusd', 'EUR/USD', '💶'), ('ndx', 'NASDAQ', '📊'), ('wtiusd', 'WTI OIL', '🛢️'),
]
```

## Filtres actifs (forwarder.py)
- Crypto (BTC/ETH/XRP...) → ignoré
- Mots blacklistés → remplacés par "elyt"
- Groupes exclus : FUNDIFY, Gold Sniper, GoldChirurgie, Formation Trading
- Résultats hebdomadaires / promos / tiktok → ignorés

## Format signal ELYT (signal_parser.py)
```
🔔 SIGNAL ELYT
BUY/SELL  ASSET
🎯 Entrée : XXXX
❌ SL : XXXX
✅ TP1 : XXXX
✅ TP2 : XXXX
⚡️ Adaptez l'entrée selon votre gestion du risque
🧿 @elytsupport
```

## Format TP touché
```
🔥 TP1 TOUCHÉ — ELYT
📌 GOLD — XAUUSD
Sécurisez vos profits selon votre money management 💰
C'est ça le travail.
🧿 @elytsupport
```
Envoyé avec GIF (tp1_hit.gif / tp2_hit.gif / tp3_hit.gif)

## Analyse du matin (scheduler.py)
- Envoyée automatiquement à 05h00 UTC (7h Paris) chaque jour
- Contient : forces devises /10, biais Daily+H4, zones or H/L, citation
- État sauvegardé dans `scheduler_state.json` (clé `YYYY-MM-DD_morning`)

## GitHub
Repo privé : https://github.com/hamzaxbenyaiche-png/elytvipfx
```bash
git add . && git commit -m "message" && git push origin main
```

## Bugs corrigés récemment
- TP1:1/TP2:2/TP3:3 → regex backtracking corrigé dans signal_parser.py (prix min 2 chiffres)
- Flèche 👉 supportée comme séparateur dans les signaux
- XAUUSD et GOLD normalisés en "GOLD — XAUUSD" dans les messages TP touché
- "Gérez" corrigé (accent) dans VIP_TEASERS
