"""Lance le forwarder Telegram."""
import asyncio
import sys
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat

API_ID   = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET   = -5471330752  # elyt CFDs forex

async def main():
    client = TelegramClient('session_forwarder', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Session invalide — relance qr_login.py", flush=True)
        return

    me = await client.get_me()
    target = await client.get_entity(TARGET)
    print(f"✅ Connecté : {me.first_name}", flush=True)
    print(f"🎯 Cible : {target.title}", flush=True)
    print(f"📡 En écoute sur tous les groupes...", flush=True)

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            chat = await event.get_chat()
            if not isinstance(chat, (Channel, Chat)):
                return
            if event.chat_id == TARGET:
                return

            chat_title = getattr(chat, 'title', 'Inconnu')
            sender = await event.get_sender()
            sender_name = ''
            if sender:
                f = getattr(sender, 'first_name', '') or ''
                l = getattr(sender, 'last_name', '') or ''
                sender_name = f"{f} {l}".strip() or getattr(sender, 'username', '')

            if event.message.media:
                await client.forward_messages(TARGET, event.message)
            elif event.message.text:
                await client.send_message(TARGET, event.message.text)

            print(f"[OK] {chat_title} → copié", flush=True)
        except Exception as e:
            print(f"[ERR] {e}", flush=True)

    await client.run_until_disconnected()

asyncio.run(main())
