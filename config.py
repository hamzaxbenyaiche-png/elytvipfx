# ─────────────────────────────────────────────
#  CONFIGURATION — à remplir avant de lancer
# ─────────────────────────────────────────────

# 1. Va sur https://my.telegram.org → "API development tools"
#    Crée une application et copie les valeurs ci-dessous
API_ID   = 2040          # Remplace par ton api_id (entier)
API_HASH = "b18441a1ff607e10a989891a5462e627"         # Remplace par ton api_hash (chaîne)

# 2. Ton numéro de téléphone (avec indicatif, ex: +33612345678)
PHONE_NUMBER = ""

# 3. ID du groupe cible où tous les messages seront copiés.
#    Met 0 pour lancer en mode "liste mes groupes" et trouver l'ID.
#    Les IDs de groupes/canaux sont souvent négatifs, ex: -1001234567890
TARGET_GROUP_ID = -5471330752

# Groupe VIP — reçoit l'analyse du matin + signaux exclusifs
VIP_GROUP_ID = -5266664273  # VIP // elyt fx

# Groupes qui reçoivent l'analyse du matin (biais Daily + H4)
MORNING_TARGETS = [
    TARGET_GROUP_ID,
    VIP_GROUP_ID,
]

# Groupes dont les signaux sont envoyés UNIQUEMENT dans le VIP (rien d'autre)
VIP_SIGNAL_SOURCES = [
    -1002162787370,  # NABIL FX CAPITAL (alias "N.M CAPITAL")
    -1001302635479,  # Hunt Money
]

# Groupes dont TOUS les messages sont partagés tel quel (pas seulement les signaux)
FULL_SHARE_SOURCES = [
    -1001240377623,  # Fondamental & News
    -1001656697308,  # Fondamentale Trader
]

# ─────────────────────────────────────────────
#  OPTIONS
# ─────────────────────────────────────────────

# Ajouter un header "📨 Groupe | Auteur" avant chaque message
ADD_HEADER = True

# Transférer aussi les médias (photos, vidéos, fichiers)
FORWARD_MEDIA = True

# Groupes autorisés (whitelist) — seuls ces groupes seront copiés
# Laisser vide [] pour copier tous les groupes sauf les exclus
ALLOWED_GROUPS = [
    -1002162787370,  # NABIL FX CAPITAL
    -1001932728357,  # CANAL HUGOFX
    -1001592589111,  # Elliot Hewitt - YoungTraderWealth
    -1002683242499,  # Don Trading [FREE]
    -1002539936877,  # Paloma TRD
    -1003182274176,  # Smart Success
    -1002665400992,  # SLM FOREX
    -1003440574851,  # LeNass
    -1001639216577,  # Taurus Analysis
    -1001268620468,  # Infositons
    -1001656697308,  # Fondamentale Trader
    -1001240377623,  # Fondamental & News
    -1002974026900,  # The Quant Room FX
    -1003876279212,  # Aupa Traders
    -1001327630851,  # FinancialJuice
    -1001302635479,  # Hunt Money
    # -1001785197109,  # AnabelSignals (retiré)
    -1001662267019,  # EliteTradingSignals
    -1001215049720,  # UnitedSignals
    -1001868019139,  # Gold Signals VIP
    -1001757977653,  # SHY TRADING ✨
    -1001624798634,  # Kasper Trading
    -1001777355266,  # Impact Trading
    -1002769656480,  # TriadFx
    -1002489151772,  # Anesaurus Signals
]

# Groupes dont les messages sont envoyés avec alerte rouge ⚠️
ALERT_GROUPS = [
    -1001327630851,  # FinancialJuice
]

# Mots/noms à remplacer par "elyt" dans le contenu des messages
# Ajoute ici tous les noms de concurrents, groupes, personnes à masquer
BLACKLIST = [
    # Noms des groupes sources
    "NABIL FX CAPITAL", "Nabil FX", "Nabil",
    "CANAL HUGOFX", "HugoFX", "Hugo FX",
    "YoungTraderWealth", "Elliot Hewitt",
    "Don Trading",
    "Paloma TRD", "Paloma",
    "Smart Success",
    "SLM FOREX", "SLM",
    "LeNass", "Le Nass", "Nass",
    "Taurus Analysis", "Taurus",
    "Infositons",
    "Formation Trading",
    "Fondamentale Trader", "Fondamentale",
    "Fondamental & News", "Fondamental",
    "The Quant Room", "Quant Room",
    "Aupa Traders", "Aupa",
    "Hunt Money",
    "AnabelSignals", "Anabel",
    "EliteTradingSignals", "Elite Trading",
    "UnitedSignals", "United Signals",
    "Gold Signals VIP",
    "SHY TRADING", "Shy Trading", "Shy",
    "Kasper Trading", "Kasper",
    "Impact Trading",
    "TriadFx", "Triad Fx", "Triad",
    "Anesaurus Signals", "Anesaurus",
    # Groupes exclus
    "FUNDIFY", "Fundify",
    "Gold Sniper",
    "GoldChirurgie",
    # Blacklist manuelle
    "NABIL FX POOL", "BARA", "palo", "Palo",
    # Noms propres détectés dans les messages
    "XauBara", "Xaubara",
]

# Groupes à ne jamais copier
EXCLUDED_GROUPS = [
    -1002982772021,  # FUNDIFY
    -1002713730505,  # Gold Sniper
    -1002920873890,  # GoldChirurgie
    -1001214412958,  # Formation Trading
    7513090900,      # David - Fundify
]
