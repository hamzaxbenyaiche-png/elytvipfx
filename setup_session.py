"""
Importe la session Telegram Desktop existante vers Telethon.
Lance ce script UNE SEULE FOIS pour créer session_forwarder.session
"""

import asyncio
from opentele.td import TDesktop
from opentele.api import API, CreateNewSession
from telethon import TelegramClient

TDATA_PATH = "/Users/hamzaxbench/Library/Application Support/Telegram Desktop/tdata"

async def main():
    print("Lecture de la session Telegram Desktop...")
    tdesk = TDesktop(TDATA_PATH)

    print(f"Comptes trouvés : {len(tdesk.accounts)}")
    if not tdesk.accounts:
        print("Aucun compte trouvé dans tdata !")
        return

    # Convertit la session tdata → Telethon
    print("Conversion de la session...")
    client = await tdesk.ToTelethon(
        session="session_forwarder",
        flag=CreateNewSession,
        api=API.TelegramDesktop
    )

    async with client:
        me = await client.get_me()
        print(f"\nConnecté en tant que : {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
        print(f"ID utilisateur : {me.id}")

        print("\n=== Tes groupes et canaux ===\n")
        target_id = None
        async for dialog in client.iter_dialogs():
            from telethon.tl.types import Channel, Chat
            if isinstance(dialog.entity, (Channel, Chat)):
                print(f"  ID: {dialog.id:>20}  |  {dialog.name}")
                if "elyt" in dialog.name.lower():
                    target_id = dialog.id
                    print(f"   ^^^ GROUPE CIBLE TROUVÉ ^^^")

        if target_id:
            print(f"\nID du groupe cible 'elyt CFDs forex' : {target_id}")
            # Met à jour config.py automatiquement
            with open("config.py", "r") as f:
                content = f.read()
            content = content.replace("TARGET_GROUP_ID = 0", f"TARGET_GROUP_ID = {target_id}")
            with open("config.py", "w") as f:
                f.write(content)
            print("config.py mis à jour avec le TARGET_GROUP_ID !")

    print("\nSession sauvegardée dans session_forwarder.session")
    print("Tu peux maintenant lancer : python3 forwarder.py")

if __name__ == '__main__':
    asyncio.run(main())
