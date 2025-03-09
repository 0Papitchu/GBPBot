# Guide de Gestion des Fichiers d'Environnement GBPBot

Ce document explique comment gérer en toute sécurité les fichiers d'environnement (`.env`) de GBPBot, qui contiennent des informations sensibles comme des clés privées, des API keys et des tokens d'authentification.

## Table des matières

1. [Présentation des fichiers d'environnement](#1-présentation-des-fichiers-denvironnement)
2. [Protection des données sensibles](#2-protection-des-données-sensibles)
3. [Outils de gestion des fichiers d'environnement](#3-outils-de-gestion-des-fichiers-denvironnement)
4. [Installation des fichiers d'environnement](#4-installation-des-fichiers-denvironnement)
5. [Variables d'environnement requises](#5-variables-denvironnement-requises)
6. [Fichiers d'environnement spécialisés](#6-fichiers-denvironnement-spécialisés)
7. [Résolution des problèmes](#7-résolution-des-problèmes)

## 1. Présentation des fichiers d'environnement

GBPBot utilise des fichiers `.env` pour stocker toutes les configurations sensibles du système, notamment :

- Clés privées des wallets
- Adresses des wallets
- Tokens d'API (Binance, etc.)
- Tokens Telegram
- URLs RPC des nodes blockchain
- Paramètres de trading

Les différents types de fichiers d'environnement :

- `.env` : Le fichier principal utilisé par le GBPBot
- `.env.local` : Fichier de configuration local (non commité dans Git)
- `.env.example` : Modèle de fichier sans données sensibles (partageable)
- `.env.backup_*` : Sauvegardes automatiques
- `.env.optimized` : Paramètres optimisés pour la performance

## 2. Protection des données sensibles

Pour protéger vos informations sensibles :

1. **Les fichiers `.env` ne doivent jamais être partagés ou publiés**
2. **Toujours utiliser `.env.local` (exclu de Git) pour vos données sensibles**
3. **Les fichiers `.env*` sont automatiquement exclus du suivi Git** (via `.gitignore`)
4. **Ne stockez jamais d'informations sensibles dans des fichiers inclus dans Git**
5. **Effectuez régulièrement des sauvegardes de vos fichiers `.env`**

## 3. Outils de gestion des fichiers d'environnement

GBPBot fournit plusieurs outils pour gérer facilement vos fichiers d'environnement :

### Script Windows (`configure_env.bat`)

Lancez `configure_env.bat` depuis la racine du projet pour :
- Créer des sauvegardes de votre fichier `.env`
- Initialiser `.env` à partir de `.env.local`
- Valider la configuration de votre fichier `.env`

### Script Python (`scripts/setup_env.py`)

Utilisable directement ou via le script batch :
```bash
# Créer une sauvegarde
python scripts/setup_env.py 1

# Initialiser .env à partir de .env.local
python scripts/setup_env.py 2

# Valider la configuration
python scripts/setup_env.py 3
```

## 4. Installation des fichiers d'environnement

Pour configurer correctement GBPBot :

1. Copiez `.env.example` vers `.env.local`
   ```bash
   cp .env.example .env.local
   ```

2. Modifiez `.env.local` avec vos informations personnelles
   ```bash
   nano .env.local # ou utilisez votre éditeur préféré
   ```

3. Utilisez l'outil de configuration pour initialiser `.env` à partir de `.env.local`
   ```bash
   # Sur Windows
   configure_env.bat
   # Puis sélectionnez l'option 2
   
   # OU avec Python directement
   python scripts/setup_env.py 2
   ```

## 5. Variables d'environnement requises

Pour un fonctionnement optimal, votre fichier `.env` doit contenir au minimum :

### Configuration Générale
```
BOT_MODE=manual|auto|telegram
DEFAULT_BLOCKCHAIN=solana|avalanche
DEBUG_MODE=false
ENVIRONMENT=development|production
LOG_LEVEL=INFO
```

### Configuration Telegram
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_AUTHORIZED_USERS=user_id_1,user_id_2
```

### Wallets & API Keys
```
PRIVATE_KEY=your_wallet_private_key
WALLET_ADDRESS=your_wallet_address
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

## 6. Fichiers d'environnement spécialisés

### `.env.optimized`
Contient des paramètres supplémentaires pour l'optimisation des performances :
```
MAX_TRANSACTION_HISTORY=10000
MAX_TOKEN_CACHE_SIZE=2000
MAX_BLACKLIST_SIZE=10000
MAX_CACHED_OPPORTUNITIES=5000
RPC_CONNECTION_LIMIT=36
ML_MAX_MEMORY_USAGE=4060
ML_GPU_ACCELERATION=auto
```

### `.env.backup_*`
Sauvegardes automatiques générées par l'outil de gestion des environnements avec un timestamp dans le nom de fichier.

## 7. Résolution des problèmes

### Erreur "Fichier `.env` manquant"
Utilisez l'outil de configuration pour initialiser votre fichier `.env` :
```bash
# Sur Windows
configure_env.bat
# Puis sélectionnez l'option 2
```

### Variables manquantes ou invalides
Validez votre configuration avec l'outil de validation :
```bash
# Sur Windows
configure_env.bat
# Puis sélectionnez l'option 3
```

### Problèmes de lecture des variables
- Vérifiez que le format des variables est correct (pas d'espaces autour du signe égal)
- Assurez-vous que les valeurs sont bien entourées de guillemets si elles contiennent des espaces

### Informations sensibles exposées
Si vous pensez avoir exposé vos informations sensibles :
1. Modifiez immédiatement vos clés API et mots de passe
2. Créez un nouveau wallet et transférez vos fonds
3. Générez un nouveau token Telegram
4. Mettez à jour votre fichier `.env.local` avec les nouvelles informations
5. Régénérez votre fichier `.env` 