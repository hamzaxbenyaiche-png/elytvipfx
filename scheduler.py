"""
Tâches planifiées pour ELYT CFDs forex :
- Analyse de marché quotidienne (7h Paris)
- Citations islamiques sur le commerce (8h et 20h Paris)
- Bilan hebdomadaire (vendredi 19h)
"""

import asyncio
import json
import logging
import os
import random
import shutil
from datetime import datetime, timezone, timedelta

import httpx
import config
from signal_parser import get_week_stats

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo('Europe/Paris')
    def paris_now():
        return datetime.now(PARIS)
except ImportError:
    # Python < 3.9 fallback (DST approximatif)
    def paris_now():
        utc = datetime.now(timezone.utc)
        month = utc.month
        offset = timedelta(hours=2 if 3 < month < 11 else 1)
        return (utc + offset).replace(tzinfo=None)

log = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), 'scheduler_state.json')
SPOTS_FILE = os.path.join(os.path.dirname(__file__), 'spots.json')


# ─────────────────────────────────────────────
#  GESTION DES PLACES VIP
# ─────────────────────────────────────────────

def _load_spots() -> dict:
    try:
        if os.path.exists(SPOTS_FILE):
            with open(SPOTS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"base_cap": 20, "start_month": 6, "start_year": 2026}

def _save_spots(spots: dict):
    with open(SPOTS_FILE, 'w') as f:
        json.dump(spots, f, indent=2)

def _get_monthly_cap() -> int:
    """Cap du mois courant : 20 + 5 par mois écoulé depuis juin 2026."""
    spots = _load_spots()
    now = paris_now()
    base_cap = spots.get('base_cap', 20)
    start_month = spots.get('start_month', 6)
    start_year  = spots.get('start_year', 2026)
    months_elapsed = (now.year - start_year) * 12 + (now.month - start_month)
    return base_cap + max(0, months_elapsed) * 5

def _get_spots_shown() -> int:
    """
    Calcule le nombre de places affichées automatiquement selon le jour du mois.
    La progression crée une pression croissante : les places "fondent" au fil des jours.
    Semaine 1 : cap complet
    Semaine 2 : 70% restant
    Semaine 3 : 40% restant
    Semaine 4 : 15% restant → 2-3 places
    Fin de mois : COMPLET / liste d'attente
    """
    import calendar
    now = paris_now()
    cap = _get_monthly_cap()
    day = now.day
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    progress = day / days_in_month  # 0.0 → 1.0

    if progress < 0.25:       # semaine 1
        ratio = 1.0
    elif progress < 0.50:     # semaine 2
        ratio = 0.70
    elif progress < 0.75:     # semaine 3
        ratio = 0.40
    elif progress < 0.90:     # semaine 4
        ratio = 0.15
    else:                     # fin de mois
        ratio = 0.0

    return max(0, round(cap * ratio))

def spots_urgency(n: int) -> str:
    if n <= 0:   return "COMPLET"
    if n <= 3:   return "QUASI_COMPLET"
    if n <= 7:   return "URGENT"
    if n <= 12:  return "MODÉRÉ"
    return "NORMAL"


DAILY_MESSAGES_NORMAL = [
    "🔐 <b>ELYT FOREX VIP</b>\n\n{n} places disponibles ce mois-ci.\n\nChaque matin tu reçois l'analyse des marchés. Chaque signal en temps réel. Chaque TP, on le vit ensemble.\n\n📩 @elytsupport",
    "🎯 <b>TU VEUX DES RÉSULTATS ?</b>\n\nELYT FOREX VIP c'est :\n\n✅ Signaux exclusifs XAUUSD & Forex\n✅ Biais Daily + H4 chaque matin\n✅ Suivi personnalisé\n\n{n} places encore disponibles.\n\n📩 @elytsupport",
    "📊 <b>ELYT FOREX VIP — {n} places</b>\n\nPendant que les marchés bougent, les membres sont déjà positionnés.\n\nTu veux faire partie de ceux qui avancent ?\n\n📩 @elytsupport",
]

DAILY_MESSAGES_MODERE = [
    "⚡️ <b>{n} PLACES RESTANTES</b>\n\nOn est à mi-chemin du mois. Les places partent.\n\nNe laisse pas une autre semaine passer sans agir.\n\n📩 @elytsupport",
    "📊 <b>ELYT FOREX VIP — {n} places</b>\n\nChaque semaine les membres encaissent avec nous.\n\nCette semaine tu étais où ?\n\n📩 @elytsupport",
    "💰 <b>{n} PLACES DISPONIBLES</b>\n\nCeux qui ont rejoint en début de mois ont déjà encaissé sur plusieurs setups.\n\nIl te reste une fenêtre pour ce mois. ⏳\n\n📩 @elytsupport",
]

DAILY_MESSAGES_URGENT = [
    "🚨 <b>PLUS QUE {n} PLACES</b>\n\nOn approche de la limite de ce mois.\n\nAprès ça : liste d'attente. Rien d'autre.\n\n📩 @elytsupport — maintenant.",
    "⏳ <b>{n} PLACES RESTANTES</b>\n\nChaque jour qui passe c'est une place de moins.\n\nLes hésitants attendront le mois prochain.\nLes décidés rejoignent maintenant.\n\n📩 @elytsupport",
    "🔥 <b>DERNIÈRES PLACES CE MOIS</b>\n\n{n} places. C'est tout ce qu'il reste.\n\n✅ Signaux exclusifs\n✅ Analyse quotidienne\n✅ Résultats réels\n\n📩 @elytsupport",
]

DAILY_MESSAGES_QUASI = [
    "🚨 <b>{n} PLACE — C'EST TOUT</b>\n\nELYT FOREX VIP est quasi complet pour ce mois.\n\nSi tu lis ça tu as encore une chance. Saisis-la.\n\n📩 @elytsupport",
    "⛔️ <b>QUASI COMPLET</b>\n\nIl ne reste que <b>{n} place</b> pour rejoindre ce mois.\n\nLes suivants iront sur liste d'attente.\n\n📩 @elytsupport — dernière chance.",
]

DAILY_MESSAGES_COMPLET = [
    "🔒 <b>ELYT FOREX VIP — COMPLET</b>\n\nToutes les places de ce mois sont occupées.\n\n📋 Liste d'attente : @elytsupport\n\n<i>Les premières places du mois prochain sont réservées en priorité aux inscrits sur liste d'attente.</i>",
    "🔒 <b>COMPLET POUR CE MOIS</b>\n\nELYT FOREX VIP n'a plus de places disponibles jusqu'au mois prochain.\n\nTu veux être prioritaire ?\n\n📩 @elytsupport — inscris-toi maintenant.",
]


async def send_daily_relance(client):
    """Relance quotidienne 18h — urgence auto selon le jour du mois."""
    try:
        n = _get_spots_shown()
        level = spots_urgency(n)
        now = paris_now()

        if level == "COMPLET":
            pool = DAILY_MESSAGES_COMPLET
        elif level == "QUASI_COMPLET":
            pool = DAILY_MESSAGES_QUASI
        elif level == "URGENT":
            pool = DAILY_MESSAGES_URGENT
        elif level == "MODÉRÉ":
            pool = DAILY_MESSAGES_MODERE
        else:
            pool = DAILY_MESSAGES_NORMAL

        # Rotation basée sur le jour pour ne pas répéter deux fois de suite le même
        msg_template = pool[now.day % len(pool)]
        msg = msg_template.replace('{n}', str(n)).replace("{'s' if {n}>1 else ''}", 's' if n > 1 else '')

        await client.send_message(config.TARGET_GROUP_ID, msg, parse_mode='html')
        log.info(f"[RELANCE DAILY] {n} places affichées — {level}")
    except Exception as e:
        log.error(f"[RELANCE DAILY] Erreur: {e}")


async def send_weekly_relance(client):
    """Relance hebdomadaire vendredi 19h — bilan de la semaine + push VIP."""
    try:
        n = _get_spots_shown()
        stats = get_week_stats()
        signals = stats.get('signals', 0)
        tps = stats.get('tps', 0)

        now = paris_now()
        monday = now - timedelta(days=now.weekday())
        period = f"{monday.strftime('%d/%m')} → {now.strftime('%d/%m')}"

        msg = (
            f"📅 <b>BILAN DE LA SEMAINE — ELYT</b>\n"
            f"<i>{period}</i>\n\n"
            f"Cette semaine avec elyt :\n"
            f"📡 <b>{signals} signaux</b> envoyés sur les marchés\n"
            f"✅ <b>{tps} TP</b> atteints\n\n"
            f"💰 Profits sécurisés sur XAUUSD & Forex\n\n"
            f"🔐 <b>ELYT FOREX VIP — {n} place{'s' if n != 1 else ''} restante{'s' if n != 1 else ''}</b>\n\n"
            f"ELYT FOREX VIP c'est exactement ça, mais en exclusif :\n"
            f"• Signaux avant tout le monde\n"
            f"• Analyse approfondie\n"
            f"• Suivi de tes trades en direct\n\n"
            f"{'⚠️ Presque complet — agis vite.' if n <= 7 else 'Places limitées chaque mois.'}\n\n"
            f"📩 @elytsupport pour rejoindre 🎯"
        )

        await client.send_message(config.TARGET_GROUP_ID, msg, parse_mode='html')
        log.info(f"[RELANCE WEEKLY] Envoyée — {signals} signaux, {tps} TP, {n} places")

        weekend_msg = (
            "🔥 <b>WEEK-END — ELYT</b>\n\n"
            "Semaine terminée.\n\n"
            "Les marchés ont bougé, on a bougé avec eux. "
            "Chaque trade géré proprement — gagné ou non — c'est de la progression. "
            "C'est ça le vrai travail.\n\n"
            "Profitez du week-end. Ressourcez-vous. "
            "Lundi les marchés rouvrent et on repart.\n\n"
            "<i>Bonne soirée à toute la team elyt</i> 🤍\n\n"
            "🧿 @elytsupport"
        )
        await client.send_message(config.TARGET_GROUP_ID, weekend_msg, parse_mode='html')
        log.info("[RELANCE WEEKLY] Message week-end envoyé")
    except Exception as e:
        log.error(f"[RELANCE WEEKLY] Erreur: {e}")


async def send_monthly_relance(client):
    """Relance mensuelle 1er du mois 10h — grande offre."""
    try:
        n = _get_spots_shown()
        cap = _get_monthly_cap()
        now = paris_now()
        month_name = ['Janvier','Février','Mars','Avril','Mai','Juin',
                      'Juillet','Août','Septembre','Octobre','Novembre','Décembre'][now.month-1]

        msg = (
            f"🔥 <b>NOUVEAU MOIS — ELYT FOREX VIP</b>\n"
            f"<i>{month_name} {now.year}</i>\n\n"
            f"<b>{cap} nouvelles places</b> sont ouvertes pour ce mois.\n\n"
            f"ELYT FOREX VIP c'est :\n\n"
            f"📡 <b>Signaux exclusifs</b> — XAUUSD, Forex, Indices\n"
            f"🌅 <b>Analyse du matin</b> — Biais Daily + H4 chaque jour\n"
            f"⚡️ <b>TP en temps réel</b> — tu suis chaque mouvement\n"
            f"💬 <b>Accompagnement</b> — tu n'es jamais seul\n\n"
            f"Ce mois-ci : <b>{n} places disponibles</b>\n"
            f"Le mois dernier : toutes les places ont été prises.\n\n"
            f"🚀 Les premières personnes à rejoindre auront accès "
            f"aux setups de la semaine dès aujourd'hui.\n\n"
            f"📩 Envoie un message à @elytsupport pour rejoindre maintenant."
        )

        await client.send_message(config.TARGET_GROUP_ID, msg, parse_mode='html')
        log.info(f"[RELANCE MONTHLY] Envoyée — {cap} places ce mois")
    except Exception as e:
        log.error(f"[RELANCE MONTHLY] Erreur: {e}")

FLAGS = {
    'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵',
    'CHF': '🇨🇭', 'CAD': '🇨🇦', 'AUD': '🇦🇺', 'NZD': '🇳🇿',
    'CNY': '🇨🇳', 'CHN': '🇨🇳',
}
IMPACT = {'High': '🔴', 'Medium': '🟡', 'Low': '⚪️'}

ISLAMIC_QUOTES = [
    {
        "type": "📖 Verset du Coran",
        "arabic": "وَأَحَلَّ اللَّهُ الْبَيْعَ وَحَرَّمَ الرِّبَا",
        "french": "Allah a rendu le commerce licite et a interdit l'usure.",
        "source": "Sourate Al-Baqara — 2:275"
    },
    {
        "type": "🤲 Hadith",
        "arabic": "التَّاجِرُ الصَّدُوقُ الْأَمِينُ مَعَ النَّبِيِّينَ وَالصِّدِّيقِينَ وَالشُّهَدَاءِ",
        "french": "Le marchand honnête et digne de confiance sera avec les prophètes, les véridiques et les martyrs.",
        "source": "Tirmidhi"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "وَابْتَغِ فِيمَا آتَاكَ اللَّهُ الدَّارَ الْآخِرَةَ وَلَا تَنسَ نَصِيبَكَ مِنَ الدُّنْيَا",
        "french": "Et cherche, dans ce qu'Allah t'a donné, la Demeure dernière, sans oublier ta part en ce monde.",
        "source": "Sourate Al-Qasas — 28:77"
    },
    {
        "type": "🤲 Hadith",
        "arabic": "مَا أَكَلَ أَحَدٌ طَعَامًا قَطُّ خَيْرًا مِنْ أَنْ يَأْكُلَ مِنْ عَمَلِ يَدِهِ",
        "french": "Nul n'a jamais mangé de meilleure nourriture que celle qu'il a gagnée du travail de ses propres mains.",
        "source": "Bukhari"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "هُوَ الَّذِي جَعَلَ لَكُمُ الْأَرْضَ ذَلُولًا فَامْشُوا فِي مَنَاكِبِهَا وَكُلُوا مِن رِّزْقِهِ",
        "french": "C'est Lui qui a mis la terre à votre service. Parcourez-en donc les contrées et mangez de Sa subsistance.",
        "source": "Sourate Al-Mulk — 67:15"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "وَمَن يَتَّقِ اللَّهَ يَجْعَل لَّهُ مَخْرَجًا وَيَرْزُقْهُ مِنْ حَيْثُ لَا يَحْتَسِبُ",
        "french": "Quiconque craint Allah, Il lui ménagera une issue et lui accordera Sa grâce par où il ne s'y attendait pas.",
        "source": "Sourate At-Talaq — 65:2-3"
    },
    {
        "type": "🤲 Hadith",
        "arabic": "إِنَّ اللَّهَ يُحِبُّ إِذَا عَمِلَ أَحَدُكُمْ عَمَلًا أَنْ يُتْقِنَهُ",
        "french": "Allah aime que lorsque l'un d'entre vous fait un travail, il le fasse avec excellence.",
        "source": "Bayhaqi"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "وَآتَاكُم مِّن كُلِّ مَا سَأَلْتُمُوهُ",
        "french": "Et Il vous a donné de tout ce que vous Lui avez demandé.",
        "source": "Sourate Ibrahim — 14:34"
    },
    {
        "type": "🤲 Dou'a du commerce",
        "arabic": "اللَّهُمَّ بَارِكْ لَنَا فِي تِجَارَتِنَا وَارْزُقْنَا مِنْ فَضْلِكَ",
        "french": "Ô Allah, bénis notre commerce et accorde-nous de Ta grâce une subsistance licite et abondante.",
        "source": "Invocation"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "french": "Certes, avec la difficulté vient la facilité.",
        "source": "Sourate Al-Inshirah — 94:6"
    },
    {
        "type": "🤲 Dou'a pour la baraka",
        "arabic": "اللَّهُمَّ بَارِكْ لَنَا فِيمَا رَزَقْتَنَا",
        "french": "Ô Allah, bénis-nous dans ce que Tu nous as accordé comme subsistance.",
        "source": "Invocation"
    },
    {
        "type": "🤲 Dou'a pour le rizq",
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ رِزْقًا حَلَالًا وَاسِعًا طَيِّبًا",
        "french": "Ô Allah, je Te demande une subsistance licite, abondante et bonne.",
        "source": "Invocation"
    },
    {
        "type": "📖 Verset du Coran",
        "arabic": "وَقُل رَّبِّ زِدْنِي عِلْمًا",
        "french": "Et dis : Mon Seigneur, accroît mes connaissances.",
        "source": "Sourate Ta-Ha — 20:114"
    },
    {
        "type": "🤲 Hadith",
        "arabic": "الْبَيِّعَانِ بِالْخِيَارِ مَا لَمْ يَتَفَرَّقَا فَإِنْ صَدَقَا وَبَيَّنَا بُورِكَ لَهُمَا فِي بَيْعِهِمَا",
        "french": "Si les deux parties du contrat sont honnêtes et transparentes, leur transaction sera bénie.",
        "source": "Bukhari & Muslim"
    },
]

MORNING_DUAS = [
    {
        "arabic": "اللَّهُمَّ بَارِكْ لَنَا فِي تِجَارَتِنَا وَارْزُقْنَا مِنْ فَضْلِكَ",
        "french": "Ô Allah, bénis notre commerce et accorde-nous de Ta grâce une subsistance licite et abondante."
    },
    {
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ رِزْقًا حَلَالًا وَاسِعًا طَيِّبًا",
        "french": "Ô Allah, je Te demande une subsistance licite, abondante et bonne."
    },
    {
        "arabic": "اللَّهُمَّ بَارِكْ لَنَا فِيمَا رَزَقْتَنَا وَقِنَا عَذَابَ النَّارِ",
        "french": "Ô Allah, bénis-nous dans ce que Tu nous as accordé et préserve-nous du châtiment du Feu."
    },
    {
        "arabic": "اللَّهُمَّ اكْفِنِي بِحَلَالِكَ عَنْ حَرَامِكَ وَأَغْنِنِي بِفَضْلِكَ عَمَّنْ سِوَاكَ",
        "french": "Ô Allah, comble-moi par ce qui est licite, préserve-moi de ce qui est illicite, et rends-moi indépendant par Ta grâce de quiconque autre que Toi."
    },
    {
        "arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
        "french": "Notre Seigneur, accorde-nous une belle part en ce monde et une belle part dans l'au-delà, et préserve-nous du châtiment du Feu."
    },
    {
        "arabic": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ وَأَعُوذُ بِكَ مِنَ الْعَجْزِ وَالْكَسَلِ",
        "french": "Ô Allah, je cherche refuge en Toi contre l'inquiétude et la tristesse, et contre l'impuissance et la paresse."
    },
    {
        "arabic": "حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ",
        "french": "Allah me suffit. Il n'y a de dieu que Lui. En Lui je place ma confiance. Il est le Seigneur du Trône immense."
    },
    {
        "arabic": "اللَّهُمَّ يَسِّرْ وَلَا تُعَسِّرْ وَتَمِّمْ بِالْخَيْرِ",
        "french": "Ô Allah, facilite et ne complique pas, et achève par le bien."
    },
    {
        "arabic": "بِسْمِ اللهِ تَوَكَّلْتُ عَلَى اللهِ وَلَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللهِ",
        "french": "Au nom d'Allah, je place ma confiance en Allah. Il n'y a de force ni de puissance qu'en Allah."
    },
    {
        "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا طَيِّبًا وَعَمَلًا مُتَقَبَّلًا",
        "french": "Ô Allah, je Te demande un savoir utile, une subsistance bonne et une œuvre acceptée."
    },
]

TESTIMONIAL_KEYWORDS = [
    'merci', 'témoignage', 'incroyable', 'chapeau', 'bravo', 'félicitations',
    'j\'ai gagné', 'j\'ai pris', 'j\'ai fait', 'top merci', 'trop forte',
    'meilleure semaine', 'premier trade', 'grâce à toi', 'grace a toi',
    'j\'ai eu', 'on l\'a eu', 'j\'ai bien reçu',
]


def is_testimonial(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    matches = sum(1 for kw in TESTIMONIAL_KEYWORDS if kw in t)
    return matches >= 2


def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_state(state: dict):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass


# Slugs ForexFactory pour chaque instrument suivi
FF_INSTRUMENTS = [
    ('dxy',     'DXY',     '💵'),
    ('goldusd', 'XAU/USD', '🪙'),
    ('eurusd',  'EUR/USD', '💶'),
    ('ndx',     'NASDAQ',  '📊'),
    ('wtiusd',  'WTI OIL', '🛢️'),
]


def tv_bias(score) -> str:
    if score is None:
        return '—'
    if score >= 0.5:
        return '🟢 FORT HAUSSIER'
    elif score >= 0.1:
        return '📈 HAUSSIER'
    elif score <= -0.5:
        return '🔴 FORT BAISSIER'
    elif score <= -0.1:
        return '📉 BAISSIER'
    else:
        return '↔️ NEUTRE'


def _bias_text(score) -> str:
    if score is None: return '—'
    if score >= 0.5:  return 'FORT HAUSSIER'
    if score >= 0.1:  return 'HAUSSIER'
    if score <= -0.5: return 'FORT BAISSIER'
    if score <= -0.1: return 'BAISSIER'
    return 'NEUTRE'


def _bias_icon(score) -> str:
    if score is None: return ''
    if score >= 0.5:  return '🟢'
    if score >= 0.1:  return '📈'
    if score <= -0.5: return '🔴'
    if score <= -0.1: return '📉'
    return '↔️'


async def fetch_ff_bias(http, slug: str):
    """
    Retourne (d1_score, h4_score) en [-1, +1] depuis ForexFactory.
    Score = position du prix dans le range High/Low de la bougie.
    0 = bas du range (baissier), 1 = haut du range (haussier), centré sur 0.
    """
    try:
        url = f'https://www.forexfactory.com/market/{slug}'
        r = await http.get(url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120'},
            timeout=12, follow_redirects=True)
        text = r.text

        def _extract(tf):
            import re as _re
            m = _re.search(
                rf'"{tf}":\{{"(?:high|low)":([\d.]+),"(?:high|low|price)":([\d.]+),"(?:spread|high|low|price)":[^,]+[^}}]*"price":([\d.]+)',
                text
            )
            if not m:
                # Pattern alternatif
                m2 = _re.search(rf'"{tf}":\{{[^}}]+\}}', text)
                if not m2:
                    return None
                block = m2.group(0)
                h = _re.search(r'"high":([\d.]+)', block)
                l = _re.search(r'"low":([\d.]+)', block)
                p = _re.search(r'"price":([\d.]+)', block)
                if not (h and l and p):
                    return None
                high, low, price = float(h.group(1)), float(l.group(1)), float(p.group(1))
            else:
                high, low, price = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if high == low:
                return 0.0
            # Centré sur 0 : -1 (bas du range) à +1 (haut du range)
            return (price - low) / (high - low) * 2 - 1

        return _extract('D1'), _extract('H4')
    except Exception:
        return None, None


async def fetch_gold_levels(http) -> tuple:
    """
    Zones clés XAUUSD via Pivot Points sur les données Daily ForexFactory.
    Zone vente = R1 (résistance)  |  Zone achat = S1 (support)
    """
    try:
        import re as _re
        r = await http.get(
            'https://www.forexfactory.com/market/goldusd',
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120'},
            timeout=12, follow_redirects=True
        )
        m = _re.search(r'"D1":\{"high":([\d.]+),"price":([\d.]+),"spread":[^,]+,"low":([\d.]+)\}', r.text)
        if not m:
            return None, None

        H, L = float(m.group(1)), float(m.group(3))
        return str(round(H)), str(round(L))

    except Exception as e:
        log.error(f"[GOLD LEVELS] {e}")
        return None, None


def _score(val) -> str:
    """Convertit un score TradingView [-1, +1] en note /10."""
    if val is None:
        return '—'
    return f"{round((val + 1) / 2 * 10, 1)}/10"


_CURRENCY_FLAGS = {
    'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵',
    'AUD': '🇦🇺', 'NZD': '🇳🇿', 'CAD': '🇨🇦', 'CHF': '🇨🇭',
}

_CURRENCIES = list(_CURRENCY_FLAGS.keys())


def fetch_currency_strength_sync() -> dict:
    """Scrape les vraies forces depuis currencystrengthmeter.org via Playwright."""
    import re as _re
    from playwright.sync_api import sync_playwright

    result = {}
    try:
        launch_kwargs = {
            'headless': True,
            'args': ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        }
        # Sur Railway/Nix, utilise le chromium du système (dépendances déjà
        # résolues via RPATH) plutôt que le binaire téléchargé par Playwright,
        # qui casse dans ce type d'environnement (libs partagées introuvables).
        nix_chromium = shutil.which('chromium') or shutil.which('chromium-browser')
        if nix_chromium:
            launch_kwargs['executable_path'] = nix_chromium
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**launch_kwargs)
            page = browser.new_page()
            page.goto('https://currencystrengthmeter.org/', wait_until='networkidle', timeout=30000)
            html = page.content()
            browser.close()

        for cur in _CURRENCIES:
            m = _re.search(
                rf'class="title">\s*{cur}.*?height:\s*([\d.]+)%',
                html, _re.DOTALL
            )
            if m:
                result[cur] = round(float(m.group(1)) / 10, 1)
            else:
                result[cur] = None
                log.warning(f"[CURRENCY STRENGTH] Pas de match pour {cur}")
    except Exception as e:
        log.error(f"[CURRENCY STRENGTH] Scraping échoué : {e}")
        result = {c: None for c in _CURRENCIES}
    return result


async def fetch_currency_strength(http) -> dict:
    """Force /10 de chaque devise — scraping direct de currencystrengthmeter.org."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_currency_strength_sync)


async def _build_bias_message(http, now_paris) -> str:
    """Construit le texte de l'analyse marché (biais + scores)."""
    day_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    jour = day_fr[now_paris.weekday()]

    lines_d1 = []
    lines_h4 = []

    raw_d1 = []
    raw_h4 = []
    for slug, name, icon in FF_INSTRUMENTS:
        try:
            d1, h4 = await fetch_ff_bias(http, slug)
            raw_d1.append((d1 or 0, name, d1))
            raw_h4.append((name, h4, False))
        except Exception:
            raw_d1.append((0, name, None))
            raw_h4.append((name, None, False))

    # Daily — DXY en premier, reste trié par score décroissant
    def _bias_line(name, score):
        return f"{name:<9} {_bias_text(score):<14} {_bias_icon(score)}"
    raw_d1_sorted = sorted(raw_d1, key=lambda x: x[0], reverse=True)
    lines_d1 = []
    dxy_entry = next(((sc, n, s) for sc, n, s in raw_d1_sorted if n == 'DXY'), None)
    if dxy_entry:
        lines_d1.append(_bias_line('DXY', dxy_entry[2]))
        lines_d1.append('')
    lines_d1 += [_bias_line(n, s) for _, n, s in raw_d1_sorted if n != 'DXY']

    # H4 — même ordre que Daily, DXY toujours en premier avec saut de ligne
    h4_scores = {}
    for name, h4_score, _ in raw_h4:
        h4_scores[name] = h4_score

    lines_h4 = []
    # DXY en premier
    if 'DXY' in h4_scores:
        lines_h4.append(_bias_line('DXY', h4_scores['DXY']))
        lines_h4.append('')  # saut de ligne après DXY
    # Reste dans l'ordre Daily (sans DXY)
    for _, name, _ in raw_d1_sorted:
        if name != 'DXY' and name in h4_scores:
            lines_h4.append(_bias_line(name, h4_scores[name]))

    # Force des devises (28 paires agrégées) — triées par note décroissante
    strength = await fetch_currency_strength(http)
    order = ['USD', 'EUR', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF', 'JPY']
    sorted_curs = sorted(order, key=lambda c: strength.get(c) or 0, reverse=True)
    strength_lines = []
    for cur in sorted_curs:
        flag = _CURRENCY_FLAGS[cur]
        val = strength.get(cur)
        score_str = f"{val:.1f}/10" if val is not None else "  —  /10"
        strength_lines.append(f"{cur:<4} {score_str:>8}  {flag}")

    sell_lvl, buy_lvl = await fetch_gold_levels(http)

    gold_section = ""
    if sell_lvl or buy_lvl:
        gold_section = "\n\nXAUUSD — ZONES CLÉS"
        if sell_lvl:
            gold_section += f"\n🔴 Vente   : {sell_lvl}"
        if buy_lvl:
            gold_section += f"\n🟢 Achat   : {buy_lvl}"
        gold_section += "\n<i>(High / Low Daily — ForexFactory)</i>"

    updated_at = now_paris.strftime('%H:%M')
    intros = [
        f"Voilà ce que les marchés nous donnent ce matin. Lisez, analysez, et attendez votre setup. Pas de précipitation.",
        f"Le marché a parlé cette nuit. Voici ce que ça donne. Prenez le temps de lire avant d'ouvrir quoi que ce soit.",
        f"Avant de toucher à quoi que ce soit, lisez ça. L'analyse du jour est posée, c'est à vous de jouer.",
        f"Nouvelle journée, nouveau biais. On repart de zéro, on relit le marché, on attend la confirmation.",
    ]
    intro = intros[now_paris.weekday() % len(intros)]
    return (
        f"🔱 <b>ANALYSE DU MATIN — ELYT</b> — <i>{jour} {now_paris.strftime('%d/%m/%Y')}</i>\n\n"
        f"{intro}\n\n"
        "<b>Biais Daily</b>\n"
        "<pre>" + "\n".join(lines_d1) + "</pre>"
        "\n<b>Biais H4</b>\n"
        "<pre>" + "\n".join(lines_h4) + "</pre>"
        "\n<b>Force des devises</b>\n"
        "<pre>" + "\n".join(strength_lines) + "</pre>"
        + gold_section +
        f"\n\n<i>Mis à jour à {updated_at} — confirmez toujours sur vos graphiques</i>\n"
        "🧿 @elytsupport"
    )


async def send_market_bias(client, state: dict = None):
    """Envoie l'analyse marché et stocke les IDs de messages pour édition future."""
    try:
        now_paris = paris_now()
        # Pas d'analyse le week-end (marchés fermés, données stale)
        if now_paris.weekday() >= 5:
            log.info("[BIAIS] Week-end — analyse ignorée")
            return
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as http:
            msg = await _build_bias_message(http, now_paris)

        # Vérification : ne pas envoyer si toutes les données sont manquantes
        if msg.count('—') > 10:
            log.warning("[BIAIS] Trop de données manquantes — analyse non envoyée")
            return

        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        msg_ids = {}
        for group_id in targets:
            try:
                sent = await client.send_message(group_id, msg, parse_mode='html')
                msg_ids[str(group_id)] = sent.id
            except Exception as e:
                log.error(f"[BIAIS] Erreur groupe {group_id}: {e}")

        # Stocke les IDs pour mise à jour future
        if state is not None and msg_ids:
            state['bias_msg_ids'] = msg_ids
            _save_state(state)

        log.info(f"[BIAIS] Envoyé → {len(targets)} groupe(s)")

    except Exception as e:
        log.error(f"[BIAIS] Erreur: {e}")


async def update_market_bias(client, state: dict):
    """Édite les messages de biais existants (mise à jour H4 sans nouveau message)."""
    msg_ids = state.get('bias_msg_ids', {})
    if not msg_ids:
        return
    try:
        now_paris = paris_now()
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as http:
            msg = await _build_bias_message(http, now_paris)

        for group_id_str, message_id in msg_ids.items():
            try:
                await client.edit_message(int(group_id_str), message_id, msg, parse_mode='html')
            except Exception as e:
                log.error(f"[BIAIS UPDATE] Erreur groupe {group_id_str}: {e}")

        log.info("[BIAIS] Message mis à jour (H4)")

    except Exception as e:
        log.error(f"[BIAIS UPDATE] Erreur: {e}")


async def send_calendar(client):
    try:
        now_paris = paris_now()
        today = now_paris.strftime('%Y-%m-%d')

        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get('https://nfs.faireconomy.media/ff_calendar_thisweek.json')
            events = r.json()

        day_events = []
        for e in events:
            if not e.get('date', '').startswith(today):
                continue
            if e.get('impact', '') != 'High':
                continue
            day_events.append(e)

        if not day_events:
            return

        day_events.sort(key=lambda x: x.get('date', ''))

        day_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour = day_fr[now_paris.weekday()]

        lines = [f"📅 <b>CALENDRIER ÉCONOMIQUE — {jour} {now_paris.strftime('%d/%m/%Y')}</b>\n"]

        for e in day_events:
            currency = e.get('currency', '')
            flag = FLAGS.get(currency, '🌐')
            impact_icon = IMPACT.get(e.get('impact', ''), '⚪️')
            title = e.get('title', '')
            forecast = e.get('forecast', '')
            previous = e.get('previous', '')

            try:
                dt_utc = datetime.fromisoformat(e['date'].replace('Z', '+00:00'))
                # Convertir en heure Paris
                try:
                    from zoneinfo import ZoneInfo
                    dt_paris = dt_utc.astimezone(ZoneInfo('Europe/Paris'))
                except ImportError:
                    month = dt_utc.month
                    dt_paris = dt_utc + timedelta(hours=2 if 3 < month < 11 else 1)
                time_str = f"{dt_paris.strftime('%H:%M')} Paris"
            except Exception:
                time_str = ''

            line = f"{flag} {time_str} {impact_icon} <b>{title}</b>"
            if forecast or previous:
                details = []
                if forecast:
                    details.append(f"Prévu: {forecast}")
                if previous:
                    details.append(f"Préc: {previous}")
                line += f"\n    └ {' | '.join(details)}"
            lines.append(line)

        msg = '\n'.join(lines)
        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        for group_id in targets:
            try:
                await client.send_message(group_id, msg, parse_mode='html')
            except Exception as e:
                log.error(f"[CALENDRIER] Erreur groupe {group_id}: {e}")
        log.info(f"[CALENDRIER] Envoyé → {len(targets)} groupe(s)")

    except Exception as e:
        log.error(f"[CALENDRIER] Erreur: {e}")


async def send_asian_killzone(client):
    """Message Asian Killzone — 2h00 Paris."""
    try:
        msg = (
            "🇯🇵 <b>ASIAN KILLZONE — 2H00</b>\n\n"
            "La session asiatique est ouverte. Liquidité faible, mouvements lents — "
            "c'est la période où les institutions posent leurs ordres discrètement.\n\n"
            "Pas de trades impulsifs. On observe, on note les niveaux, "
            "on prépare les setups pour Londres.\n\n"
            "<i>Patience. La vraie action commence à Londres.</i>\n\n"
            "🧿 @elytsupport"
        )
        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        for gid in targets:
            await client.send_message(gid, msg, parse_mode='html')
        log.info("[ASIAN KZ] Envoyé")
    except Exception as e:
        log.error(f"[ASIAN KZ] Erreur: {e}")


async def send_london_killzone(client):
    """Message London Killzone — 8h00 Paris."""
    try:
        msg = (
            "🇬🇧 <b>LONDON KILLZONE — 8H00</b>\n\n"
            "La liquidité entre sur le marché. "
            "C'est maintenant que les vraies positions s'ouvrent.\n\n"
            "Pas de précipitation. On attend la structure, on attend la confirmation. "
            "Un bon setup vaut mieux que trois mauvaises entrées.\n\n"
            "<i>Disciplinés. Patients. Décisifs.</i>\n\n"
            "🧿 @elytsupport"
        )
        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        for gid in targets:
            await client.send_message(gid, msg, parse_mode='html')
        log.info("[LONDON KZ] Envoyé")
    except Exception as e:
        log.error(f"[LONDON KZ] Erreur: {e}")


async def send_newyork_killzone(client):
    """Message New York Killzone — 13h00 Paris."""
    try:
        msg = (
            "🇺🇸 <b>NEW YORK KILLZONE — 13H00</b>\n\n"
            "Wall Street ouvre. Le volume explose. "
            "C'est la session la plus volatile de la journée.\n\n"
            "Les setups London qui n'ont pas encore bougé peuvent se déclencher maintenant. "
            "Restez sur vos niveaux — pas de chasse, pas d'improvisation.\n\n"
            "<i>Concentration maximale. C'est maintenant que ça se joue.</i>\n\n"
            "🧿 @elytsupport"
        )
        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        for gid in targets:
            await client.send_message(gid, msg, parse_mode='html')
        log.info("[NY KZ] Envoyé")
    except Exception as e:
        log.error(f"[NY KZ] Erreur: {e}")


async def send_morning_dua(client):
    """Envoie une dou'a aléatoire chaque matin dans les deux groupes."""
    try:
        dua = random.choice(MORNING_DUAS)
        msg = (
            f"🤲 <b>DOU'A DU MATIN</b>\n\n"
            f"「 {dua['arabic']} 」\n\n"
            f"\n"
            f"<i>{dua['french']}</i>\n\n"
            f"Que Allah bénisse votre journée et vos échanges 🤍"
        )
        targets = getattr(config, 'MORNING_TARGETS', [config.TARGET_GROUP_ID])
        for gid in targets:
            try:
                await client.send_message(gid, msg, parse_mode='html')
            except Exception as e:
                log.error(f"[DOU'A] Erreur groupe {gid}: {e}")
        log.info("[DOU'A] Envoyée")
    except Exception as e:
        log.error(f"[DOU'A] Erreur: {e}")


async def send_islamic_quote(client):
    try:
        q = random.choice(ISLAMIC_QUOTES)
        msg = (
            f"✨ {q['type']}\n\n"
            f"{q['arabic']}\n\n"
            f"« {q['french']} »\n\n"
            f"{q['source']}\n\n"
            f"Que Allah bénisse votre journée et vos échanges 🤲"
        )
        await client.send_message(config.TARGET_GROUP_ID, msg)
        log.info("[CITATION] Envoyée")
    except Exception as e:
        log.error(f"[CITATION] Erreur: {e}")


SAMEDI_MESSAGES = [
    "🌴 <b>SAMEDI BIEN MÉRITÉ — ELYT</b>\n\nLes marchés sont fermés. La team, elle, est toujours là.\n\nCe week-end c'est repos, réflexion, ressourcement. On a bossé toute la semaine — on mérite de souffler.\n\nProfitez de votre famille, de vos proches. Revenez lundi avec la tête reposée et les yeux frais sur les graphiques.\n\n<i>Bon week-end à toute la team elyt</i> 🤍\n\n🧿 @elytsupport",

    "☀️ <b>BON SAMEDI LA TEAM — ELYT</b>\n\nLes marchés dorment. Vous pouvez en faire autant.\n\nLe trading c'est aussi savoir s'arrêter. Ceux qui durent dans ce métier sont ceux qui savent récupérer mentalement.\n\nAujourd'hui : pas de graphiques, pas de stress. Juste vous.\n\n<i>À lundi, reposés et prêts</i> 💪\n\n🧿 @elytsupport",

    "🔱 <b>PAUSE MÉRITÉE — ELYT</b>\n\nSemaine intense derrière nous. Marchés fermés devant nous.\n\nC'est le moment de recharger les batteries. Un trader reposé prend de meilleures décisions qu'un trader épuisé — c'est aussi simple que ça.\n\nProfitez du calme. On revient lundi avec l'analyse et les setups de la semaine.\n\n<i>Bon week-end à tous</i> 🤍\n\n🧿 @elytsupport",

    "🌅 <b>LE WEEK-END COMMENCE — ELYT</b>\n\nMarchés fermés. Esprits libres.\n\nCe moment de calme c'est précieux. Profitez-en pour vous ressourcer, passer du temps avec ceux qui comptent, vous rappeler pourquoi vous tradez.\n\nLundi on repart, plus forts et plus concentrés.\n\n<i>Toute la team elyt vous souhaite un excellent week-end</i> 🤍\n\n🧿 @elytsupport",

    "🌅 <b><i>SAMEDI COMMENCE...</i></b>\n\n⏳ Et 24h sont devant nous pour faire ce qui nous donne un maximum <u>d'énergie</u>.\n\nAlors pourquoi pas <u>poser le téléphone</u>, fermer les graphiques...\n\n➡️ Et se focus à 100% sur <u>l'instant présent</u> ?\n\n<blockquote>Car si on se reconnecte maintenant, lundi on arrivera complètement rechargés et prêts mentalement.</blockquote>\n\n<b>BON SAMEDI À TOUS</b> 🧡\n\n🧿 @elytsupport",
]


async def send_samedi_community(client):
    """Message de communauté le samedi matin."""
    try:
        now = paris_now()
        msg = SAMEDI_MESSAGES[now.day % len(SAMEDI_MESSAGES)]
        await client.send_message(config.TARGET_GROUP_ID, msg, parse_mode='html')
        log.info("[SAMEDI] Message communauté envoyé")
    except Exception as e:
        log.error(f"[SAMEDI] Erreur: {e}")


async def check_tradingview_ideas(client, state: dict):
    """
    Vérifie le flux RSS TradingView de chaque auteur surveillé.
    Si une nouvelle idée est détectée, télécharge l'image du graphique
    et l'envoie dans le groupe public sous le nom ELYT, sans aucune trace de l'auteur.
    """
    import xml.etree.ElementTree as ET
    import re as _re

    for username in []:
        try:
            url = f"https://www.tradingview.com/feed/?author={username}&type=chart"
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as http:
                r = await http.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code != 200:
                    continue

                root = ET.fromstring(r.text)
                channel = root.find('channel')
                if channel is None:
                    continue
                items = channel.findall('item')
                if not items:
                    continue

                latest = items[0]
                guid = (latest.findtext('guid') or latest.findtext('link') or '').strip()
                if not guid:
                    continue

                state_key = f"tv_idea_{username}"
                if state.get(state_key) == guid:
                    continue  # déjà envoyé

                title = (latest.findtext('title') or 'Analyse technique').strip()

                # Extrait l'image du graphique depuis content:encoded
                encoded_el = latest.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                encoded_html = encoded_el.text if encoded_el is not None else ''

                img_url = None
                # Pattern : <img src="https://s3.tradingview.com/u/XXXXXXXX_mid.png"/>
                m = _re.search(r'<img src="(https://s3\.tradingview\.com/u/[^"]+_mid\.png)"', encoded_html)
                if m:
                    img_url = m.group(1)
                else:
                    # Fallback : extraire l'ID depuis l'URL de l'idée
                    chart_id_m = _re.search(r'/chart/[^/]+/([A-Za-z0-9]+)-', guid)
                    if chart_id_m:
                        img_url = f"https://s3.tradingview.com/u/{chart_id_m.group(1)}_mid.png"

                # Caption ELYT — aucune mention de l'auteur ni de lien
                caption = (
                    f"📊 <b>ANALYSE TECHNIQUE — ELYT</b>\n\n"
                    f"<b>{title}</b>\n\n"
                    f"Lisez le graphique avant d'ouvrir une position. "
                    f"Attendez toujours la confirmation avant d'entrer.\n\n"
                    f"🧿 @elytsupport"
                )

                # Récupère l'image via og:image de la page (avec Referer pour contourner le 403 S3)
                idea_url = latest.findtext('link') or guid
                TV_HEADERS = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Referer': 'https://www.tradingview.com/',
                }
                page_r = await http.get(idea_url, headers=TV_HEADERS)
                og_m = _re.search(r'<meta property="og:image" content="([^"]+)"', page_r.text)
                if og_m:
                    img_url = og_m.group(1)

                if img_url:
                    img_r = await http.get(img_url, headers=TV_HEADERS)
                    if img_r.status_code == 200 and len(img_r.content) > 10000:
                        await client.send_file(
                            config.TARGET_GROUP_ID,
                            img_r.content,
                            caption=caption,
                            parse_mode='html',
                        )
                    else:
                        await client.send_message(config.TARGET_GROUP_ID, caption, parse_mode='html', link_preview=False)
                else:
                    await client.send_message(config.TARGET_GROUP_ID, caption, parse_mode='html', link_preview=False)

                state[state_key] = guid
                _save_state(state)
                log.info(f"[TV WATCH] Nouvelle analyse publiée: {title[:60]}")

        except Exception as e:
            log.error(f"[TV WATCH] Erreur {username}: {e}")


async def run_scheduler(client):
    """Planificateur robuste : envoie les tâches manquées au redémarrage."""
    log.info("🗓️ Planificateur démarré")

    state = _load_state()

    while True:
        now = paris_now()
        today = now.strftime('%Y-%m-%d')
        h = now.hour
        weekday = now.weekday()

        # Supprime les clés d'anciens jours (sauf bias_msg_ids qui sert toute la journée)
        for key in list(state.keys()):
            if key == 'bias_msg_ids':
                continue
            if not key.startswith(today):
                del state[key]

        # 7h00 — Biais marché + Calendrier économique (envoi initial)
        key_morning = f"{today}_morning"
        if h >= 7 and key_morning not in state:
            await send_market_bias(client, state)
            await send_calendar(client)
            await send_morning_dua(client)
            state[key_morning] = True
            _save_state(state)

        # 2h00 — Asian Killzone (seulement entre 2h et 4h pour éviter le rattrapage tardif)
        key_asian = f"{today}_asian"
        if 2 <= h < 5 and key_asian not in state:
            await send_asian_killzone(client)
            state[key_asian] = True
            _save_state(state)
        elif h >= 5 and key_asian not in state:
            state[key_asian] = True  # marquer comme fait sans envoyer

        # 8h00 — London Killzone + Citation islamique
        key_london = f"{today}_london"
        if h >= 8 and key_london not in state:
            await send_london_killzone(client)
            state[key_london] = True
            _save_state(state)

        # 13h00 — New York Killzone
        key_ny = f"{today}_newyork"
        if h >= 13 and key_ny not in state:
            await send_newyork_killzone(client)
            state[key_ny] = True
            _save_state(state)

        key_quote_am = f"{today}_quote_am"
        if h >= 8 and key_quote_am not in state:
            await send_islamic_quote(client)
            state[key_quote_am] = True
            _save_state(state)

        # Mises à jour H4 : 11h, 15h, 19h, 23h — édite le message existant
        for update_h in [11, 15, 19, 23]:
            key_h4 = f"{today}_h4update_{update_h}"
            if h >= update_h and key_h4 not in state:
                await update_market_bias(client, state)
                state[key_h4] = True
                _save_state(state)

        # 1er du mois 10h — Relance mensuelle
        key_monthly = f"{today}_monthly_relance"
        if now.day == 1 and h >= 10 and key_monthly not in state:
            await send_monthly_relance(client)
            state[key_monthly] = True
            _save_state(state)

        # 18h00 — Relance quotidienne places VIP
        key_relance = f"{today}_relance"
        if h >= 18 and key_relance not in state:
            await send_daily_relance(client)
            state[key_relance] = True
            _save_state(state)

        # 19h00 vendredi — Relance weekly (bilan désactivé)
        key_bilan = f"{today}_bilan"
        if h >= 19 and weekday == 4 and key_bilan not in state:
            await send_weekly_relance(client)
            state[key_bilan] = True
            _save_state(state)

        # 20h00 — Citation islamique du soir
        key_quote_pm = f"{today}_quote_pm"
        if h >= 20 and key_quote_pm not in state:
            await send_islamic_quote(client)
            state[key_quote_pm] = True
            _save_state(state)

        # 10h00 samedi — Message de communauté
        key_samedi = f"{today}_samedi"
        if weekday == 5 and h >= 10 and key_samedi not in state:
            await send_samedi_community(client)
            state[key_samedi] = True
            _save_state(state)

        await asyncio.sleep(30)
