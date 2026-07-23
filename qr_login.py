"""
Connexion Telethon par QR code.
Lance ce script, scanne le QR avec ton téléphone Telegram, et la session est créée.
"""

import asyncio
import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Credentials Telegram Desktop officiels
API_ID   = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

async def main():
    client = TelegramClient("session_forwarder", API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Déjà connecté : {me.first_name} (@{me.username})")
        await find_target_group(client)
        await client.disconnect()
        return

    print("Génération du QR code de connexion...\n")

    qr_login = await client.qr_login()

    # Affiche le QR code dans le terminal
    qr = qrcode.QRCode()
    qr.add_data(qr_login.url)
    qr.make()
    qr.print_ascii(invert=True)

    print(f"\nURL : {qr_login.url}")
    print("\n→ Scanne ce QR code avec Telegram sur ton téléphone :")
    print("   Paramètres → Appareils → Connecter un appareil\n")
    print("En attente du scan...")

    try:
        await qr_login.wait(timeout=120)
        print("\nConnexion réussie !")
    except SessionPasswordNeededError:
        pwd = input("Mot de passe 2FA : ")
        await client.sign_in(password=pwd)
    except Exception as e:
        print(f"Erreur : {e}")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"Connecté : {me.first_name} {me.last_name or ''} (@{me.username or me.id})")

    await find_target_group(client)
    await client.disconnect()

async def find_target_group(client):
    from telethon.tl.types import Channel, Chat

    print("\n=== Tes groupes et canaux ===\n")
    target_id = None

    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, (Channel, Chat)):
            print(f"  {dialog.id:>20}  |  {dialog.name}")
            if "elyt" in dialog.name.lower():
                target_id = dialog.id
                print(f"                       ^^^ GROUPE CIBLE ^^^")

    if target_id:
        print(f"\nID trouvé : {target_id}")
        with open("config.py", "r") as f:
            content = f.read()
        content = content.replace("TARGET_GROUP_ID = 0", f"TARGET_GROUP_ID = {target_id}")
        # Mise à jour API credentials aussi
        content = content.replace("API_ID   = 0", "API_ID   = 2040")
        content = content.replace('API_HASH = ""', 'API_HASH = "b18441a1ff607e10a989891a5462e627"')
        with open("config.py", "w") as f:
            f.write(content)
        print("config.py mis à jour automatiquement !")
        print("\nLance maintenant : python3 forwarder.py")

if __name__ == "__main__":
    asyncio.run(main())
