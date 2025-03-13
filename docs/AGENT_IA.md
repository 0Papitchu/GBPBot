# Agent IA Avancé pour GBPBot

## Introduction

L'Agent IA est une fonctionnalité avancée du GBPBot qui permet d'orchestrer intelligemment les différents modules du bot pour prendre des décisions de trading automatisées. Basé sur LangChain et intégrant divers modèles d'IA (Claude, OpenAI, LLaMA), l'Agent IA peut analyser le marché, détecter des opportunités, gérer des profils de trading et exécuter des transactions de manière autonome ou semi-autonome.

## 🌟 Caractéristiques Principales

- **🤖 Intelligence Adaptative** - Prise de décision basée sur le contexte et l'analyse en temps réel
- **🔄 Orchestration de Modules** - Coordination intelligente entre les différents composants du GBPBot
- **🚦 Niveaux d'Autonomie Configurables** - Mode semi-autonome, autonome ou hybride selon vos préférences
- **🔍 Recherche Web Intégrée** - Enrichissement des analyses avec des données externes
- **🛡️ Validation Humaine** - Possibilité de valider les décisions critiques
- **📊 Statistiques et Suivi** - Métriques détaillées sur les décisions et actions de l'agent
- **⚡ Haute Performance** - Conception asynchrone pour ne pas ralentir les opérations de trading

## Installation

### Prérequis

- Python 3.11+
- GBPBot correctement installé
- Bibliothèques LangChain et dépendances

### Installation des Dépendances

```bash
# Windows
pip install -r requirements-agent.txt

# Linux/macOS
pip install -r requirements-agent.txt
```

## Utilisation

### Lancement via Scripts

La méthode la plus simple pour utiliser l'Agent IA est via les scripts inclus :

- **Windows**: Double-cliquez sur `run_agent.bat`
- **Linux/macOS**: Exécutez `./run_agent.sh` (rendez-le exécutable avec `chmod +x run_agent.sh` si nécessaire)

### Lancement Manuel

Vous pouvez également lancer l'Agent IA manuellement :

```bash
# Activer l'environnement virtuel
source env/bin/activate  # Linux/macOS
# ou
env\Scripts\activate     # Windows

# Lancer l'Agent IA
python -m gbpbot.agent_example
```

### Menu Interactif

Une fois lancé, l'Agent IA présente un menu interactif :

```
=== Menu Agent IA ===
1. Analyse du marché et recommandation
2. Recherche d'opportunités d'arbitrage
3. Détection et sniping de nouveaux tokens
4. Mode autonome (démo 5min)
5. Retour
```

Chaque option déclenche une tâche spécifique :

1. **Analyse du marché et recommandation** - L'agent analyse le marché et recommande des opportunités de trading
2. **Recherche d'opportunités d'arbitrage** - L'agent cherche des écarts de prix exploitables entre différents DEX
3. **Détection et sniping de nouveaux tokens** - L'agent recherche et analyse les nouveaux tokens prometteurs
4. **Mode autonome** - L'agent fonctionne de manière continue, surveillant le marché et exécutant des transactions selon les opportunités
5. **Retour** - Quitte le menu de l'Agent IA

## Niveaux d'Autonomie

L'Agent IA propose trois niveaux d'autonomie configurables :

### 1. Semi-Autonome (`semi_autonomous`)

- L'agent demande systématiquement une validation humaine avant chaque action significative
- Idéal pour les utilisateurs qui souhaitent garder un contrôle total
- Recommandé pour les débutants ou les tests initiaux

### 2. Autonome (`autonomous`)

- L'agent prend toutes les décisions et exécute les actions sans validation humaine
- Maximise l'automatisation et la réactivité
- À utiliser avec précaution et sur des montants limités

### 3. Hybride (`hybrid`) - Par défaut

- L'agent est autonome pour les décisions de faible risque ou de montant limité
- Demande une validation pour les opérations importantes ou risquées
- Équilibre optimal entre autonomie et contrôle

## Configuration

### Configuration Basique (Ligne de Commande)

```bash
python -m gbpbot.agent_example --autonomy hybrid
```

Options disponibles :
- `--autonomy semi_autonomous` - Mode semi-autonome (validation systématique)
- `--autonomy autonomous` - Mode totalement autonome (aucune validation)
- `--autonomy hybrid` - Mode hybride adaptatif (par défaut)

### Configuration Avancée

Pour une configuration plus fine, vous pouvez modifier directement les paramètres dans le fichier `gbpbot/ai/agent_manager.py` en ajustant la classe `AgentConfig` :

```python
@dataclass
class AgentConfig:
    """Configuration de l'agent IA."""
    autonomy_level: AgentAutonomyLevel = AgentAutonomyLevel.HYBRIDE
    max_decision_amount: float = 0.1  # Montant max pour décisions sans validation
    enable_websearch: bool = True
    enable_human_feedback: bool = True
    max_consecutive_actions: int = 5
    ai_temperature: float = 0.2
    ai_max_tokens: int = 4000
    cache_timeout_minutes: int = 10
    approval_timeout_seconds: int = 300
    language: str = "fr"  # 'fr' ou 'en'
```

## Intégration avec les Modules Existants

L'Agent IA s'intègre avec les modules existants de GBPBot :

1. **Module TokenSniper** - Pour la détection et le sniping de nouveaux tokens
2. **Module ArbitrageEngine** - Pour l'exécution d'opérations d'arbitrage entre DEX
3. **Module ProfileIntelligence** - Pour la sélection intelligente des profils de trading
4. **Module StealthManager** - Pour la gestion de la furtivité et l'anti-détection

L'Agent IA détecte automatiquement les modules disponibles et adapte ses capacités en conséquence.

## Architecture Technique

L'Agent IA est construit sur une architecture modulaire :

```
AgentManager
│
├── LangChain Adapter
│   ├── LLMProviderAdapter - Adaptation des modèles IA existants (Claude, OpenAI, LLaMA)
│   └── GBPBotTool - Adaptateur pour les outils GBPBot
│
├── Outils (Tools)
│   ├── MarketAnalyzer - Analyse du marché crypto
│   ├── TokenSniper - Sniping de nouveaux tokens
│   ├── ArbitrageEngine - Arbitrage entre DEX
│   ├── ProfileManager - Gestion des profils de trading
│   ├── TransactionExecutor - Exécution des transactions
│   └── WebSearch - Recherche d'informations externes
│
└── Système de Validation
    └── Mécanisme d'approbation configurable
```

## Exemples d'Utilisation Avancée

### 1. Intégration Programmatique

```python
from gbpbot.ai.agent_manager import create_agent_manager

# Callback personnalisé pour validation
async def my_approval_callback(operation, params):
    # Logique personnalisée
    return True  # ou False pour rejeter

# Créer l'agent
agent = create_agent_manager(
    autonomy_level="hybrid",
    max_decision_amount=0.2,  # 0.2 ETH/SOL maximum sans validation
    require_approval_callback=my_approval_callback
)

# Exécuter l'agent avec une instruction spécifique
result = await agent.run_agent("Analyse les opportunités d'arbitrage sur Solana")
print(result)
```

### 2. Automatisation Avancée

```python
import asyncio
from gbpbot.ai.agent_manager import create_agent_manager, AgentAutonomyLevel

async def trading_automation():
    # Créer l'agent en mode autonome
    agent = create_agent_manager(autonomy_level="autonomous")
    
    while True:
        # Exécuter une séquence d'analyses et actions
        await agent.run_agent("Analyse le marché et identifie les tendances actuelles")
        await agent.run_agent("Cherche les tokens avec forte activité d'achat par des whales")
        await agent.run_agent("Vérifie les opportunités d'arbitrage avec au moins 1.5% de profit")
        
        # Pause entre les cycles
        await asyncio.sleep(300)  # 5 minutes

# Lancer l'automatisation
asyncio.run(trading_automation())
```

## FAQ

**Q: L'Agent IA peut-il fonctionner sans connexion Internet ?**
R: Non, il nécessite une connexion Internet pour communiquer avec les API d'IA (Claude, OpenAI) et pour la recherche web. Cependant, si vous utilisez LLaMA en local, certaines fonctionnalités peuvent fonctionner hors ligne.

**Q: L'Agent IA ralentit-il les opérations de trading ?**
R: Non, l'Agent IA est conçu de manière asynchrone pour éviter de bloquer les opérations critiques. Les analyses approfondies sont effectuées en parallèle des opérations de trading.

**Q: Comment limiter les risques avec l'Agent IA ?**
R: Utilisez le mode semi-autonome ou hybride, définissez un `max_decision_amount` faible, et commencez avec des montants limités pour tester le comportement de l'agent.

**Q: Puis-je utiliser l'Agent IA avec d'autres blockchains que celles par défaut ?**
R: Oui, l'Agent IA peut travailler avec toutes les blockchains supportées par GBPBot. Il adapte ses analyses et recommandations en fonction de la blockchain cible.

**Q: Comment surveiller les performances de l'Agent IA ?**
R: Utilisez la méthode `get_stats()` de l'Agent pour obtenir des métriques détaillées sur ses décisions et actions.

## Dépannage

### Problèmes d'Initialisation

- **Erreur "LangChain non disponible"** - Assurez-vous d'avoir installé LangChain avec `pip install -r requirements-agent.txt`
- **Erreur "Provider LLM non initialisé"** - Vérifiez vos clés API dans le fichier `.env.local`

### Problèmes d'Exécution

- **Actions non exécutées** - Vérifiez les logs pour détecter les erreurs spécifiques
- **Timeout lors des approbations** - Augmentez le délai d'approbation dans `AgentConfig`

## Conclusion

L'Agent IA représente une avancée majeure dans l'automatisation intelligente du trading avec GBPBot. En combinant la puissance des modèles d'IA avancés et l'orchestration des modules spécialisés, il offre un niveau d'autonomie et d'efficacité inédit, tout en maintenant des mécanismes de contrôle essentiels pour la sécurité de vos opérations. 