"""
Détection et reformatage des signaux de trading en format ELYT uniforme.
Suivi automatique pour le bilan hebdomadaire.
"""

import re
import json
import os
from datetime import datetime, timezone

SIGNAL_FILE = "/Users/hamzaxbench/telegram_forwarder/signals_log.json"

ASSET_MAP = {
    'XAUUSD': '🪙 GOLD — XAUUSD',
    'GOLD':   '🪙 GOLD — XAUUSD',
    'XAGUSD': '🥈 SILVER — XAGUSD',
    'SILVER': '🥈 SILVER — XAGUSD',
    'EURUSD': '💶 EUR/USD',
    'GBPUSD': '💷 GBP/USD',
    'USDJPY': '💴 USD/JPY',
    'USDCHF': '🇨🇭 USD/CHF',
    'AUDUSD': '🇦🇺 AUD/USD',
    'USDCAD': '🇨🇦 USD/CAD',
    'NZDUSD': '🇳🇿 NZD/USD',
    'GBPJPY': '💷 GBP/JPY',
    'EURJPY': '💶 EUR/JPY',
    'NASDAQ': '📊 NASDAQ',
    'NAS100': '📊 NASDAQ',
    'US30':   '📊 US30 — DOW JONES',
    'SP500':  '📊 S&P 500',
    'OIL':    '🛢️ OIL — WTI',
    'USOIL':  '🛢️ OIL — WTI',
    'BTC':    '₿ BITCOIN',
    'BTCUSD': '₿ BITCOIN',
    'ETH':    '⟠ ETHEREUM',
    'DXY':    '📊 DXY',
    'GBPAUD': '💷 GBP/AUD',
    'NZDCHF': '🇳🇿 NZD/CHF',
    'GBPCAD': '💷 GBP/CAD',
    'EURGBP': '💶 EUR/GBP',
    'CHFJPY': '🇨🇭 CHF/JPY',
    'EURAUD': '💶 EUR/AUD',
    'AUDCAD': '🇦🇺 AUD/CAD',
    'CADJPY': '🇨🇦 CAD/JPY',
    'EURCHF': '💶 EUR/CHF',
    'AUDJPY': '🇦🇺 AUD/JPY',
    'GBPCHF': '💷 GBP/CHF',
    'NZDJPY': '🇳🇿 NZD/JPY',
    'CADCHF': '🇨🇦 CAD/CHF',
    'EURNZD': '💶 EUR/NZD',
    'GBPNZD': '💷 GBP/NZD',
    'AUDNZD': '🇦🇺 AUD/NZD',
}

DIRECTION_ICON = {'BUY': '📈', 'SELL': '📉'}


def detect_tp_hit(text: str):
    """Retourne {tp_num, asset} si le message annonce un TP touché, sinon None."""
    if not text:
        return None
    t = text.upper()
    # Détecte TP HIT / TOUCHÉ / CHECKED / SECURED / DELIVERED / SMASHED / ✅
    m = re.search(r'TP\s*(\d+)\s*(?:HIT|TOUCH[EÉ]|CHECKED|SECURED|DELIVERED|SMASHED|BANKED|LOCKED|✅)', t)
    if not m:
        # Cas "TP1 ✅" ou "✅ TP1" — nécessite que ✅ soit réellement présent
        m = re.search(r'(?:✅\s*TP\s*(\d+)|TP\s*(\d+)\s*✅)', t)
        if m:
            m = type('M', (), {'group': lambda self, n: m.group(1) or m.group(2)})()
    if not m:
        return None
    tp_num = int(m.group(1))

    # Trouve la paire et normalise son nom d'affichage (XAUUSD et GOLD → même libellé)
    pair = None
    for key in sorted(ASSET_MAP.keys(), key=len, reverse=True):
        if key in t:
            pair = re.sub(r'^(?:[\U0001F1E0-\U0001F1FF]{2}|[\U00010000-\U0010ffff☀-⛿✀-➿])\s*', '', ASSET_MAP[key])
            break

    return {'tp_num': tp_num, 'pair': pair}


def detect_signal(text: str) -> bool:
    """Retourne True si le message ressemble à un signal de trading entrant."""
    if not text:
        return False
    t = text.upper()
    # Exclure les résultats de trades (TP HIT, +X points, pips gagnés)
    if re.search(r'TP\s*\d*\s*HIT|TP\s*\d*\s*TOUCHÉ|TP\s*\d*\s*CHECKED|(?<!\w)\+\d+\s*(POINTS?|PIPS?)\b', t):
        return False
    has_direction = bool(re.search(r'\b(BUY|SELL|ACHAT|VENTE|LONG|SHORT)\b', t))
    has_price = bool(re.search(r'\b(ENTRY|ENTR[EÉ]E|PE\b|SL\b|STOP|TP\s*\d|TAKE\s*PROFIT|TARGET|ENTRY\s*(POINT|LEVEL)|ENTRY\s*ZONE)\b', t))
    has_numbers = len(re.findall(r'\b\d{3,5}\.?\d*\b', t)) >= 2
    return has_direction and (has_price or has_numbers)


def _expand_range(entry: str) -> str:
    """Expand '4130-35' → '4130-4135'."""
    clean = entry.replace(' ', '')
    m = re.match(r'^(\d+)[-–](\d{2,3})$', clean)
    if m:
        base, suffix = m.group(1), m.group(2)
        return f"{base}-{base[:-len(suffix)]+suffix}"
    return entry


def _clean_price(p: str) -> str:
    """Retire les annotations parasites d'un prix: '4234.60(-50 pips)' → '4234.60'"""
    return re.match(r'[\d.,]+', p).group(0) if re.match(r'[\d.,]+', p) else p


def parse_signal(text: str):
    """Parse un signal et retourne un dict structuré, ou None si pas parseable."""
    if not text:
        return None
    t = text.upper()

    # Détection swing trade
    is_swing = bool(re.search(r'\bswing\b', text, re.IGNORECASE))

    # Direction — inclut "Bias - Bearish/Bullish" et "Fall Expected"
    direction_match = re.search(r'\b(BUY|SELL|ACHAT|VENTE|LONG|SHORT)\b', t)
    if not direction_match:
        if re.search(r'\bBEARISH\b|FALL\s*EXPECT', t):
            direction = 'SELL'
            direction_match = type('M', (), {'end': lambda self: 0, 'group': lambda self, n: 'SELL'})()
        elif re.search(r'\bBULLISH\b|RISE\s*EXPECT|MOVE\s*UP', t):
            direction = 'BUY'
            direction_match = type('M', (), {'end': lambda self: 0, 'group': lambda self, n: 'BUY'})()
        else:
            return None
    else:
        raw_dir = direction_match.group(1)
        direction = 'BUY' if raw_dir in ('BUY', 'ACHAT', 'LONG') else 'SELL'

    # Asset
    asset = None
    for key in sorted(ASSET_MAP.keys(), key=len, reverse=True):
        if key in t:
            asset = ASSET_MAP[key]
            break
    if not asset:
        # Cherche d'abord un hashtag #XXXX en début de message (ex: EliteTrading, UnitedSignals)
        tag = re.search(r'#([A-Z]{6})\b', t)
        if tag and tag.group(1) in ASSET_MAP:
            asset = ASSET_MAP[tag.group(1)]
        else:
            after = t[direction_match.end():direction_match.end()+30].strip()
            word = re.match(r'[\w/]+', after)
            candidate = word.group(0).upper() if word else ''
            # Filtre les mots parasites
            BAD_WORDS = {'FROM','TRADING','LONG','SHORT','BUY','SELL','THE','A','IN','ON','AT','HERE','NOW'}
            if candidate and candidate not in BAD_WORDS:
                asset = ASSET_MAP.get(candidate, f"📊 {candidate}")
            else:
                asset = "📊 ASSET"

    # Entry — supporte: ENTRY, ENTRÉE, PE, ENTRY POINT, ENTRY LEVEL, ENTRY ZONE,
    #          CURRENT PRICE (AnabelSignals), "trading on X pivot level"
    entry = None
    PRICE_RE = r'(\d[\d.,]*\s*[-–]\s*\d[\d.,]*|\d[\d.,]*)'
    entry_match = re.search(
        r'(?:ENTRY(?:\s*(?:POINT|LEVEL|ZONE))?|ENTR[EÉ]E|PE|CURRENT\s*PRICE|KEY\s*LEVEL)\s*[:\-]?\s*(?:👉|➡️|→)?\s*\n?' + PRICE_RE,
        t
    )
    if not entry_match:
        # "coiling around X" / "trading on X pivot"
        entry_match = re.search(r'(?:TRADING\s+ON|COILING\s+AROUND|AROUND)\s+([\d.,]+)', t)
    if entry_match:
        entry = _expand_range(entry_match.group(1).strip())
    else:
        # Cherche une plage de prix sur une ligne seule (ex: "4118-4123")
        range_match = re.search(r'^\s*([\d]{4,5}\.?\d*)\s*[-–]\s*([\d]{4,5}\.?\d*)\s*$', t, re.MULTILINE)
        if range_match:
            entry = f"{range_match.group(1)}-{range_match.group(2)}"
        else:
            single = re.search(r'^\s*([\d]{4,5}\.?\d*)\s*$', t, re.MULTILINE)
            if single:
                entry = single.group(1)

    # Stop Loss — SL, STOP LOSS, STOP
    sl = None
    sl_match = re.search(r'(?:SL|STOP\s*LOSS|STOP)\s*[:\-]?\s*(?:👉|➡️|→)?\s*(\d{2,}[\d.,]*)', t)
    if sl_match:
        sl = _clean_price(sl_match.group(1))

    # Take Profits — TP1/TP 1/TAKE PROFIT/TARGET LEVEL/TARGET/GOAL
    tps = []
    for tp_match in re.finditer(r'TP\s*\d*\s*[:\-]?\s*(?:👉|➡️|→)?\s*(\d{2,}[\d.,]*)', t):
        val = _clean_price(tp_match.group(1))
        if val not in tps:
            tps.append(val)
    if not tps:
        for match in re.finditer(r'TAKE\s*(?:PROFIT)?\s*\d*\s*[:\-]?\s*(?:👉|➡️|→)?\s*(\d{2,}[\d.,]*)', t):
            val = _clean_price(match.group(1))
            if val not in tps:
                tps.append(val)
    if not tps:
        for match in re.finditer(r'(?:TARGET(?:\s*LEVEL)?|GOAL)\s*\d*\s*[:\-]?\s*(?:👉|➡️|→)?\s*(\d{2,}[\d.,]*)', t):
            val = _clean_price(match.group(1))
            if val not in tps:
                tps.append(val)

    return {
        'direction': direction,
        'asset': asset,
        'entry': entry,
        'sl': sl,
        'tps': tps,
        'swing': is_swing,
    }


def format_signal(parsed: dict) -> str:
    """Formate un signal parsé en message ELYT propre."""
    direction = parsed['direction']
    icon = DIRECTION_ICON.get(direction, '📊')
    asset = parsed['asset']
    entry = parsed.get('entry')
    sl = parsed.get('sl')
    tps = list(parsed.get('tps', []))

    sl_be = None

    if len(tps) >= 4:
        sl_be = tps[0]
        tps = tps[1:4]
    elif len(tps) > 3:
        tps = tps[:3]

    asset_clean = re.sub(r'^(?:[\U0001F1E0-\U0001F1FF]{2}|[\U00010000-\U0010ffff☀-⛿✀-➿])\s*', '', asset)

    lines = [
        "🔔 SIGNAL ELYT",
        "",
        f"{direction}  {asset_clean}",
        "",
    ]

    if entry:
        lines.append(f"🎯 Entrée : {entry}")
        lines.append("")
    if sl:
        lines.append(f"❌ SL : {sl}")
    if sl_be:
        lines.append(f"🔒 SL BE : {sl_be}")
    if tps:
        lines.append("")
    for i, tp in enumerate(tps, 1):
        lines.append(f"✅ TP{i} : {tp}")

    swing_tag = "\n#SWING" if parsed.get('swing') else ""

    lines += [
        "",
        "⚡️ Adaptez l'entrée selon votre gestion du risque",
        f"🧿 @elytsupport{swing_tag}",
    ]

    return "\n".join(lines)


def log_signal(parsed: dict):
    """Enregistre le signal dans le fichier de suivi pour le bilan."""
    try:
        logs = []
        if os.path.exists(SIGNAL_FILE):
            with open(SIGNAL_FILE, 'r') as f:
                logs = json.load(f)
        logs.append({
            'date': datetime.now(timezone.utc).isoformat(),
            'direction': parsed['direction'],
            'asset': parsed['asset'],
            'tps_count': len(parsed.get('tps', [])),
        })
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(logs, f)
    except Exception:
        pass


def get_week_stats() -> dict:
    """Retourne les stats de la semaine en cours."""
    try:
        if not os.path.exists(SIGNAL_FILE):
            return {'signals': 0, 'tps': 0}
        with open(SIGNAL_FILE, 'r') as f:
            logs = json.load(f)
        now = datetime.now(timezone.utc)
        # Lundi de cette semaine
        monday = now - __import__('datetime').timedelta(days=now.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        week_logs = [
            l for l in logs
            if datetime.fromisoformat(l['date']) >= monday
        ]
        return {
            'signals': len(week_logs),
            'tps': sum(l.get('tps_count', 0) for l in week_logs),
        }
    except Exception:
        return {'signals': 0, 'tps': 0}
