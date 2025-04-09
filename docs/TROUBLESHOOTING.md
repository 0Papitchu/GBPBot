# Guide de Dépannage GBPBot

Ce document fournit des solutions aux problèmes courants que vous pourriez rencontrer lors de l'utilisation de GBPBot.

## 🚀 Problèmes de Lancement

### 🔴 Le bot ne démarre pas

#### Problème 1: Python n'est pas installé ou non disponible
```
Erreur: Python n'est pas installé ou n'est pas dans le PATH.
```

**Solution:**
1. Téléchargez et installez Python 3.8+ depuis [python.org](https://www.python.org/downloads/)
2. Lors de l'installation, cochez l'option "Add Python to PATH"
3. Redémarrez votre terminal/invite de commande et réessayez

#### Problème 2: Fichier gbpbot_launcher.py introuvable
```
Erreur: Fichier gbpbot_launcher.py introuvable.
```

**Solution:**
1. Vérifiez que vous êtes dans le répertoire principal du projet GBPBot
2. Si le fichier est manquant, téléchargez à nouveau le projet ou restaurez-le depuis la sauvegarde

#### Problème 3: Erreur de permission lors de l'exécution du script (Linux/macOS)
```
Permission denied: ./launch_gbpbot.sh
```

**Solution:**
   ```bash
chmod +x launch_gbpbot.sh
./launch_gbpbot.sh
```

### 🔴 Erreurs d'importation

#### Problème: Modules Python manquants
```
ModuleNotFoundError: No module named 'XXX'
```

**Solution:**
1. Installez les dépendances requises:
   ```bash
   pip install -r requirements.txt
   ```

2. Si le problème persiste, essayez de mettre à jour pip:
   ```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
   ```

3. Pour les dépendances problématiques spécifiques:
   ```bash
pip install XXX --no-deps
```

### 🔴 Problèmes avec asyncio (Windows)

#### Problème: Erreur de boucle d'événements
```
RuntimeError: There is no current event loop in thread 'MainThread'
```

**Solution:**
Le lanceur devrait corriger automatiquement ce problème, mais si vous le rencontrez:

1. Utilisez directement `gbpbot_launcher.py`:
   ```bash
python gbpbot_launcher.py
```

2. Si le problème persiste, utilisez la solution temporaire suivante:
```python
# Au début de votre script:
import asyncio
import os

if os.name == 'nt':  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## 💾 Problèmes de Configuration

### 🔴 Fichier .env manquant ou corrompu

#### Problème: Le bot ne trouve pas la configuration
```
ConfigError: Fichier .env introuvable ou inaccessible
```

**Solution:**
1. Créez un nouveau fichier `.env` en copiant `.env.example`:
   ```bash
copy .env.example .env  # Windows
cp .env.example .env    # Linux/macOS
```

2. Modifiez le fichier `.env` pour configurer vos clés API et autres paramètres

### 🔴 Erreur de lecture des clés API

#### Problème: Le bot ne peut pas se connecter aux exchanges
```
APIError: Impossible de se connecter à l'exchange. Vérifiez vos clés API.
```

**Solution:**
1. Vérifiez vos clés API dans le fichier `.env`
2. Assurez-vous que les clés API ont les permissions nécessaires
3. Vérifiez que vous avez activé les bons réseaux pour vos clés API

## 🔧 Problèmes avec les Modules

### 🔴 Module d'Arbitrage

#### Problème: Aucune opportunité d'arbitrage trouvée
```
ArbitrageWarning: Aucune opportunité d'arbitrage détectée après X secondes
```

**Solution:**
1. Vérifiez les paires configurées dans `.env`
2. Assurez-vous que les DEX ciblés sont accessibles
3. Ajustez les seuils de profit minimal dans la configuration

#### Problème: Échec de l'exécution des transactions d'arbitrage
```
TransactionError: La transaction d'arbitrage a échoué
```

**Solution:**
1. Vérifiez le solde du wallet pour les frais de transaction
2. Assurez-vous que le slippage est correctement configuré
3. Vérifiez les limites de gaz dans la configuration

### 🔴 Module de Sniping

#### Problème: Le bot ne détecte pas les nouveaux tokens
```
SnipingWarning: Aucun nouveau token détecté après X minutes
```

**Solution:**
1. Vérifiez que les RPC configurés sont opérationnels
2. Assurez-vous que les DEX surveillés sont correctement configurés
3. Ajustez les filtres de sniping dans la configuration

#### Problème: Le bot détecte mais n'achète pas les tokens
```
SnipingError: Échec de l'achat du token XXX
```

**Solution:**
1. Vérifiez le solde du wallet pour les achats
2. Ajustez les paramètres de sécurité si le token est filtré
3. Vérifiez les limites de gaz dans la configuration

## 🔐 Problèmes de Wallet

### 🔴 Erreur d'accès au wallet

#### Problème: Impossible de charger le wallet
```
WalletError: Impossible de charger le wallet. Vérifiez le chemin ou le mot de passe.
```

**Solution:**
1. Vérifiez le chemin du fichier de wallet dans la configuration
2. Assurez-vous que le mot de passe est correct
3. Recréez le wallet si nécessaire:
```bash
python gbpbot_launcher.py --mode cli
# Puis utiliser l'option de configuration du wallet
```

#### Problème: Solde insuffisant
```
InsufficientBalanceError: Solde insuffisant pour effectuer cette opération
```

**Solution:**
1. Envoyez des fonds au wallet configuré
2. Vérifiez que vous avez sélectionné le bon wallet dans la configuration
3. Assurez-vous d'avoir suffisamment de fonds pour couvrir les frais de gaz

## 📊 Problèmes de Performance

### 🔴 Le bot est lent ou se bloque

#### Problème: Haute consommation de mémoire ou CPU
```
PerformanceWarning: Utilisation élevée des ressources système
```

**Solution:**
1. Réduisez le nombre de paires/tokens surveillés
2. Ajustez les intervalles de surveillance dans la configuration
3. Utilisez un ordinateur plus puissant si possible

#### Problème: Erreurs de timeout avec les RPC
```
RPCError: Timeout en attendant la réponse du nœud
```

**Solution:**
1. Utilisez des RPC plus rapides et fiables
2. Configurez plusieurs RPC pour la redondance
3. Ajustez les timeouts RPC dans la configuration

## 📞 Support Supplémentaire

Si vous rencontrez des problèmes non listés ici:

1. Vérifiez les logs détaillés dans le dossier `logs/`
2. Exécutez le bot en mode debug pour plus d'informations:
```bash
python gbpbot_launcher.py --debug
```
3. Recherchez des problèmes similaires dans les issues du projet
4. Contactez l'équipe de support avec les logs et les détails de votre problème 

## Problèmes liés aux Dépendances d'IA

### Erreur "No module named 'tensorflow.python'"

**Problème**: Cette erreur apparaît lors de l'accès à certaines fonctionnalités qui utilisent TensorFlow, comme les statistiques avancées ou l'assistant IA.

**Solution**:
1. Installez TensorFlow: `pip install tensorflow`
2. Si vous ne souhaitez pas installer TensorFlow (qui peut être volumineux), le bot fonctionnera en mode dégradé avec des fonctionnalités limitées.
3. Exécutez `python gbpbot_launcher.py --check-ai` pour voir quelles fonctionnalités sont disponibles sur votre système.

### Avertissements "PyTorch/TensorFlow/ONNX Runtime n'est pas disponible"

**Problème**: Ces avertissements indiquent que certaines dépendances optionnelles pour les fonctionnalités d'IA ne sont pas installées.

**Solution**:
1. Ce ne sont que des avertissements, le bot continuera à fonctionner avec des fonctionnalités limitées.
2. Si vous souhaitez utiliser toutes les fonctionnalités:
```bash
   pip install tensorflow torch onnxruntime llama-cpp-python
   ```
3. Pour les systèmes avec des ressources limitées, vous pouvez installer uniquement les dépendances nécessaires aux fonctionnalités que vous utilisez (voir la documentation INSTALLATION.md).

### L'affichage des statistiques de trading ne fonctionne pas

**Problème**: Lorsque vous sélectionnez "2. Afficher les statistiques de trading" dans le menu, vous obtenez une erreur.

**Solution**:
1. Vérifiez que le module de performance est correctement installé
2. Si vous obtenez une erreur concernant TensorFlow ou autre bibliothèque d'IA, le bot utilise ces dépendances pour certaines statistiques avancées
3. Vous pouvez:
   - Installer les dépendances nécessaires (voir INSTALLATION.md)
   - Continuer à utiliser le bot sans ces statistiques avancées
4. Exécutez `python gbpbot_launcher.py --check-ai` pour diagnostiquer les problèmes de dépendances d'IA 