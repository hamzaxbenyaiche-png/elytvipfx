"""
Rattrapage des messages manqués — à lancer manuellement.
Récupère les N dernières heures depuis tous les groupes autorisés.
"""
import asyncio
import sys
import re
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, MessageMediaDocument, DocumentAttributeSticker

sys.path.insert(0, '/Users/hamzaxbench/telegram_forwarder')
import config
from forwarder import clean_message, is_video_message, is_competitor_media, replace_preserve_case
from scheduler import is_testimonial
from signal_parser import detect_signal, parse_signal, format_signal, log_signal

FJ_RED = re.compile(
    r'🚨|BREAKING|ALERT|WARNING|URGENT|FLASH|RED|CRITICAL|MAJOR|SURPRISE|SHOCK|UNEXPECT|ABOVE EXPECT|BELOW EXPECT|BEATS|MISSES|EXCEEDS',
    re.IGNORECASE
)

async def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    print(f"⏱ Rattrapage depuis {hours}h — après {since.strftime('%H:%M')} UTC")

    client = TelegramClient('session_forwarder', config.API_ID, config.API_HASH)
    await client.connect()

    total = 0
    skipped = 0

    for group_id in config.ALLOWED_GROUPS:
        try:
            entity = await client.get_entity(group_id)
            title = getattr(entity, 'title', str(group_id))
            is_alert = group_id in config.ALERT_GROUPS

            msgs = []
            async for msg in client.iter_messages(entity, limit=50):
                if msg.date < since:
                    break
                msgs.append(msg)

            msgs.reverse()  # ordre chronologique

            for msg in msgs:
                raw_text = msg.text or ''

                if is_alert and not FJ_RED.search(raw_text):
                    skipped += 1
                    continue
                if is_video_message(raw_text, msg.media):
                    skipped += 1
                    continue
                if is_testimonial(raw_text):
                    skipped += 1
                    continue

                if msg.media:
                    if isinstance(msg.media, MessageMediaDocument):
                        doc = msg.media.document
                        if any(isinstance(a, DocumentAttributeSticker) for a in getattr(doc, 'attributes', [])):
                            await client.send_file(config.TARGET_GROUP_ID, doc)
                            total += 1
                            print(f"  🎭 sticker ({title})")
                            await asyncio.sleep(1)
                            continue
                    if raw_text and not is_competitor_media(raw_text):
                        pass
                    else:
                        skipped += 1
                        continue

                if raw_text:
                    if not is_alert and detect_signal(raw_text):
                        parsed = parse_signal(raw_text)
                        if parsed:
                            out = format_signal(parsed)
                            log_signal(parsed)
                            await client.send_message(config.TARGET_GROUP_ID, out)
                            total += 1
                            print(f"  📊 signal {parsed['direction']} {parsed['asset']} ({title})")
                            await asyncio.sleep(1)
                            continue

                    cleaned = clean_message(raw_text)
                    if cleaned:
                        if is_alert:
                            cleaned = f"🔴⚠️ ALERTE MARCHÉ ⚠️🔴\n\n{cleaned}"
                        await client.send_message(config.TARGET_GROUP_ID, cleaned, parse_mode='md')
                        total += 1
                        print(f"  ✅ ({title}) {cleaned[:60].strip()}...")
                        await asyncio.sleep(1)

        except Exception as e:
            print(f"  ❌ {group_id}: {e}")

    await client.disconnect()
    print(f"\n✅ Terminé — {total} envoyés, {skipped} ignorés")

asyncio.run(main())
