# GBPBot - Trading Bot pour MEME coins

<div align="center">
    <img src="docs/images/logo.png" alt="GBPBot Logo" width="200" height="200" />
    <h3>Trading ultra-rapide et intelligent pour Solana, AVAX et Sonic</h3>
</div>

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Version](https://img.shields.io/badge/version-0.7.0-green)
![Security](https://img.shields.io/badge/security-codeql-green)
![Quality](https://img.shields.io/badge/quality-sonarqube-orange)
![AI](https://img.shields.io/badge/AI-Claude%203.7-purple)
![Stealth](https://img.shields.io/badge/stealth-advanced-black)

GBPBot est un bot de trading avancé conçu pour maximiser les profits dans l'écosystème des MEME coins sur Solana, AVAX et Sonic. Il intègre des fonctionnalités d'arbitrage, de sniping et de MEV/frontrunning avec une optimisation continue basée sur l'intelligence artificielle avancée via Claude 3.7.

## ✨ Caractéristiques principales

- **🚀 Ultra-rapide** - Exécution optimisée des transactions pour battre les autres bots
- **🛡️ Sécurisé** - Protection contre les rug pulls et les honeypots
- **🤖 Automatisé** - Fonctionne en mode automatique ou semi-automatique
- **📊 Intelligent** - S'améliore automatiquement grâce à l'analyse des données et au ML
- **💸 Rentable** - Maximise les profits via sniping, arbitrage et frontrunning
- **🔍 Discret** - Système anti-détection avancé avec simulation comportementale
- **🧠 IA avancée** - Analyses de marché et stratégies optimisées par Claude 3.7
- **🔄 Interface unifiée** - Accès simplifié à tous les modules via une interface centralisée

## 🌟 Modules principaux

1. **Arbitrage entre DEX**
   - Exploitation des écarts de prix entre différents DEX/CEX
   - Exécution instantanée des transactions pour profiter des opportunités
   - Intégration d'un mode "Flash Arbitrage" pour ne jamais immobiliser de fonds
   - Optimisation des trades par IA avec Claude 3.7
   - ✅ Module 100% finalisé et optimisé

2. **Sniping de Tokens**
   - Surveillance en temps réel des nouvelles paires créées
   - Détection des whale movements pour identifier les tokens à potentiel
   - Stop-loss intelligent et prise de profit automatique
   - Analyse de la liquidité et du market cap pour éviter les scams
   - Évaluation de risque avancée via Claude 3.7
   - ✅ Module 100% finalisé et optimisé

3. **MEV/Frontrunning pour AVAX**
   - Surveillance du mempool pour détecter les opportunités de frontrunning
   - Stratégies de frontrunning, backrunning et sandwich attacks
   - Optimisation des transactions pour maximiser les profits
   - Intégration avec Flashbots pour les bundles de transactions
   - Simulation des transactions avant exécution
   - ⏳ Module à 80% - Tests en environnement réel en cours

4. **Mode Automatique**
   - Analyse en temps réel des opportunités sur plusieurs blockchains
   - Ajustement dynamique des stratégies en fonction des résultats passés
   - Gestion efficace des fonds basée sur le risque/récompense
   - Stratégies de trading personnalisées générées par Claude 3.7
   - ✅ Module 100% finalisé et optimisé

5. **Interface Unifiée (NOUVEAU)**
   - Point d'entrée unique pour tous les modules du bot
   - Architecture asynchrone compatible avec le reste du code
   - Mapping des modules et des modes d'exécution pour un accès simplifié
   - Gestion améliorée des configurations
   - ⏳ Module à 85% - Finalisation de l'intégration avec tous les modules en cours

6. **Système Anti-Détection** 
   - Simulation comportementale multi-niveau (débutant, intermédiaire, expert)
   - Rotation intelligente des wallets avec gestion de réputation
   - Randomisation des montants et timings de transactions
   - Prévention des patterns récurrents détectables
   - Simulation de sessions de trading avec timing réaliste
   - ✅ Intégré dans tous les modules

## 🧠 Intelligence artificielle intégrée 

GBPBot intègre Claude 3.7, l'un des modèles d'IA les plus avancés, pour améliorer ses capacités analytiques:

- **Analyse de marché en temps réel** - Vue d'ensemble du marché crypto avec tendances et opportunités
- **Évaluation avancée des tokens** - Notation de risque, détection des red flags et identification des gems
- **Stratégies de trading optimisées** - Points d'entrée/sortie et paramètres personnalisés
- **Recherche web intégrée** - Enrichissement des analyses avec des données du web en temps réel

## 🤖 Agent IA multi-modules

Le nouveau système d'Agent IA vous permet de:

- **Activer les capacités d'IA** dans les modules d'arbitrage et de sniping existants
- **Choisir le niveau d'autonomie** adapté à votre confort:
  - **Semi-autonome**: Validation humaine pour chaque action critique
  - **Autonome**: L'IA prend toutes les décisions sans validation
  - **Hybride**: Validation uniquement pour les opérations à risque élevé
- **Utiliser le mode entièrement automatique** pour surveiller le marché et exécuter des stratégies intelligentes:
  - Analyse continue des opportunités de trading
  - Prise de décision basée sur le contexte de marché
  - Exécution optimisée des transactions

L'Agent IA utilise LangChain pour orchestrer l'intelligence de Claude 3.7, améliorant considérablement la détection d'opportunités et la prise de décision.

[En savoir plus sur l'Agent IA](docs/AGENT_IA.md) | [En savoir plus sur l'intégration Claude 3.7](CLAUDE_INTEGRATION.md)

## 🛠️ Installation

### Prérequis

- Python 3.11 ou supérieur
- Node.js et npm (pour l'adaptateur Solana Web3.js)
- Git
- Clé API Claude 3.7 (pour les fonctionnalités d'IA avancées)

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

# Configuration Claude 3.7
AI_PROVIDER=claude
CLAUDE_API_KEY=votre_clé_api_ici
CLAUDE_MODEL=claude-3-7-sonnet-20240229

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

GBPBot peut être utilisé via son interface CLI conviviale ou sa nouvelle interface unifiée:

```bash
# Démarrer le bot via l'interface CLI traditionnelle
python gbpbot_cli_bridge.py

# Démarrer le bot via la nouvelle interface unifiée
python -m gbpbot.interface.unified_interface
```

### Interface CLI

L'interface CLI offre un menu interactif:

```
==========================================================
                GBPBot - Menu Principal
==========================================================
1. Démarrer le Bot
2. Configurer les paramètres
3. Afficher la configuration actuelle
4. Statistiques et Logs
5. Afficher les Modules Disponibles
6. Quitter
```

### Interface Unifiée (NOUVEAU)

La nouvelle interface unifiée permet d'accéder directement à tous les modules:

```python
# Exemple d'utilisation programmatique
import asyncio
from gbpbot.interface.unified_interface import UnifiedInterface

async def main():
    ui = UnifiedInterface()
    await ui.initialize()
    
    # Lancer un module spécifique
    await ui.launch_module("Arbitrage", mode="live")
    
    # Configurer les paramètres
    await ui.configure()
    
    # Afficher les statistiques
    await ui.display_statistics()

if __name__ == "__main__":
    asyncio.run(main())
```

### Modes d'exécution

Pour chaque module, vous pouvez choisir entre:

1. **Mode Test** - Simulation sans transactions réelles
2. **Mode Simulation** - Exécution en environnement réel mais sans transactions financières
3. **Mode Live** - Exécution complète avec transactions réelles

### Modules disponibles

Sélectionnez un module après avoir démarré le bot:

```
==========================================================
               GBPBot - Sélection de Module
==========================================================
1. Arbitrage entre les DEX
2. Sniping de Token
3. Mode Automatique
4. MEV/Frontrunning
5. AI Assistant
6. Backtesting
7. Retour au menu principal
```

Pour plus de détails sur l'utilisation, consultez [le guide utilisateur complet](docs/USER_GUIDE.md).

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

## 🔒 Sécurité et Qualité du Code

GBPBot intègre des pratiques d'analyse de code automatisée pour garantir une qualité et une sécurité optimales. Nous avons mis en place plusieurs outils pour analyser en continu la qualité et la sécurité du code.

### Analyse Automatisée du Code

Nous utilisons les outils suivants pour maintenir la qualité et la sécurité du code :

1. **CodeQL** - Analyse sémantique puissante pour détecter les vulnérabilités et les bugs
2. **SonarQube** - Analyse approfondie de la qualité et de la sécurité du code
3. **Dependabot** - Surveillance automatique des dépendances pour détecter les vulnérabilités
4. **Bandit** - Détection des vulnérabilités spécifiques à Python
5. **Safety** - Vérification des dépendances Python pour les vulnérabilités connues

### Analyse Locale

Pour les développeurs souhaitant exécuter des analyses localement avant de soumettre leur code, nous fournissons des scripts d'analyse locale :

- **Windows** : `analyse_locale.ps1`
- **Linux/macOS** : `analyse_locale.sh`

Ces scripts exécutent les mêmes analyses que notre pipeline CI/CD et génèrent des rapports détaillés dans le dossier `reports/`.

### Badges de Qualité

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=GBPBot&metric=alert_status)](https://sonarcloud.io/dashboard?id=GBPBot)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=GBPBot&metric=security_rating)](https://sonarcloud.io/dashboard?id=GBPBot)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=GBPBot&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=GBPBot)

### Intégration CI/CD

Notre pipeline d'intégration continue vérifie automatiquement la qualité et la sécurité du code à chaque commit ou pull request :

- **Analyse statique** - Détection des bugs et des vulnérabilités
- **Tests automatisés** - Vérification de la fonctionnalité correcte
- **Couverture de code** - Suivi de la couverture des tests
- **Vérification des dépendances** - Détection des versions obsolètes ou vulnérables

### Exécuter l'Analyse Localement

Les développeurs peuvent exécuter les mêmes analyses localement avant de soumettre leur code :

Sous Linux/macOS :
```bash
chmod +x analyse_locale.sh
./analyse_locale.sh
```

Sous Windows :
```bash
.\analyse_locale.ps1
```

Ces scripts exécutent une suite d'analyses comprenant Bandit, Pylint, Safety, et Ruff, générant des rapports détaillés que vous pouvez consulter.

### Résultats de l'Analyse

Les résultats des analyses sont disponibles :
- Dans les rapports générés localement
- Dans l'onglet "Security" du dépôt GitHub
- Dans le dashboard Codiga connecté au projet
- Dans le dashboard SonarQube connecté au projet

### Bonnes Pratiques de Sécurité

GBPBot implémente les meilleures pratiques de sécurité pour le trading de cryptomonnaies :
- Détection des secrets et des clés privées dans le code
- Vérification des contrats avant interaction
- Protection contre les rug pulls et les honeypots
- Validation des transactions avant exécution
- Gestion sécurisée des clés privées

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## ⚠️ Avertissement

Le trading de crypto-monnaies comporte des risques significatifs. N'investissez que ce que vous pouvez vous permettre de perdre. Les performances passées ne garantissent pas les résultats futurs.

## 🔄 Roadmap

- [x] Installation et configuration automatique
- [x] Module d'arbitrage entre DEX
- [x] Module de sniping de tokens
- [x] Mode automatique avec ML
- [x] Méthodes de lancement unifiées
- [x] Intégration d'outils d'analyse de code et de sécurité
- [ ] Interface web avancée
- [ ] Support multicompte
- [ ] Intégration de nouveaux DEX (Raydium v2, Uniswap v4)
- [ ] Prédiction de tendances avec LLM
- [ ] Intégration avec Telegram

## 🤝 Contribuer

Les contributions sont les bienvenues! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives.

## 📧 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur ce dépôt.

## Système Anti-Détection

Le GBPBot intègre un système anti-détection avancé qui lui permet de rester indétectable par les DEX et autres acteurs de la blockchain. Ce système combine plusieurs couches de protection:

- **Rotation d'IP automatique** pour éviter les bannissements
- **Randomisation des délais** entre les transactions
- **Simulation comportementale humaine** pour éviter les patterns détectables
- **Transactions fantômes** pour brouiller les pistes
- **Protection contre le blacklisting** des wallets 
- **Gestion intelligente des profils de trading** par IA pour équilibrer parfaitement discrétion et performance

### Gestion Automatique des Profils par IA

Le GBPBot dispose désormais d'un système d'intelligence avancé qui permet aux différentes IA intégrées (Claude, OpenAI, LLaMA) de gérer automatiquement les profils de trading utilisés par le système anti-détection:

- **Analyse contextuelle** de chaque opération (blockchain, type d'opération, token)
- **Sélection optimale** du profil le plus adapté pour maximiser les profits tout en évitant la détection
- **Adaptation dynamique** au niveau de risque de chaque blockchain
- **Équilibre automatique** entre performance et discrétion selon vos priorités
- **Traçabilité des décisions** pour comprendre le raisonnement de l'IA

Cette fonctionnalité permet au GBPBot de s'adapter automatiquement aux conditions du marché et aux niveaux de risque, sans nécessiter d'intervention manuelle. La gestion des profils peut être configurée pour privilégier la performance (profits maximaux) ou la discrétion (sécurité maximale) selon vos préférences et les objectifs de trading.

## Configuration

Le GBPBot peut être configuré via le fichier `.env.local` à la racine du projet. Voici les principales options:

```env
# Configuration générale
GBPBOT_LOG_LEVEL=INFO       # Niveau de log (DEBUG, INFO, WARNING, ERROR)

# Configuration blockchain
DEFAULT_BLOCKCHAIN=solana    # Blockchain par défaut (solana, avax, sonic)

# Configuration anti-détection
ANTI_DETECTION_ENABLED=true  # Activer/désactiver le système anti-détection
AI_PROFILE_MANAGEMENT=true   # Gestion automatique des profils par IA
PERFORMANCE_PRIORITY=0.7     # Équilibre performance/discrétion (0.0-1.0)

# Clés API pour les IA (au moins une est nécessaire)
AI_PROVIDER=auto             # Provider à utiliser: auto, claude, openai, llama
CLAUDE_API_KEY=your_api_key  # Clé API pour Claude d'Anthropic
CLAUDE_MODEL=claude-3-haiku-20240307  # Modèle Claude à utiliser
OPENAI_API_KEY=your_api_key  # Clé API pour GPT d'OpenAI
OPENAI_MODEL=gpt-4           # Modèle OpenAI à utiliser
LLAMA_MODEL_PATH=/path/to/model.gguf  # Chemin vers le modèle LLaMA
```

## Intégration d'un Agent IA Avancé dans GBPBot

Après analyse approfondie du code existant, je constate que votre GBPBot dispose déjà de certaines bases pour l'intégration d'agents IA, notamment via:

1. Le système `profile_intelligence.py` qui permet une gestion intelligente des profils de trading par IA
2. L'intégration multi-modèles (Claude, OpenAI, LLaMA) avec la classe `LLMProvider`
3. Le `StealthManager` qui applique intelligemment des stratégies de trading

Cependant, votre proposition va plus loin en structurant un véritable **agent autonome** avec orchestration d'outils et prise de décision complexe. Voici une comparaison et mon analyse:

## Existant vs Proposition d'Agent IA

| Fonctionnalité | État Actuel dans GBPBot | Proposition d'Agent IA |
|----------------|--------------------------|------------------------|
| Modèles IA | ✅ Intégration multi-modèles (Claude, OpenAI, LLaMA) | ✅ Similaire avec utilisation de LangChain |
| Orchestration | ❌ Pas d'orchestrateur central | ✅ LangChain pour orchestrer les outils |
| Niveaux d'autonomie | ⚠️ Paramétrable mais non structuré en "agents" | ✅ Structure claire (semi-autonome, autonome, hybride) |
| Outils accessibles | ⚠️ Limités aux modules internes | ✅ Extension à des APIs externes et web search |
| Décisions adaptatives | ⚠️ Basées sur profils prédéfinis | ✅ Apprentissage continu et ajustement dynamique |

## Proposition d'Implémentation d'Agent IA pour GBPBot

Pour implémenter cette architecture d'agent IA dans votre GBPBot, je vous recommande les étapes suivantes:

### 1. Création du module `gbpbot/ai/agent_manager.py`

```python
"""
Module AgentManager - Système d'orchestration d'agents IA pour GBPBot

Ce module implémente un agent IA avancé capable d'orchestrer l'ensemble des modules
du GBPBot pour une prise de décision autonome ou semi-autonome basée sur LangChain.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum

# Importations LangChain
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.llms.base import BaseLLM
from langchain.chains.conversation.memory import ConversationBufferMemory

# Importations internes
from gbpbot.utils.logger import setup_logger
from gbpbot.config.settings import get_settings
from gbpbot.ai.llm_provider import get_ai_client, LLMProvider, AiClientResponse
from gbpbot.ai.profile_intelligence import ProfileIntelligence
from gbpbot.security.stealth_manager import StealthManager
from gbpbot.modules.token_sniper import TokenSniper
from gbpbot.modules.arbitrage_engine import ArbitrageEngine
from gbpbot.modules.market_analyzer import MarketAnalyzer

# Configuration du logger
logger = setup_logger("agent_manager", logging.INFO)

class AgentAutonomyLevel(Enum):
    """Niveau d'autonomie de l'agent IA."""
    SEMI_AUTONOME = "semi_autonomous"  # Requiert validation humaine pour actions critiques
    AUTONOME = "autonomous"            # Totalement autonome
    HYBRIDE = "hybrid"                 # Adaptatif selon contexte et risque

class AgentManager:
    """
    Gestionnaire d'agents IA pour GBPBot.
    
    Implémente un système avancé d'agents IA basés sur LangChain pour
    orchestrer les différents modules du GBPBot et prendre des décisions
    intelligentes de manière autonome ou semi-autonome.
    """
    
    def __init__(
        self,
        autonomy_level: AgentAutonomyLevel = AgentAutonomyLevel.HYBRIDE,
        llm_provider: Optional[LLMProvider] = None,
        max_decision_amount: float = 0.1,  # Montant max pour décisions sans validation
        require_approval_callback: Optional[Callable[[str, Dict[str, Any]], asyncio.Future]] = None
    ):
        """
        Initialise le gestionnaire d'agents IA.
        
        Args:
            autonomy_level: Niveau d'autonomie de l'agent
            llm_provider: Fournisseur de modèle LLM (Claude, OpenAI, LLaMA)
            max_decision_amount: Montant maximum pour décisions autonomes
            require_approval_callback: Fonction de callback pour validation humaine
        """
        self.autonomy_level = autonomy_level
        self.llm_provider = llm_provider
        self.max_decision_amount = max_decision_amount
        self.require_approval_callback = require_approval_callback
        
        # État interne
        self.initialized = False
        self.tools = []
        self.agent = None
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # Composants du bot
        self.token_sniper = None
        self.arbitrage_engine = None
        self.market_analyzer = None
        self.stealth_manager = None
        self.profile_intelligence = None
        
        # Statistiques et métriques
        self.total_decisions = 0
        self.approved_decisions = 0
        self.rejected_decisions = 0
        self.autonomous_decisions = 0
        self.decision_history = []
        
        # Initialisation asynchrone
        asyncio.create_task(self._async_init())
    
    async def _async_init(self) -> None:
        """Initialisation asynchrone des composants."""
        try:
            # Initialiser le provider LLM si non fourni
            if not self.llm_provider:
                self.llm_provider = await get_ai_client()
                if not self.llm_provider:
                    logger.error("Impossible d'initialiser un provider LLM")
                    return
            
            # Initialiser les composants du bot
            # (Ces instanciations dépendraient de l'implémentation réelle de vos modules)
            self.token_sniper = TokenSniper()
            self.arbitrage_engine = ArbitrageEngine()
            self.market_analyzer = MarketAnalyzer()
            self.stealth_manager = StealthManager()
            self.profile_intelligence = ProfileIntelligence()
            
            # Définir les outils disponibles pour l'agent
            self._define_tools()
            
            # Initialiser l'agent LangChain
            self._initialize_langchain_agent()
            
            self.initialized = True
            logger.info(f"Agent IA initialisé avec niveau d'autonomie: {self.autonomy_level.value}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'agent IA: {str(e)}")
    
    def _define_tools(self) -> None:
        """Définit les outils disponibles pour l'agent."""
        self.tools = [
            Tool(
                name="MarketAnalyzer",
                func=self._analyze_market,
                description="Analyse les données du marché crypto et recommande des opportunités."
            ),
            Tool(
                name="TokenSniper",
                func=self._snipe_token,
                description="Effectue un sniping rapide d'un token spécifique."
            ),
            Tool(
                name="ArbitrageEngine",
                func=self._execute_arbitrage,
                description="Exécute des opérations d'arbitrage entre DEX."
            ),
            Tool(
                name="ProfileManager",
                func=self._select_trading_profile,
                description="Sélectionne le profil de trading optimal pour une opération spécifique."
            ),
            Tool(
                name="TransactionExecutor",
                func=self._execute_transaction,
                description="Exécute une transaction blockchain avec les paramètres spécifiés."
            ),
            Tool(
                name="WebSearch",
                func=self._search_web,
                description="Recherche des informations sur le web pour enrichir l'analyse."
            )
        ]
    
    def _initialize_langchain_agent(self) -> None:
        """Initialise l'agent LangChain avec les outils définis."""
        # Adapter le LLMProvider au format attendu par LangChain
        # (Ceci est une simplification, l'implémentation réelle nécessiterait une adaptation plus poussée)
        langchain_llm = self._adapt_llm_provider_to_langchain()
        
        if not langchain_llm:
            logger.error("Impossible d'adapter le LLMProvider pour LangChain")
            return
        
        # Initialiser l'agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=langchain_llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory
        )
    
    def _adapt_llm_provider_to_langchain(self) -> Optional[BaseLLM]:
        """
        Adapte le LLMProvider au format attendu par LangChain.
        
        Note: Cette méthode est une approximation simplifiée. L'implémentation réelle
        nécessiterait une adaptation plus poussée du LLMProvider à l'interface BaseLLM de LangChain.
        
        Returns:
            Instance de BaseLLM compatible avec LangChain ou None si échec
        """
        # Implémentation à développer - ceci est un placeholder
        return None
    
    async def run_agent(self, query: str) -> Dict[str, Any]:
        """
        Exécute l'agent IA avec une requête spécifique.
        
        Args:
            query: Requête ou instruction pour l'agent
            
        Returns:
            Résultat de l'exécution de l'agent
        """
        if not self.initialized or not self.agent:
            await self._async_init()
            if not self.initialized:
                return {"error": "Agent IA non initialisé"}
        
        try:
            # Exécuter l'agent
            result = await asyncio.to_thread(self.agent.run, query)
            
            # Mettre à jour les statistiques
            self.total_decisions += 1
            
            return {
                "success": True,
                "result": result,
                "query": query
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'agent: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    # Implémentations des fonctions d'outil (simplifiées pour l'exemple)
    
    async def _analyze_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse le marché et retourne des opportunités."""
        # Implémentation réelle utiliserait self.market_analyzer
        return {"status": "not_implemented"}
    
    async def _snipe_token(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une opération de sniping de token."""
        # Vérifier si l'approbation est nécessaire
        if self._requires_approval(params):
            approved = await self._request_approval("Sniping de token", params)
            if not approved:
                return {"status": "rejected", "reason": "L'utilisateur a rejeté l'opération"}
        
        # Implémentation réelle utiliserait self.token_sniper
        return {"status": "not_implemented"}
    
    async def _execute_arbitrage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une opération d'arbitrage."""
        # Implémentation similaire avec vérification d'approbation
        return {"status": "not_implemented"}
    
    async def _select_trading_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sélectionne le profil de trading optimal."""
        # Utiliserait self.profile_intelligence
        return {"status": "not_implemented"}
    
    async def _execute_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une transaction blockchain."""
        # Implémentation avec vérification d'approbation
        return {"status": "not_implemented"}
    
    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Recherche des informations sur le web."""
        # Implémentation d'un web scraper ou utilisation d'API
        return {"status": "not_implemented"}
    
    def _requires_approval(self, params: Dict[str, Any]) -> bool:
        """
        Détermine si une opération nécessite une approbation humaine.
        
        Args:
            params: Paramètres de l'opération
            
        Returns:
            True si l'approbation est nécessaire, False sinon
        """
        # Semi-autonome - toujours demander approbation
        if self.autonomy_level == AgentAutonomyLevel.SEMI_AUTONOME:
            return True
        
        # Autonome - jamais demander approbation
        if self.autonomy_level == AgentAutonomyLevel.AUTONOME:
            return False
        
        # Hybride - décider en fonction des paramètres
        # Par exemple, vérifier si le montant dépasse le seuil
        amount = params.get("amount", 0.0)
        if amount > self.max_decision_amount:
            return True
        
        # Vérifier si l'opération est à haut risque
        risk_level = params.get("risk_level", "low")
        if risk_level.lower() in ["high", "très élevé", "extreme"]:
            return True
        
        return False
    
    async def _request_approval(self, operation: str, params: Dict[str, Any]) -> bool:
        """
        Demande l'approbation utilisateur pour une opération.
        
        Args:
            operation: Description de l'opération
            params: Paramètres de l'opération
            
        Returns:
            True si approuvé, False sinon
        """
        if not self.require_approval_callback:
            logger.warning("Callback d'approbation non configuré, refus automatique")
            return False
        
        try:
            # Créer un future pour attendre la réponse
            approval_future = self.require_approval_callback(operation, params)
            
            # Attendre la réponse avec timeout
            approved = await asyncio.wait_for(approval_future, timeout=300)  # 5 minutes max
            
            # Mettre à jour les statistiques
            if approved:
                self.approved_decisions += 1
            else:
                self.rejected_decisions += 1
            
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Timeout de l'approbation pour {operation}, refus automatique")
            self.rejected_decisions += 1
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la demande d'approbation: {str(e)}")
            self.rejected_decisions += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de l'agent.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            "total_decisions": self.total_decisions,
            "approved_decisions": self.approved_decisions,
            "rejected_decisions": self.rejected_decisions,
            "autonomous_decisions": self.autonomous_decisions,
            "approval_rate": self.approved_decisions / max(1, self.total_decisions),
            "autonomy_level": self.autonomy_level.value,
            "initialized": self.initialized
        }

def create_agent_manager(
    autonomy_level: str = "hybrid",
    max_decision_amount: float = 0.1,
    require_approval_callback: Optional[Callable] = None
) -> AgentManager:
    """
    Crée et retourne une instance d'AgentManager.
    
    Args:
        autonomy_level: Niveau d'autonomie ("semi_autonomous", "autonomous", "hybrid")
        max_decision_amount: Montant maximum pour décisions autonomes
        require_approval_callback: Fonction de callback pour validation humaine
        
    Returns:
        Instance d'AgentManager
    """
    # Convertir la chaîne en enum
    autonomy_enum = AgentAutonomyLevel.HYBRIDE
    if autonomy_level == "semi_autonomous":
        autonomy_enum = AgentAutonomyLevel.SEMI_AUTONOME
    elif autonomy_level == "autonomous":
        autonomy_enum = AgentAutonomyLevel.AUTONOME
    
    return AgentManager(
        autonomy_level=autonomy_enum,
        max_decision_amount=max_decision_amount,
        require_approval_callback=require_approval_callback
    )
```

### 2. Intégration dans le système existant (`gbpbot/main.py` ou équivalent)

```python
# Ajouter à votre fichier principal

from gbpbot.ai.agent_manager import create_agent_manager

# Callback pour demander l'approbation utilisateur
async def request_user_approval(operation: str, params: Dict[str, Any]) -> bool:
    # En mode CLI
    print(f"\n[APPROBATION REQUISE] {operation}")
    print("Paramètres:", json.dumps(params, indent=2))
    response = input("Approuver (o/n)? ").lower()
    return response in ["o", "oui", "y", "yes"]

# Création de l'agent avec callback d'approbation
agent_manager = create_agent_manager(
    autonomy_level="hybrid",  # "semi_autonomous", "autonomous" ou "hybrid"
    max_decision_amount=0.1,  # 0.1 ETH/SOL/etc. maximum sans approbation
    require_approval_callback=request_user_approval
)

# Exemple d'utilisation dans un menu
async def menu_agent_ia():
    print("\n=== Menu Agent IA ===")
    print("1. Analyse du marché et recommandation")
    print("2. Recherche d'opportunités d'arbitrage")
    print("3. Détection et sniping de nouveaux tokens")
    print("4. Mode autonome (24h)")
    print("5. Retour")
    
    choice = input("Votre choix: ")
    
    if choice == "1":
        result = await agent_manager.run_agent("Analyse le marché crypto actuel et recommande les 3 meilleures opportunités de trading.")
        print(result.get("result", "Erreur lors de l'analyse"))
    elif choice == "2":
        result = await agent_manager.run_agent("Trouve les meilleures opportunités d'arbitrage entre DEX sur Solana avec au moins 2% de profit potentiel.")
        print(result.get("result", "Erreur lors de la recherche d'arbitrage"))
    elif choice == "3":
        result = await agent_manager.run_agent("Détecte et analyse les nouveaux tokens sur Solana ayant une liquidité d'au moins 10K$, et prépare une stratégie de sniping optimale.")
        print(result.get("result", "Erreur lors de la détection"))
    elif choice == "4":
        # Lancer l'agent en mode autonome (exemple simplifié)
        print("Mode autonome activé pour 24h. Utiliser Ctrl+C pour arrêter.")
        try:
            while True:
                await agent_manager.run_agent("Surveille le marché et exécute automatiquement les meilleures opportunités de profit.")
                await asyncio.sleep(300)  # 5 minutes entre chaque cycle
        except KeyboardInterrupt:
            print("Mode autonome arrêté par l'utilisateur")
```

### 3. Installation des dépendances

Créez un fichier `requirements-agent.txt` avec:

```
langchain>=0.0.300
openai>=0.27.0
anthropic>=0.5.0
llama-cpp-python>=0.1.50  # Si utilisation locale de LLaMA
duckduckgo-search>=1.0.0  # Pour recherche web
```

Puis exécutez:

```bash
pip install -r requirements-agent.txt
```

## Avantages par rapport à l'implémentation actuelle

1. **Architecture d'agent formalisée** - Système complet d'agents au lieu de simples intégrations IA ponctuelles
2. **Orchestration LangChain** - Utilisation d'un framework optimisé pour les agents IA
3. **Niveaux d'autonomie structurés** - Système clairement défini allant de semi-autonome à autonome adaptatif
4. **Intégration d'outils externes** - Possibilité d'exploiter des APIs et informations web
5. **Mécanisme d'approbation** - Système de validation pour les décisions critiques
6. **Suivi statistique avancé** - Analyse des performances de l'agent

## Prochaines étapes recommandées

1. **Implémentation de l'AgentManager** - Créer les fichiers et modules nécessaires
2. **Adaptation LLMProvider pour LangChain** - Créer une couche d'adaptation entre votre système et LangChain
3. **Développement des outils spécifiques** - Implémenter les fonctions d'outils qui utilisent vos modules existants
4. **Tests en environnement contrôlé** - Démarrer avec des montants faibles et validation humaine requise
5. **Documentation utilisateur** - Guide explicatif sur le fonctionnement et la configuration de l'agent

Souhaitez-vous que j'approfondisse un aspect spécifique de cette proposition d'implémentation?

## 🧪 Tests de Sécurité

GBPBot intègre plusieurs mécanismes pour garantir la sécurité du système :

- **Analyse statique du code** avec CodeQL et SonarCloud
- **Vérification des dépendances** pour les vulnérabilités connues
- **Tests de pénétration automatisés** pour détecter les faiblesses potentielles
- **Protection contre les attaques** (injections, XSS, etc.)
- **Audit régulier** du code et des processus

## 📚 Documentation

GBPBot dispose d'une documentation complète pour vous aider :

- [Guide d'Utilisation](gbpbot/USER_GUIDE.md) - Guide complet pour l'utilisation du bot
- [Documentation Technique](gbpbot/TECHNICAL_DOCUMENTATION.md) - Architecture et détails techniques
- [Guide des Tests de Pénétration](docs/PENTESTS_GUIDE.md) - Comment tester la sécurité du bot
- [Guide d'API](docs/API_REFERENCE.md) - Documentation de l'API (si applicable)

Pour plus de documentation, consultez le répertoire [docs/](docs/).