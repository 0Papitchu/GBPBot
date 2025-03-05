import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Fonction pour récupérer une variable d'environnement avec gestion des erreurs et conversion
def get_env_variable(var_name, default=None, cast_type=str, sensitive=False):
    """
    Récupère une variable d'environnement avec gestion des erreurs et conversion de type.

    :param var_name: Nom de la variable d'environnement
    :param default: Valeur par défaut si la variable est absente
    :param cast_type: Type de conversion attendu (str, int, float, bool)
    :param sensitive: Masquer la valeur dans les logs si sensible (ex: clés privées)
    :return: La valeur convertie de la variable d'environnement
    """
    value = os.getenv(var_name, default)
    
    if value is None:
        raise ValueError(f"❌ ERREUR: La variable d'environnement '{var_name}' est manquante.")

    try:
        converted_value = cast_type(value)
    except ValueError:
        raise ValueError(f"❌ ERREUR: Impossible de convertir '{var_name}' en {cast_type.__name__}.")

    if not sensitive:
        print(f"✅ {var_name}: {converted_value}")  # Affichage uniquement pour les valeurs non sensibles

    return converted_value

# 🔹 Paramètres de connexion blockchain
PRIVATE_KEY = get_env_variable("PRIVATE_KEY", sensitive=True)  # Clé privée masquée
WALLET_ADDRESS = get_env_variable("WALLET_ADDRESS")
RPC_URL = get_env_variable("RPC_URL")

# 🔹 Seuil minimum pour un arbitrage rentable (exprimé en %)
ARBITRAGE_THRESHOLD = get_env_variable("ARBITRAGE_THRESHOLD", 4.0, float)  # % d'écart minimum

# 🔹 Temps d'attente entre chaque scan (en secondes) pour ajuster la réactivité
SLEEP_TIME = get_env_variable("SLEEP_TIME", 5, int)  

# 🔹 Estimation des frais (mise à jour automatique)
GAS_ESTIMATION = get_env_variable("GAS_ESTIMATION", 0.001, float)  # AVAX
DEX_FEE_ESTIMATION = get_env_variable("DEX_FEE_ESTIMATION", 0.002, float)  # Frais des échanges centralisés

# 🔹 Attente maximum pour la confirmation d'une transaction (en secondes)
MAX_WAIT_CONFIRMATION = get_env_variable("MAX_WAIT_CONFIRMATION", 90, int)

# 🔹 Fichier pour enregistrer les opportunités détectées
OPPORTUNITIES_CSV = get_env_variable("OPPORTUNITIES_CSV", "opportunities.csv")

# 🔹 Montant du trade
TRADE_AMOUNT = get_env_variable("TRADE_AMOUNT", 5, float)  # Montant en AVAX par trade

# 🔹 Gestion des profits (wallet sécurisé)
PROFIT_TRANSFER_THRESHOLD = get_env_variable("PROFIT_TRANSFER_THRESHOLD", 10.0, float)  # 10 USDT avant transfert
PROFIT_TRANSFER_PERCENTAGE = get_env_variable("PROFIT_TRANSFER_PERCENTAGE", 30.0, float)  # 30% des profits transférés
SECURE_WALLET_ADDRESS = get_env_variable("SECURE_WALLET_ADDRESS")  # Adresse du wallet sécurisé

# 🔹 Configuration de la base de données
DB_TYPE = get_env_variable("DB_TYPE", "sqlite", str)  # "sqlite" ou "postgresql"
DB_HOST = get_env_variable("DB_HOST", "localhost", str) if DB_TYPE == "postgresql" else None
DB_PORT = get_env_variable("DB_PORT", 5432, int) if DB_TYPE == "postgresql" else None
DB_NAME = get_env_variable("DB_NAME", "memescan", str) if DB_TYPE == "postgresql" else "simulation.db"
DB_USER = get_env_variable("DB_USER", "postgres", str) if DB_TYPE == "postgresql" else None
DB_PASSWORD = get_env_variable("DB_PASSWORD", "", str, sensitive=True) if DB_TYPE == "postgresql" else None

# ✅ Confirmation du chargement réussi
print("✅ Configuration chargée avec succès !")
