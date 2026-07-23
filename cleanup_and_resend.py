"""
Supprime les anciens messages de la session et renvoie les teasers corrigés.
"""
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteMessagesRequest
import config

TARGET = config.TARGET_GROUP_ID

VIP_TEASERS = [
    "💡 <b>CONSEIL DU JOUR</b>\n\nNe tradez jamais sans stop loss défini avant d'entrer. Pas après. Avant.\n\nLa discipline sur le SL c'est ce qui sépare ceux qui durent de ceux qui brûlent leur compte en quelques semaines.\n\nC'est ce qu'on applique sur chaque signal chez elyt. @elytsupport",

    "📖 <b>CE QUE PERSONNE NE TE DIT SUR LE TRADING</b>\n\nLa majorité des pertes ne viennent pas de mauvais signaux. Elles viennent de la surexposition.\n\nTrader 0.01 lot sur un compte de 100€ et trader 1 lot sur un compte de 100€, c'est pas le même jeu. L'un construit, l'autre détruit.\n\nGerez votre risque. Toujours. @elytsupport",

    "🧠 <b>PSYCHOLOGIE DE TRADING</b>\n\nLe pire ennemi d'un trader c'est pas le marché. C'est lui-même.\n\nCouper ses gains trop tôt par peur. Laisser courir ses pertes par espoir. Ce pattern détruit plus de comptes que n'importe quelle analyse ratée.\n\nLaisser le plan travailler. C'est tout. @elytsupport",

    "📊 <b>POURQUOI LE BIAIS DAILY EST IMPORTANT</b>\n\nTrader en H1 contre le biais Daily c'est nager à contre-courant.\n\nOn peut gagner quelques trades comme ça. Mais sur la durée, le Daily gagne toujours. Chaque matin chez elyt on commence par là — lire le marché avant de l'attaquer.\n\n@elytsupport",

    "⏳ <b>LA PATIENCE EST UNE POSITION</b>\n\nNe pas trader c'est aussi une décision.\n\nQuand le marché n'est pas clair, quand les signaux se contredisent, quand la liquidité est faible — rester en dehors c'est protéger son capital. Les meilleures semaines sont souvent celles où on a su attendre le bon setup.\n\n@elytsupport",
]

async def main():
    client = TelegramClient('session_audit', config.API_ID, config.API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Session non autorisée")
        return

    print("✅ Connecté")

    # Récupère les 60 derniers messages du groupe
    msgs_to_delete = []
    async for msg in client.iter_messages(TARGET, limit=60):
        if msg.text:
            t = msg.text
            # Cible les anciens teasers (titres en minuscule) et les anomalies
            if any(kw in t for kw in [
                "Conseil du jour",
                "Ce que personne ne te dit",
                "Psychologie de trading",
                "Pourquoi le biais Daily",
                "La patience est une position",
                # Anomalies HTML visibles dans les messages
                "_C'est ça le travail.",
                "_Semaine du",
                "_Mis à jour",
                "_Bonne soirée",
                "_Disciplinés",
                "h4update</i>",
            ]):
                msgs_to_delete.append(msg.id)
                print(f"  → Suppression msg {msg.id}: {t[:60].strip()!r}")

    if msgs_to_delete:
        await client.delete_messages(TARGET, msgs_to_delete)
        print(f"✅ {len(msgs_to_delete)} message(s) supprimé(s)")
    else:
        print("ℹ️ Aucun message à supprimer")

    # Envoie les 5 teasers corrigés
    print("\nEnvoi des nouveaux teasers...")
    for i, teaser in enumerate(VIP_TEASERS, 1):
        await client.send_message(TARGET, teaser, parse_mode='html')
        print(f"  ✅ Teaser {i}/5 envoyé")
        await asyncio.sleep(1)

    print("\n✅ Terminé.")
    await client.disconnect()

asyncio.run(main())
