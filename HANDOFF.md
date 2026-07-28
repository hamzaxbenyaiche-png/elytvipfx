# ELYT Bot — Handoff complet (28/07/2026)

## Projet
Bot Telegram de forwarding/signaux ELYT FX.
- **Repo GitHub** : https://github.com/hamzaxbenyaiche-png/elytvipfx (public)
- **Dossier Mac** : `/Users/hamzaxbench/Projets/telegram_forwarder/`
- **Compte Telegram** : hamzaxbenyaiche@gmail.com
- **API_ID** : 2040 | **API_HASH** : b18441a1ff607e10a989891a5462e627

## Lancer le bot (Mac)
```bash
cd /Users/hamzaxbench/Projets/telegram_forwarder
caffeinate -i python3 forwarder.py > /tmp/elyt_bot.log 2>&1 &
```
Session Telethon : `session_audit` (fichier `session_audit.session`)

## Fichiers clés
- `forwarder.py` — bot principal, écoute + relaie signaux
- `scheduler.py` — analyse du matin 7h Paris, killzones, relances VIP
- `signal_parser.py` — parse/formate signaux en style ELYT
- `config.py` — IDs groupes, credentials (API_ID=2040)
- `scheduler_state.json` — état tâches journalières (auto-créé)

## Groupes cibles
- `-5471330752` → elyt CFDs forex (public)
- `-5266664273` → VIP // elyt fx
- `MORNING_TARGETS` = les deux

## Sources de données
- **Forces devises** : Playwright → currencystrengthmeter.org (notes /10)
- **Biais Daily/H4** : httpx → ForexFactory (/market/goldusd etc.)
- **Zones XAUUSD** : ForexFactory D1 High/Low direct

## Ce qui tourne automatiquement (scheduler.py)
| Heure Paris | Tâche |
|-------------|-------|
| 2h00 | Asian Killzone (seulement entre 2h-5h) |
| 7h00 | Analyse du matin (biais + forces + zones or) |
| 8h00 | London Killzone + Citation islamique |
| 11h/15h/19h/23h | Mise à jour H4 (edit message existant) |
| 13h00 | New York Killzone |
| 18h00 | Relance places VIP |
| 19h00 vendredi | Bilan hebdo |
| 20h00 | Citation islamique soir |
| 10h00 samedi | Message communauté week-end |
| 10h 1er du mois | Relance mensuelle |

## Règles importantes
- `parse_mode='html'` partout (`<b>`, `<i>`, `<pre>`) — jamais markdown
- Session = `'session_audit'` (pas session_audit2)
- Après chaque modif → envoyer message confirmation dans le groupe
- AnabelSignals retiré (commenté dans config.py)
- Signaux crypto (BTC/ETH…) ignorés automatiquement

## Filtres actifs (forwarder.py)
- Crypto BTC/ETH/XRP... → skip
- TikTok/live → skip
- Weekly results / propfirm → skip
- Témoignages → skip
- Noms blacklistés → remplacés par "elyt"
- Sources exclues : FUNDIFY, Gold Sniper, GoldChirurgie, Formation Trading

## Format signal ELYT
```
🔔 SIGNAL ELYT
BUY/SELL  ASSET
🎯 Entrée : XXXX
❌ SL : XXXX
✅ TP1 : XXXX
⚡️ Adaptez l'entrée selon votre gestion du risque
🧿 @elytsupport
```

## Format TP touché
```
🔥 TP{n} TOUCHÉ — ELYT
📌 GOLD — XAUUSD
Sécurisez vos profits selon votre money management 💰
C'est ça le travail.
🧿 @elytsupport
```
+ GIF correspondant (tp1_hit.gif / tp2_hit.gif / tp3_hit.gif)

## Bugs corrigés (cette session)
1. TP1:1/TP2:2/TP3:3 → regex backtracking corrigé (prix min 2 chiffres)
2. Flèche 👉 supportée comme séparateur dans les signaux
3. XAUUSD et GOLD → normalisés en "GOLD — XAUUSD"
4. "Gérez" → accent corrigé dans VIP_TEASERS
5. "Sécurisez vos profits selon votre money management 💰"
6. Crash Windows (`fcntl`) → fix cross-platform
7. Crash Python 3.10+ (`get_event_loop`) → `get_running_loop()`
8. Fichiers JSON sécurisés (`with open()`)
9. GIFs TP différenciés par numéro
10. Pas d'analyse le week-end (marchés fermés)
11. Analyse bloquée si données manquantes
12. Asian Killzone : plus de spam au redémarrage
13. Faux winrate supprimé du bilan

## Git
```bash
git add -A && git commit -m "message" && git push origin main
```
Token GitHub configuré — pas besoin de login.

## Pour continuer sur un autre ordi
1. `git clone https://github.com/hamzaxbenyaiche-png/elytvipfx`
2. Copier `session_audit.session` depuis Mac (dans Saved Messages Telegram — ZIP envoyé)
3. `pip install -r requirements.txt`
4. `python3 -m playwright install chromium`
5. `python forwarder.py`
