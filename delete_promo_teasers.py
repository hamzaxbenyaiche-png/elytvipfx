"""Supprime les anciens teasers promo/vente du groupe public."""
import asyncio
from telethon import TelegramClient
import config

PROMO_KEYWORDS = [
    "ALERTE VIP — ELYT",
    "LES MEMBRES VIP SONT EN POSITION",
    "CE SIGNAL VIENT D'ÊTRE ENVOYÉ AU VIP",
    "SIGNAL ACTIF — ELYT FOREX VIP",
    "TU VEUX DES RÉSULTATS CONCRETS",
    "Envoie \"VIP\"",
    "Envoie \"vip\"",
    'Envoie "VIP"',
    "tu veux être le prochain",
    "Ici tu suis. Là-bas tu trades",
    "les membres sont en position",
]

async def main():
    client = TelegramClient('session_audit', config.API_ID, config.API_HASH)
    await client.connect()
    print("✅ Connecté")

    to_delete = []
    async for msg in client.iter_messages(config.TARGET_GROUP_ID, limit=200):
        if msg.text and any(kw.lower() in msg.text.lower() for kw in PROMO_KEYWORDS):
            to_delete.append(msg.id)
            print(f"  → Suppression {msg.id}: {msg.text[:60]!r}")

    if to_delete:
        await client.delete_messages(config.TARGET_GROUP_ID, to_delete)
        print(f"✅ {len(to_delete)} message(s) supprimé(s)")
    else:
        print("ℹ️ Aucun message promo trouvé")

    await client.disconnect()

asyncio.run(main())
