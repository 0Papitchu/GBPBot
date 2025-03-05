import time
import logging
import csv
import os
from datetime import datetime, timedelta
from utils import (
    get_prices, calculate_fees, execute_trade, calculate_roi, send_profits_to_secure_wallet
)
from config import (
    ARBITRAGE_THRESHOLD, SLEEP_TIME, OPPORTUNITIES_CSV, TRADE_AMOUNT,
    MAX_WAIT_CONFIRMATION, PROFIT_TRANSFER_THRESHOLD, PROFIT_TRANSFER_PERCENTAGE
)

# Configuration du logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Vérifier si le fichier CSV existe et ajouter l'en-tête si nécessaire
if not os.path.isfile(OPPORTUNITIES_CSV):
    with open(OPPORTUNITIES_CSV, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Date", "Buy Exchange", "Sell Exchange", "Buy Price", "Sell Price",
            "Spread (%)", "Profit Brut (USDT)", "Frais Totaux (USDT)", "Profit Net (USDT)", "ROI (%)"
        ])

def load_recent_opportunities():
    """
    Charge les 20 dernières opportunités pour éviter les doublons.
    """
    recent_opportunities = []
    if os.path.isfile(OPPORTUNITIES_CSV):
        with open(OPPORTUNITIES_CSV, mode="r") as file:
            reader = list(csv.reader(file))
            data = reader[1:]  # Sauter l'en-tête
            for row in data[-20:]:  # On ne prend que les 20 dernières entrées
                try:
                    entry = {
                        "Date": datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S"),
                        "Buy Exchange": row[1],
                        "Sell Exchange": row[2],
                        "Buy Price": float(row[3]),
                        "Sell Price": float(row[4])
                    }
                    recent_opportunities.append(entry)
                except ValueError:
                    continue  # Ignorer les lignes corrompues
    return recent_opportunities

def is_duplicate_opportunity(buy_exchange, sell_exchange, buy_price, sell_price):
    """
    Vérifie si une opportunité similaire a déjà été détectée récemment.
    """
    recent_opportunities = load_recent_opportunities()
    now = datetime.now()
    for entry in recent_opportunities:
        if (
            entry["Buy Exchange"] == buy_exchange and
            entry["Sell Exchange"] == sell_exchange and
            abs(entry["Buy Price"] - buy_price) < 0.01 and
            abs(entry["Sell Price"] - sell_price) < 0.01 and
            (now - entry["Date"]) < timedelta(minutes=10)
        ):
            return True  # Opportunité déjà détectée récemment
    return False

def log_arbitrage_opportunity(buy_exchange, sell_exchange, buy_price, sell_price, spread, profit_brut, frais_totaux, profit_net, roi):
    """
    Enregistre une opportunité d'arbitrage dans le CSV.
    """
    if is_duplicate_opportunity(buy_exchange, sell_exchange, buy_price, sell_price):
        logging.info("⚠️ Opportunité déjà détectée récemment, non enregistrée.")
        return
    with open(OPPORTUNITIES_CSV, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), buy_exchange, sell_exchange,
            buy_price, sell_price, spread, profit_brut, frais_totaux, profit_net, roi
        ])
    logging.info(f"📂 Opportunité enregistrée dans {OPPORTUNITIES_CSV} ✅")

def find_arbitrage_opportunity(prices):
    """
    Identifie les opportunités d'arbitrage en comparant les prix sur différents exchanges.
    """
    best_buy_exchange = min(prices, key=prices.get)
    best_sell_exchange = max(prices, key=prices.get)
    
    buy_price = prices[best_buy_exchange]
    sell_price = prices[best_sell_exchange]
    spread = ((sell_price - buy_price) / buy_price) * 100

    if spread >= ARBITRAGE_THRESHOLD:
        logging.info("\n🚀 Opportunité d'arbitrage détectée ! 🚀")
        logging.info(f"Acheter sur {best_buy_exchange} à {buy_price:.3f} USDT")
        logging.info(f"Vendre sur {best_sell_exchange} à {sell_price:.3f} USDT")
        logging.info(f"Écart potentiel : {spread:.2f}%")

        # Simulation de trade avec montant configurable
        simulate_trade(TRADE_AMOUNT, buy_price, sell_price, best_buy_exchange, best_sell_exchange, spread)
    else:
        logging.debug(f"🔍 Aucune opportunité rentable détectée. (Écart : {spread:.2f}%)")

def simulate_trade(amount, buy_price, sell_price, buy_exchange, sell_exchange, spread):
    """
    Simule un trade d'arbitrage avec gestion automatique des profits.
    """
    gross_profit, total_fees, net_profit, roi = calculate_roi(amount, buy_price, sell_price, buy_exchange, sell_exchange)
    logging.info(f"\n💰 Simulation Trade ({amount} AVAX) 💰")
    logging.info(f"Achat sur {buy_exchange} à {buy_price:.3f} USDT")
    logging.info(f"Vente sur {sell_exchange} à {sell_price:.3f} USDT")
    logging.info(f"Profit brut estimé : {gross_profit:.3f} USDT")
    logging.info(f"Frais estimés : {total_fees:.3f} USDT")
    logging.info(f"Profit net après frais : {net_profit:.3f} USDT")
    logging.info(f"📈 ROI estimé : {roi:.2f}%")

    # Enregistrer l'opportunité
    log_arbitrage_opportunity(buy_exchange, sell_exchange, buy_price, sell_price, spread, gross_profit, total_fees, net_profit, roi)

    # Vérifier si le trade est rentable
    if net_profit > 0:
        logging.info("✅ Trade RENTABLE détecté, EXÉCUTION...")
        execute_trade(amount, buy_exchange, sell_exchange, buy_price, sell_price, spread)

        # **💰 Vérification des profits pour transfert automatique**
        if net_profit >= PROFIT_TRANSFER_THRESHOLD:
            transfer_amount = net_profit * (PROFIT_TRANSFER_PERCENTAGE / 100)
            logging.info(f"🔄 Transfert automatique des profits ({transfer_amount:.3f} USDT) en cours...")
            send_profits_to_secure_wallet(transfer_amount)

if __name__ == "__main__":
    logging.info("🚀 Démarrage du bot d'arbitrage...\n")
    while True:
        try:
            prices = get_prices()
            find_arbitrage_opportunity(prices)
            time.sleep(SLEEP_TIME)
        except KeyboardInterrupt:
            logging.info("🛑 Bot arrêté manuellement.")
            break
        except Exception as e:
            logging.error(f"⚠️ Erreur inattendue : {e}")
