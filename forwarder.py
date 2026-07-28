"""
Telegram Group Message Forwarder — ELYT
Transfère les messages vers le groupe cible en supprimant les noms propres.
"""

import asyncio
import json
import logging
import os
import re
import sys
import traceback
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, MessageMediaDocument, DocumentAttributeSticker
import config
from scheduler import run_scheduler, is_testimonial, _load_spots, _save_spots, _get_spots_shown
from signal_parser import detect_signal, detect_tp_hit, parse_signal, format_signal, log_signal

_BOT_DIR = os.path.dirname(os.path.abspath(__file__))
TP_GIFS = {
    1: os.path.join(_BOT_DIR, 'tp1_hit.gif'),
    2: os.path.join(_BOT_DIR, 'tp2_hit.gif'),
    3: os.path.join(_BOT_DIR, 'tp3_hit.gif'),
}
TP_GIF_DEFAULT = os.path.join(_BOT_DIR, 'tp_hit.gif')
TP_TARGETS = [config.TARGET_GROUP_ID, config.VIP_GROUP_ID]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

MY_USERNAME = "@elytsupport"

SIGNAL_COUNTER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signal_counter.json')

def _get_signal_count():
    try:
        with open(SIGNAL_COUNTER_FILE) as f:
            return json.load(f).get('count', 0)
    except Exception:
        return 0

def _inc_signal_count():
    count = _get_signal_count() + 1
    with open(SIGNAL_COUNTER_FILE, 'w') as f:
        json.dump({'count': count}, f)
    return count

VIP_TEASERS = [
    "⚡️ <b>CONSEIL DU JOUR</b>\n\nNe tradez jamais sans stop loss défini avant d'entrer. Pas après. Avant.\n\nLa discipline sur le SL c'est ce qui sépare ceux qui durent de ceux qui brûlent leur compte en quelques semaines.\n\nC'est ce qu'on applique sur chaque signal chez elyt.\n\n🧿 @elytsupport",

    "🔥 <b>CE QUE PERSONNE NE TE DIT SUR LE TRADING</b>\n\nLa majorité des pertes ne viennent pas de mauvais signaux. Elles viennent de la surexposition.\n\nTrader 0.01 lot sur un compte de 100€ et trader 1 lot sur un compte de 100€, c'est pas le même jeu. L'un construit, l'autre détruit.\n\nGérez votre risque. Toujours.\n\n🧿 @elytsupport",

    "🔱 <b>PSYCHOLOGIE DE TRADING</b>\n\nLe pire ennemi d'un trader c'est pas le marché. C'est lui-même.\n\nCouper ses gains trop tôt par peur. Laisser courir ses pertes par espoir. Ce pattern détruit plus de comptes que n'importe quelle analyse ratée.\n\nLaisser le plan travailler. C'est tout.\n\n🧿 @elytsupport",

    "💶 <b>POURQUOI LE BIAIS DAILY EST IMPORTANT</b>\n\nTrader en H1 contre le biais Daily c'est nager à contre-courant.\n\nOn peut gagner quelques trades comme ça. Mais sur la durée, le Daily gagne toujours. Chaque matin chez elyt on commence par là — lire le marché avant de l'attaquer.\n\n🧿 @elytsupport",

    "♾️ <b>LA PATIENCE EST UNE POSITION</b>\n\nNe pas trader c'est aussi une décision.\n\nQuand le marché n'est pas clair, quand les signaux se contredisent, quand la liquidité est faible — rester en dehors c'est protéger son capital. Les meilleures semaines sont souvent celles où on a su attendre le bon setup.\n\n🧿 @elytsupport",
]

# Messages Financial Juice haute priorité uniquement
FJ_RED = re.compile(
    r'🚨|BREAKING|ALERT|WARNING|URGENT|FLASH|RED|CRITICAL|MAJOR|SURPRISE|SHOCK|UNEXPECT|ABOVE EXPECT|BELOW EXPECT|BEATS|MISSES|EXCEEDS',
    re.IGNORECASE
)


def is_video_message(text: str, media) -> bool:
    if text and re.search(r'youtube\.com|youtu\.be', text, re.IGNORECASE):
        return True
    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if hasattr(doc, 'mime_type') and doc.mime_type in ('video/mp4', 'video/mpeg', 'video/webm', 'video/quicktime'):
            return True
    return False


def is_competitor_media(caption: str) -> bool:
    """Retourne True si l'image fait de la pub pour un concurrent (blacklist ou lien t.me)."""
    if not caption:
        return False
    for word in config.BLACKLIST:
        if word.lower() in caption.lower():
            return True
    # Liens directs vers d'autres groupes Telegram
    if re.search(r'\bFTG\b|formation.*trading|t\.me/', caption, re.IGNORECASE):
        return True
    return False


def replace_preserve_case(match):
    original = match.group(0)
    if original.isupper():
        return 'ELYT'
    elif original[0].isupper():
        return 'Elyt'
    else:
        return 'ELYT'


def clean_message(text: str) -> str:
    if not text or not text.strip():
        return text

    # Supprime les liens YouTube entiers
    text = re.sub(r'https?://(www\.)?(youtube\.com|youtu\.be)\S*', '', text, flags=re.IGNORECASE)

    # Supprime les liens markdown [texte](url)
    text = re.sub(r'\[[^\]]*\]\(https?://\S+\)', '', text)
    text = re.sub(r'\[[^\]]*\]\(t\.me/\S+\)', '', text)

    # Supprime les attributions ([Tweet] ([Reuters] (CoinDesk) > X: > Reuters: etc.
    text = re.sub(r'\(\[[^\]]{1,40}\]', '', text)
    text = re.sub(r'\([A-Z][a-zA-Z\s]{1,20}\)', '', text)
    text = re.sub(r'^\s*>\s*\w[\w\s]*:\s*', '', text, flags=re.MULTILINE)

    # Supprime les liens
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r't\.me/\S+', '', text)

    # Remplace les @mentions concurrentes par @elytsupport (une seule passe)
    text = re.sub(r'@(?!elytsupport)\w+', '@elytsupport', text)

    # Supprime les tags Financial Juice ($MACRO|FJ, etc.)
    text = re.sub(r'\$[A-Z]+\s*\|?\s*FJ\b', '', text)
    text = re.sub(r'\$[A-Z]+\s*\|\s*@\w+', '', text)
    text = re.sub(r'\s*\|\s*FJ\b', '', text)

    # Remplace les noms de la blacklist en respectant la casse
    for word in config.BLACKLIST:
        text = re.sub(re.escape(word), replace_preserve_case, text, flags=re.IGNORECASE)

    # "xauelyt" ou "xau ELYT" → "ELYT" (pseudo concurrent xaubara)
    text = re.sub(r'xau\s*ELYT', 'ELYT', text, flags=re.IGNORECASE)

    # Nettoie le markdown cassé (** ou __ orphelins)
    for marker in ['**', '__', '~~']:
        if text.count(marker) % 2 != 0:
            text = text.replace(marker, '')

    # Supprime les | résiduels et parenthèses/crochets orphelins en fin de message
    text = re.sub(r'\s*\|\s*', ' ', text)
    text = re.sub(r'[\(\[]\s*$', '', text)

    # Nettoie les espaces doubles et lignes vides en excès
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


async def main():
    client = TelegramClient('session_audit', config.API_ID, config.API_HASH)

    @client.on(events.NewMessage(outgoing=True, pattern=r'^/spots\s+(\d+)$'))
    async def cmd_spots(event):
        """Commande admin : /spots 14 → met à jour les places disponibles."""
        try:
            n = int(event.pattern_match.group(1))
            spots = _load_spots()
            spots['available'] = n
            _save_spots(spots)
            await event.reply(f"✅ Places VIP mises à jour : <b>{n} places</b> disponibles.", parse_mode='html')
            log.info(f"[SPOTS] Mis à jour manuellement → {n} places")
        except Exception as e:
            log.error(f"[SPOTS CMD] Erreur: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r'^/spots$'))
    async def cmd_spots_show(event):
        """Commande admin : /spots → affiche le statut actuel."""
        try:
            spots = _load_spots()
            n = spots.get('available', 0)
            cap = spots.get('monthly_cap', 20)
            joined = spots.get('joined_this_month', 0)
            await event.reply(
                f"📊 <b>Statut places ELYT FOREX VIP</b>\n\n"
                f"Disponibles : <b>{n}</b>\n"
                f"Cap ce mois : <b>{cap}</b>\n"
                f"Rejoints ce mois : <b>{joined}</b>",
                parse_mode='html'
            )
        except Exception as e:
            log.error(f"[SPOTS CMD] Erreur: {e}")

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            chat = await event.get_chat()
            chat_id = event.chat_id

            def normalize(cid):
                s = str(cid)
                return int(s) if s.startswith('-100') else int('-100' + s.lstrip('-'))

            chat_ids = {chat_id, normalize(chat_id)}

            if config.TARGET_GROUP_ID in chat_ids:
                return
            if not isinstance(chat, (Channel, Chat)):
                return
            if chat_ids & set(config.EXCLUDED_GROUPS):
                return
            if config.ALLOWED_GROUPS and not (chat_ids & set(config.ALLOWED_GROUPS)):
                return

            chat_title = getattr(chat, 'title', '')
            raw_text = event.message.text or ''
            is_alert = bool(chat_ids & set(config.ALERT_GROUPS))
            is_vip_source = bool(chat_ids & set(config.VIP_SIGNAL_SOURCES))

            # Sources VIP (NABIL + Hunt Money) : signaux uniquement → groupe VIP
            if is_vip_source:
                if not raw_text:
                    return
                if not detect_signal(raw_text):
                    return
                parsed = parse_signal(raw_text)
                if parsed and (parsed.get('entry') or parsed.get('sl')) and parsed.get('tps') and parsed.get('asset') != '📊 ASSET':
                    msg = format_signal(parsed)
                    log_signal(parsed)
                    await client.send_message(config.VIP_GROUP_ID, msg)
                    log.info(f"[VIP SIGNAL] {parsed['direction']} {parsed['asset']} ({chat_title})")
                return

            # Financial Juice : ignore les messages non-urgents
            if is_alert and not FJ_RED.search(raw_text):
                return

            # Ignore vidéos YouTube et mp4
            if is_video_message(raw_text, event.message.media):
                log.info(f"[SKIP] Vidéo ignorée ({chat_title})")
                return

            # Ignore témoignages membres
            if is_testimonial(raw_text):
                log.info(f"[SKIP] Témoignage ignoré ({chat_title})")
                return

            # Ignore mentions de live / TikTok
            if re.search(r'tiktok|tik tok|live\s+tiktok|tiktok\s+live|@\w+\s+sur\s+tiktok|je\s+suis\s+en\s+live|en\s+live\s+sur|rdv\b.*\blive\b|\blive\b.*\brdv\b', raw_text, re.IGNORECASE):
                log.info(f"[SKIP] TikTok ignoré ({chat_title})")
                return

            # Ignore signaux crypto (BTC, ETH, XRP, etc.)
            if re.search(r'\b(BTC|ETH|XRP|SOL|BNB|DOGE|ADA|LTC|DOT|AVAX|MATIC|LINK|UNI|SHIB|USDT|USDC)[\s/USD]', raw_text, re.IGNORECASE):
                log.info(f"[SKIP] Signal crypto ignoré ({chat_title})")
                return

            # Ignore résultats hebdo (WIN/LOSS/pips) et promo propfirm/robot
            if re.search(r'weekly\s+vip\s+results|weekly\s+results|\+\d+\s*pips\s+win|\bnet\s+win\b', raw_text, re.IGNORECASE):
                log.info(f"[SKIP] Weekly results ignoré ({chat_title})")
                return
            if re.search(r'propfirm|prop\s*firm|robot\s+de\s+trading|ea\s+robot|on\s+n.a\s+pas\s+de\s+robot|promo.*code|code\s*:\s*\w+', raw_text, re.IGNORECASE):
                log.info(f"[SKIP] Promo propfirm/robot ignoré ({chat_title})")
                return

            if event.message.media:
                # Sticker → re-envoyer directement
                if isinstance(event.message.media, MessageMediaDocument):
                    doc = event.message.media.document
                    if any(isinstance(attr, DocumentAttributeSticker) for attr in getattr(doc, 'attributes', [])):
                        await client.send_file(config.TARGET_GROUP_ID, doc)
                        log.info(f"[STICKER] Envoyé ({chat_title})")
                        return
                # Image avec texte → on envoie uniquement le texte (sans l'image concurrente)
                if raw_text and not is_competitor_media(raw_text):
                    pass  # tombe dans le bloc texte ci-dessous
                else:
                    return  # image sans texte ou pub concurrente → ignorée

            if raw_text:
                # TP touché → GIF ELYT dans les deux groupes
                if not is_alert:
                    tp_info = detect_tp_hit(raw_text)
                    if tp_info and tp_info.get('tp_num'):
                        tp_num = tp_info['tp_num']
                        asset = tp_info.get('asset') or ''
                        pair = tp_info.get('pair') or ''
                        pair_line = f"📌 {pair}\n" if pair else ''
                        caption = (
                            f"🔥 <b>TP{tp_num} TOUCHÉ — ELYT</b>\n\n"
                            f"{pair_line}"
                            f"Sécurisez vos profits selon votre money management 💰\n"
                            f"<i>C'est ça le travail.</i>\n\n"
                            f"🧿 @elytsupport"
                        )
                        gif_path = TP_GIFS.get(tp_num, TP_GIF_DEFAULT)
                        if not os.path.exists(gif_path):
                            gif_path = TP_GIF_DEFAULT
                        for gid in TP_TARGETS:
                            try:
                                await client.send_file(gid, gif_path, caption=caption, parse_mode='html')
                            except Exception as e:
                                log.error(f"[TP HIT] Erreur groupe {gid}: {e}")
                        log.info(f"[TP HIT] TP{tp_num} {pair} → {len(TP_TARGETS)} groupe(s)")
                        return

                # Signal de trading → format ELYT uniforme → groupe public + VIP
                if not is_alert and detect_signal(raw_text):
                    parsed = parse_signal(raw_text)
                    if parsed and (parsed.get('entry') or parsed.get('sl')) and parsed.get('tps') and parsed.get('asset') != '📊 ASSET':
                        msg = format_signal(parsed)
                        log_signal(parsed)
                        for gid in [config.TARGET_GROUP_ID, config.VIP_GROUP_ID]:
                            await client.send_message(gid, msg, parse_mode='html')
                        log.info(f"[SIGNAL] {parsed['direction']} {parsed['asset']} ({chat_title})")
                        count = _inc_signal_count()
                        if count % 5 == 0:
                            teaser = VIP_TEASERS[(count // 5 - 1) % len(VIP_TEASERS)]
                            await client.send_message(config.TARGET_GROUP_ID, teaser, parse_mode='html')
                            log.info(f"[TEASER VIP] Envoyé après {count} signaux")
                        return

                # Alertes Financial Juice uniquement — tout autre message non-signal est ignoré
                if is_alert:
                    cleaned = clean_message(raw_text)
                    if cleaned:
                        cleaned = f"⚡️ <b>ALERTE MARCHÉ — ELYT</b>\n\n{cleaned}"
                        await client.send_message(config.TARGET_GROUP_ID, cleaned, parse_mode='html')
                        log.info(f"[ALERTE] {chat_title} → envoyé")
                else:
                    log.info(f"[SKIP] Message non-signal ignoré ({chat_title})")

        except Exception as e:
            log.error(f"[ERREUR] {e}\n{traceback.format_exc()}")

    log.info("=== Démarrage forwarder ELYT ===")
    await client.connect()

    if not await client.is_user_authorized():
        log.error("❌ Session non autorisée.")
        return

    log.info("✅ Connecté à Telegram")
    target = await client.get_entity(config.TARGET_GROUP_ID)
    log.info(f"🎯 Groupe cible : {target.title}")
    log.info("📡 En écoute")

    await asyncio.gather(
        client.run_until_disconnected(),
        run_scheduler(client),
    )


if __name__ == '__main__':
    # Verrou exclusif : une seule instance à la fois (compatible Mac + Windows)
    _lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.forwarder.lock')
    try:
        if sys.platform == 'win32':
            import msvcrt
            _lock_fd = open(_lock_path, 'w')
            _lock_fd.write('lock')
            _lock_fd.flush()
            _lock_fd.seek(0)
            try:
                msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_NBLCK, 4)
            except OSError:
                print("❌ Une instance est déjà en cours. Arrêt.")
                raise SystemExit(0)
        else:
            import fcntl
            _lock_fd = open(_lock_path, 'w')
            try:
                fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                print("❌ Une instance est déjà en cours. Arrêt.")
                raise SystemExit(0)
    except SystemExit:
        raise
    except Exception:
        pass  # Si le verrou échoue pour une autre raison, on continue quand même
    asyncio.run(main())
