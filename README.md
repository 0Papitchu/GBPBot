# GBPBot - Trading Bot pour MEME coins

<div align="center">
    <img src="docs/images/logo.png" alt="GBPBot Logo" width="200" height="200" />
    <h3>Trading ultra-rapide et intelligent pour Solana, AVAX et Sonic</h3>
</div>

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Version](https://img.shields.io/badge/version-0.1.0-green)

GBPBot est un bot de trading avancé conçu pour maximiser les profits dans l'écosystème des MEME coins sur Solana, AVAX et Sonic. Il intègre des fonctionnalités d'arbitrage, de sniping et de MEV/frontrunning avec une optimisation continue basée sur l'intelligence artificielle.

## ✨ Caractéristiques principales

- **🚀 Ultra-rapide** - Exécution optimisée des transactions pour battre les autres bots
- **🛡️ Sécurisé** - Protection contre les rug pulls et les honeypots
- **🤖 Automatisé** - Fonctionne en mode automatique ou semi-automatique
- **📊 Intelligent** - S'améliore automatiquement grâce à l'analyse des données et au ML
- **💸 Rentable** - Maximise les profits via sniping, arbitrage et frontrunning
- **🔍 Discret** - Mécanismes pour éviter la détection par les DEX

## 🌟 Modules principaux

1. **Arbitrage entre DEX**
   - Exploitation des écarts de prix entre différents DEX/CEX
   - Exécution instantanée des transactions pour profiter des opportunités
   - Intégration d'un mode "Flash Arbitrage" pour ne jamais immobiliser de fonds

2. **Sniping de Tokens**
   - Surveillance en temps réel des nouvelles paires créées
   - Détection des whale movements pour identifier les tokens à potentiel
   - Stop-loss intelligent et prise de profit automatique
   - Analyse de la liquidité et du market cap pour éviter les scams

3. **Mode Automatique**
   - Analyse en temps réel des opportunités sur plusieurs blockchains
   - Ajustement dynamique des stratégies en fonction des résultats passés
   - Gestion efficace des fonds basée sur le risque/récompense

## 🛠️ Installation

### Prérequis

- Python 3.11 ou supérieur
- Node.js et npm (pour l'adaptateur Solana Web3.js)
- Git

### Installation automatique

Sous Linux/macOS:
```bash
git clone https://github.com/username/GBPBot.git
cd GBPBot
chmod +x install.sh
./install.sh
```

Sous Windows:
```bash
git clone https://github.com/username/GBPBot.git
cd GBPBot
install.bat
```

### Installation manuelle

1. Cloner le dépôt:
```bash
git clone https://github.com/username/GBPBot.git
cd GBPBot
```

2. Créer et activer un environnement virtuel:
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installer les dépendances:
```bash
pip install -r requirements.txt
```

4. Configurer les clés API et les wallets:
```bash
cp .env.example .env
# Modifier le fichier .env avec vos clés
```

## ⚙️ Configuration

GBPBot est hautement configurable via le fichier `.env`. Voici les principaux paramètres:

```env
# Configuration blockchain
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=votre_clé_privée_ici
AVAX_RPC_URL=https://api.avax.network/ext/bc/C/rpc
AVAX_PRIVATE_KEY=votre_clé_privée_ici
SONIC_RPC_URL=https://rpc.sonic.fantom.network/
SONIC_PRIVATE_KEY=votre_clé_privée_ici

# Paramètres trading
MAX_SLIPPAGE=1.0
GAS_PRIORITY=medium
MAX_TRANSACTION_AMOUNT=0.1
ENABLE_SNIPING=true
ENABLE_ARBITRAGE=false
ENABLE_AUTO_MODE=false

# Sécurité
REQUIRE_CONTRACT_ANALYSIS=true
ENABLE_STOP_LOSS=true
DEFAULT_STOP_LOSS_PERCENTAGE=5
```

Consultez la [documentation complète](docs/configuration.md) pour tous les paramètres disponibles.

## 🚀 Utilisation

### Démarrer GBPBot

Sous Linux/macOS:
```bash
./start_gbpbot.sh
```

Sous Windows:
```bash
start_gbpbot.bat
```

### Menu principal

Une fois lancé, GBPBot affiche un menu interactif:

```
============================================================
                    GBPBot - Menu Principal
============================================================
Bienvenue dans GBPBot, votre assistant de trading sur Avalanche!

Veuillez choisir une option:
1. Démarrer le Bot
2. Configurer les paramètres
3. Afficher la configuration actuelle
4. Statistiques et Logs
5. Afficher les Modules Disponibles
6. Quitter
```

### Sélection du module

Après avoir sélectionné "Démarrer le Bot", vous pouvez choisir le module à exécuter:

```
============================================================
                GBPBot - Sélection de Module
============================================================
1. Arbitrage entre les DEX
2. Sniping de Token
3. Lancer automatiquement le bot
4. Retour au menu principal
```

## 📈 Stratégies optimales

### Sniping de Tokens

- Prioriser Solana pour le sniping en raison des faibles frais et de la rapidité
- Cibler les tokens avec un ratio de liquidité/MarketCap > 5%
- Rechercher un volume potentiel de $500K+ en moins d'1h
- Éviter les tokens où le wallet du développeur détient >30% du supply

### Arbitrage

- Diviser les ordres en plusieurs petites transactions pour minimiser le slippage
- Utiliser l'optimisation du gaz pour dépasser les autres traders
- Exécuter des stratégies de "Flash Arbitrage" pour ne pas immobiliser de capital

## 📊 Performance

GBPBot inclut un dashboard pour suivre les performances historiques et analyser les résultats. Accédez au dashboard via le menu principal ou directement via l'interface web:

```
http://localhost:8080
```

## 🧪 Tests

Pour exécuter les tests:

```bash
pytest -xvs tests/
```

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## ⚠️ Avertissement

Le trading de crypto-monnaies comporte des risques significatifs. N'investissez que ce que vous pouvez vous permettre de perdre. Les performances passées ne garantissent pas les résultats futurs.

## 🔄 Roadmap

- [x] Installation et configuration automatique
- [x] Module d'arbitrage entre DEX
- [x] Module de sniping de tokens
- [x] Mode automatique avec ML
- [ ] Interface web avancée
- [ ] Support multicompte
- [ ] Intégration de nouveaux DEX (Raydium v2, Uniswap v4)
- [ ] Prédiction de tendances avec LLM
- [ ] Intégration avec Telegram

## 🤝 Contribuer

Les contributions sont les bienvenues! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives.

## 📧 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur ce dépôt.