"""
Supprime tous les messages du groupe public depuis le 23 juin
et renvoie les versions corrigées ELYT pour chaque jour.
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
import config

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo('Europe/Paris')
    def paris_now():
        return datetime.now(PARIS)
    def paris_dt(year, month, day, hour=0, minute=0):
        return datetime(year, month, day, hour, minute, tzinfo=PARIS)
except ImportError:
    def paris_now():
        utc = datetime.now(timezone.utc)
        offset = timedelta(hours=2)
        return (utc + offset).replace(tzinfo=None)
    def paris_dt(year, month, day, hour=0, minute=0):
        return datetime(year, month, day, hour, minute)

TARGET = config.TARGET_GROUP_ID

# ── Dou'as ──────────────────────────────────────────────────────────────
DUAS = [
    {"arabic": "اللَّهُمَّ بَارِكْ لَنَا فِي تِجَارَتِنَا وَارْزُقْنَا مِنْ فَضْلِكَ",
     "french": "Ô Allah, bénis notre commerce et accorde-nous de Ta grâce une subsistance licite et abondante."},
    {"arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ رِزْقًا حَلَالًا وَاسِعًا طَيِّبًا",
     "french": "Ô Allah, je Te demande une subsistance licite, abondante et bonne."},
    {"arabic": "اللَّهُمَّ بَارِكْ لَنَا فِيمَا رَزَقْتَنَا وَقِنَا عَذَابَ النَّارِ",
     "french": "Ô Allah, bénis-nous dans ce que Tu nous as accordé et préserve-nous du châtiment du Feu."},
    {"arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
     "french": "Notre Seigneur, accorde-nous une belle part en ce monde et dans l'au-delà, et préserve-nous du châtiment du Feu."},
    {"arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا طَيِّبًا وَعَمَلًا مُتَقَبَّلًا",
     "french": "Ô Allah, je Te demande un savoir utile, une subsistance bonne et une œuvre acceptée."},
]

# ── Teasers éducatifs ───────────────────────────────────────────────────
TEASERS = [
    "💡 <b>CONSEIL DU JOUR</b>\n\nNe tradez jamais sans stop loss défini avant d'entrer. Pas après. Avant.\n\nLa discipline sur le SL c'est ce qui sépare ceux qui durent de ceux qui brûlent leur compte en quelques semaines.\n\nC'est ce qu'on applique sur chaque signal chez elyt. @elytsupport",
    "📖 <b>CE QUE PERSONNE NE TE DIT SUR LE TRADING</b>\n\nLa majorité des pertes ne viennent pas de mauvais signaux. Elles viennent de la surexposition.\n\nTrader 0.01 lot sur un compte de 100€ et trader 1 lot sur un compte de 100€, c'est pas le même jeu. L'un construit, l'autre détruit.\n\nGerez votre risque. Toujours. @elytsupport",
    "🧠 <b>PSYCHOLOGIE DE TRADING</b>\n\nLe pire ennemi d'un trader c'est pas le marché. C'est lui-même.\n\nCouper ses gains trop tôt par peur. Laisser courir ses pertes par espoir. Ce pattern détruit plus de comptes que n'importe quelle analyse ratée.\n\nLaisser le plan travailler. C'est tout. @elytsupport",
    "📊 <b>POURQUOI LE BIAIS DAILY EST IMPORTANT</b>\n\nTrader en H1 contre le biais Daily c'est nager à contre-courant.\n\nOn peut gagner quelques trades comme ça. Mais sur la durée, le Daily gagne toujours. Chaque matin chez elyt on commence par là — lire le marché avant de l'attaquer.\n\n@elytsupport",
    "⏳ <b>LA PATIENCE EST UNE POSITION</b>\n\nNe pas trader c'est aussi une décision.\n\nQuand le marché n'est pas clair, quand les signaux se contredisent, quand la liquidité est faible — rester en dehors c'est protéger son capital. Les meilleures semaines sont souvent celles où on a su attendre le bon setup.\n\n@elytsupport",
]

# ── Messages par type ────────────────────────────────────────────────────
def msg_dua(dua, jour, date_str):
    return (
        f"🤲 <b>DOU'A DU MATIN</b>\n\n"
        f"「 {dua['arabic']} 」\n\n"
        f"<i>{dua['french']}</i>\n\n"
        f"Que Allah bénisse votre journée et vos échanges 🤍"
    )

def msg_london():
    return (
        "🇬🇧 <b>LONDON KILLZONE — 8H00</b>\n\n"
        "La liquidité entre sur le marché. "
        "C'est maintenant que les vraies positions s'ouvrent.\n\n"
        "Pas de précipitation. On attend la structure, on attend la confirmation. "
        "Un bon setup vaut mieux que trois mauvaises entrées.\n\n"
        "<i>Disciplinés. Patients. Décisifs.</i>\n\n"
        "@elytsupport"
    )

def msg_analyse(jour, date_str):
    intros = [
        "Voilà ce que les marchés nous donnent ce matin. Lisez, analysez, et attendez votre setup. Pas de précipitation.",
        "Le marché a parlé cette nuit. Voici ce que ça donne. Prenez le temps de lire avant d'ouvrir quoi que ce soit.",
        "Avant de toucher à quoi que ce soit, lisez ça. L'analyse du jour est posée, c'est à vous de jouer.",
        "Nouvelle journée, nouveau biais. On repart de zéro, on relit le marché, on attend la confirmation.",
    ]
    jours = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']
    idx = jours.index(jour) if jour in jours else 0
    return (
        f"🌅 <b>ANALYSE DU MATIN — ELYT</b>\n"
        f"<i>{jour} {date_str}</i>\n\n"
        f"{intros[idx % len(intros)]}\n\n"
        f"<i>Analyse disponible sur les graphiques. Biais Daily + H4 consultés avant chaque signal.</i>\n\n"
        f"@elytsupport"
    )

def msg_relance(n=14):
    return (
        f"🔐 <b>ELYT FOREX VIP</b>\n\n"
        f"{n} places disponibles ce mois-ci.\n\n"
        f"Chaque matin tu reçois l'analyse des marchés. Chaque signal en temps réel. Chaque TP, on le vit ensemble.\n\n"
        f"📩 @elytsupport"
    )

def msg_bilan(period, signals=12, tps=8):
    wr = round((min(signals, round(tps / 2)) / signals) * 100) if signals > 0 else 0
    return (
        f"📊 <b>BILAN DE LA SEMAINE — ELYT</b>\n"
        f"<i>Semaine du {period}</i>\n\n"
        f"📡  Signaux envoyés   <b>{signals}</b>\n"
        f"✅  TP atteints       <b>{tps}</b>\n"
        f"📈  Winrate estimé    <b>~{wr}%</b>\n\n"
        f"Que Allah bénisse nos échanges et multiplie nos rizq 🤲\n\n"
        f"@elytsupport"
    )

def msg_weekend():
    return (
        "🏴‍☠️ <b>WEEK-END — ELYT</b>\n\n"
        "Semaine terminée.\n\n"
        "Les marchés ont bougé, on a bougé avec eux. "
        "Chaque trade géré proprement — gagné ou non — c'est de la progression. "
        "C'est ça le vrai travail.\n\n"
        "Profitez du week-end. Ressourcez-vous. "
        "Lundi les marchés rouvrent et on repart.\n\n"
        "<i>Bonne soirée à toute la team elyt</i> 🤍\n\n"
        "@elytsupport"
    )

DAYS = [
    ("Lundi",    "23/06/2026"),
    ("Mardi",    "24/06/2026"),
    ("Mercredi", "25/06/2026"),
    ("Jeudi",    "26/06/2026"),
    ("Vendredi", "27/06/2026"),
]


async def main():
    client = TelegramClient('session_audit', config.API_ID, config.API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Non autorisé")
        return
    print("✅ Connecté\n")

    # ── 1. Suppression de TOUS les messages depuis le 23 juin ─────────────
    cutoff = paris_dt(2026, 6, 23, 0, 0).astimezone(timezone.utc)
    to_delete = []
    print("Recherche des messages à supprimer...")
    async for msg in client.iter_messages(TARGET, limit=500):
        msg_date = msg.date.astimezone(timezone.utc) if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
        if msg_date >= cutoff:
            to_delete.append(msg.id)
        else:
            break  # messages plus anciens → stop

    if to_delete:
        # Suppression par batch de 100
        for i in range(0, len(to_delete), 100):
            await client.delete_messages(TARGET, to_delete[i:i+100])
        print(f"✅ {len(to_delete)} message(s) supprimé(s)\n")
    else:
        print("ℹ️ Aucun message à supprimer\n")

    await asyncio.sleep(2)

    # ── 2. Renvoi des messages corrigés par jour ──────────────────────────
    random.seed(42)  # reproductible pour les dua'as
    dua_pool = DUAS.copy()
    random.shuffle(dua_pool)

    for i, (jour, date_str) in enumerate(DAYS):
        print(f"── {jour} {date_str} ──")
        dua = dua_pool[i % len(dua_pool)]

        # Dou'a du matin
        await client.send_message(TARGET, msg_dua(dua, jour, date_str), parse_mode='html')
        print(f"  ✅ Dou'a")
        await asyncio.sleep(1)

        # Analyse du matin
        await client.send_message(TARGET, msg_analyse(jour, date_str), parse_mode='html')
        print(f"  ✅ Analyse du matin")
        await asyncio.sleep(1)

        # London KZ (jours de semaine uniquement)
        await client.send_message(TARGET, msg_london(), parse_mode='html')
        print(f"  ✅ London KZ")
        await asyncio.sleep(1)

        # Teaser (1 par jour, rotatif)
        teaser = TEASERS[i % len(TEASERS)]
        await client.send_message(TARGET, teaser, parse_mode='html')
        print(f"  ✅ Teaser")
        await asyncio.sleep(1)

        # Relance VIP 18h
        await client.send_message(TARGET, msg_relance(), parse_mode='html')
        print(f"  ✅ Relance VIP")
        await asyncio.sleep(1)

        # Vendredi → bilan + week-end
        if jour == "Vendredi":
            await client.send_message(TARGET, msg_bilan("23/06 au 27/06/2026"), parse_mode='html')
            print(f"  ✅ Bilan semaine")
            await asyncio.sleep(1)
            await client.send_message(TARGET, msg_weekend(), parse_mode='html')
            print(f"  ✅ Week-end")
            await asyncio.sleep(1)

        print()

    print("✅ Tout renvoyé avec succès.")
    await client.disconnect()

asyncio.run(main())
