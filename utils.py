import random
import logging
import csv
import os
from datetime import datetime
from config import OPPORTUNITIES_CSV, SECURE_WALLET_ADDRESS, WALLET_ADDRESS, PROFIT_TRANSFER_THRESHOLD, PROFIT_TRANSFER_PERCENTAGE  # Ajout des nouvelles variables

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Définition des frais par exchange
EXCHANGE_FEES = {
    "binance": 0.1 / 100,  # 0.1% par trade
    "kucoin": 0.1 / 100,
    "gateio": 0.2 / 100,
}

def get_prices():
    """
    Simule l'obtention des prix des exchanges. Dans la version finale, ce serait des API requests.
    """
    prices = {
        "binance": round(random.uniform(20.5, 21.5), 3),
        "kucoin": round(random.uniform(20.5, 21.5), 3),
        "gateio": round(random.uniform(20.5, 21.5), 3),
    }
    logging.info(f"📊 Prix actuels simulés: {prices}")
    return prices

def calculate_fees(amount, buy_price, sell_price, buy_exchange, sell_exchange):
    """
    Calcule les frais totaux du trade en fonction des exchanges utilisés.
    """
    buy_fee = amount * buy_price * EXCHANGE_FEES.get(buy_exchange, 0)
    sell_fee = amount * sell_price * EXCHANGE_FEES.get(sell_exchange, 0)
    total_fees = buy_fee + sell_fee
    logging.info(f"💰 Frais estimés: {total_fees:.3f} USDT ({buy_exchange}: {buy_fee:.3f}, {sell_exchange}: {sell_fee:.3f})")
    return total_fees

def calculate_roi(amount, buy_price, sell_price, buy_exchange, sell_exchange):
    """
    Calcule le ROI du trade après prise en compte des frais.
    """
    gross_profit = (sell_price - buy_price) * amount
    total_fees = calculate_fees(amount, buy_price, sell_price, buy_exchange, sell_exchange)
    net_profit = gross_profit - total_fees
    roi = (net_profit / (amount * buy_price)) * 100  # ROI en pourcentage
    logging.info(f"📈 ROI estimé: {roi:.2f}% | Profit net: {net_profit:.3f} USDT | Profit brut: {gross_profit:.3f} USDT")
    return gross_profit, total_fees, net_profit, roi

def send_profits_to_secure_wallet(profit):
    """
    Transfère automatiquement une partie des profits vers un wallet sécurisé.
    """
    if profit >= PROFIT_TRANSFER_THRESHOLD:
        amount_to_transfer = (profit * PROFIT_TRANSFER_PERCENTAGE) / 100
        logging.info(f"🔄 Transfert automatique de {amount_to_transfer:.2f} USDT vers le wallet sécurisé {SECURE_WALLET_ADDRESS} 🔒")
        # Ici, on ajouterait la logique pour envoyer la transaction réelle sur la blockchain
        return True
    return False

def save_opportunity_to_csv(timestamp, buy_exchange, sell_exchange, buy_price, sell_price, spread, gross_profit, total_fees, net_profit, roi):
    """
    Sauvegarde une opportunité d'arbitrage dans un fichier CSV pour analyse future.
    """
    file_exists = os.path.isfile(OPPORTUNITIES_CSV)
    with open(OPPORTUNITIES_CSV, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Date", "Buy Exchange", "Sell Exchange", "Buy Price", "Sell Price", "Spread (%)", "Profit Brut (USDT)", "Frais Totaux (USDT)", "Profit Net (USDT)", "ROI (%)"])
        writer.writerow([timestamp, buy_exchange, sell_exchange, buy_price, sell_price, spread, gross_profit, total_fees, net_profit, roi])
    logging.info(f"📂 Opportunité enregistrée dans {OPPORTUNITIES_CSV} ✅")

def execute_trade(amount, buy_exchange, sell_exchange, buy_price, sell_price, spread):
    """
    Simule l'exécution d'un trade avec des ordres limit.
    """
    logging.info(f"📢 Tentative d'achat sur {buy_exchange} à {buy_price:.3f} USDT en Limit Order...")
    success_buy = random.choices([True, False], weights=[85, 15])[0]  # 85% chance de succès
    
    if not success_buy:
        logging.warning("❌ Achat échoué, opportunité perdue.")
        return False

    logging.info(f"✅ Achat réussi ! {amount} AVAX acheté sur {buy_exchange} à {buy_price:.3f} USDT.")

    logging.info(f"📢 Tentative de vente sur {sell_exchange} à {sell_price:.3f} USDT en Limit Order...")
    success_sell = random.choices([True, False], weights=[90, 10])[0]  # 90% chance de succès
    
    if not success_sell:
        logging.warning("❌ Vente échouée, risque de perte minimisé.")
        return False

    logging.info(f"✅ Vente réussie ! {amount} AVAX vendu sur {sell_exchange} à {sell_price:.3f} USDT.")
    
    # Calcul des profits et frais
    gross_profit, total_fees, net_profit, roi = calculate_roi(amount, buy_price, sell_price, buy_exchange, sell_exchange)

    # Enregistrer l'opportunité si le trade a réussi
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_opportunity_to_csv(timestamp, buy_exchange, sell_exchange, buy_price, sell_price, spread, gross_profit, total_fees, net_profit, roi)

    if net_profit > 0:
        logging.info(f"🎉 **TRADE COMPLETÉ AVEC SUCCÈS !** 💰 Profit net: {net_profit:.3f} USDT | ROI: {roi:.2f}% ✅")

        # **Transfert automatique des profits**
        send_profits_to_secure_wallet(net_profit)
        return True
    else:
        logging.info(f"⚠️ **TRADE NON RENTABLE** | Perte estimée: {net_profit:.3f} USDT ❌")
        return False
