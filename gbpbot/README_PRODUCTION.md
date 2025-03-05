# Guide de Déploiement en Production de GBPBot

Ce guide détaille les étapes nécessaires pour déployer GBPBot en production de manière sécurisée et stable.

## Prérequis

- Python 3.8+ installé
- Accès à un serveur Linux (recommandé Ubuntu 20.04 LTS ou plus récent)
- Accès root ou sudo pour l'installation des dépendances système
- Clés API pour les fournisseurs blockchain (Infura, Alchemy, etc.)
- Portefeuille crypto avec des fonds suffisants pour les transactions

## 1. Installation

### 1.1 Cloner le dépôt

```bash
git clone https://github.com/votre-username/gbpbot.git
cd gbpbot
```

### 1.2 Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
venv\Scripts\activate  # Sur Windows
```

### 1.3 Installer les dépendances

```bash
pip install -r requirements.txt
```

### 1.4 Configurer les variables d'environnement

Copiez le fichier `.env.example` vers `.env` et modifiez-le avec vos propres valeurs :

```bash
cp .env.example .env
nano .env  # ou utilisez votre éditeur préféré
```

Variables importantes à configurer :
- `WEB3_PROVIDER_URL` : URL de votre fournisseur Web3 (Infura, Alchemy, etc.)
- `WALLET_PRIVATE_KEY` : Clé privée de votre portefeuille (gardez-la secrète !)
- `GBPBOT_API_KEY` : Clé API pour sécuriser l'accès à l'API (générez une clé forte)
- `GBPBOT_IP_WHITELIST` : Liste des IPs autorisées à accéder à l'API

## 2. Tests avant déploiement

Avant de déployer en production, exécutez les tests pour vérifier que tout fonctionne correctement :

```bash
python production_test.py
```

Ce script vérifiera :
- La connexion Web3
- L'initialisation des modules (mempool_sniping, gas_optimizer, bundle_checker)
- Le démarrage des serveurs API et dashboard
- La sécurité de l'API

## 3. Génération des certificats SSL

Pour sécuriser les communications, générez des certificats SSL :

```bash
python generate_ssl_cert.py --output-dir ssl --days 365 --common-name votre-domaine.com
```

Pour un environnement de production réel, utilisez Let's Encrypt ou un autre fournisseur de certificats SSL reconnu.

## 4. Déploiement en production

### 4.1 Utilisation du script de déploiement automatique

Le script `deploy_production.py` automatise le processus de déploiement :

```bash
python deploy_production.py
```

Options disponibles :
- `--config` : Chemin vers un fichier de configuration personnalisé
- `--create-service` : Créer un service systemd pour démarrer GBPBot au démarrage du système

### 4.2 Configuration personnalisée

Vous pouvez créer un fichier de configuration JSON pour personnaliser le déploiement :

```json
{
  "api_host": "0.0.0.0",
  "api_port": 5000,
  "dashboard_host": "0.0.0.0",
  "dashboard_port": 5001,
  "use_https": true,
  "ssl_cert_path": "/chemin/vers/cert.pem",
  "ssl_key_path": "/chemin/vers/key.pem",
  "backup_before_deploy": true,
  "run_tests_before_deploy": true
}
```

Puis utilisez-le lors du déploiement :

```bash
python deploy_production.py --config votre_config.json
```

### 4.3 Création d'un service systemd

Pour que GBPBot démarre automatiquement au démarrage du système :

```bash
python deploy_production.py --create-service
sudo systemctl start gbpbot
```

## 5. Surveillance en production

### 5.1 Démarrer le moniteur de production

```bash
python monitor_production.py
```

Options disponibles :
- `--config` : Chemin vers un fichier de configuration de surveillance personnalisé

### 5.2 Configuration des alertes

Modifiez le fichier `.env` pour configurer les alertes par email ou Telegram :

```
# Alertes Email
GBPBOT_EMAIL_FROM=votre-email@exemple.com
GBPBOT_EMAIL_TO=destinataire@exemple.com
GBPBOT_SMTP_SERVER=smtp.gmail.com
GBPBOT_SMTP_PORT=587
GBPBOT_SMTP_USER=votre-email@exemple.com
GBPBOT_SMTP_PASSWORD=votre-mot-de-passe

# Alertes Telegram
GBPBOT_TELEGRAM_TOKEN=votre-token-bot
GBPBOT_TELEGRAM_CHAT_ID=votre-chat-id
```

Puis activez les alertes dans le fichier de configuration de surveillance :

```json
{
  "enable_email_alerts": true,
  "enable_telegram_alerts": true,
  "cpu_threshold": 80,
  "memory_threshold": 80,
  "disk_threshold": 90
}
```

## 6. Sécurité en production

### 6.1 Recommandations de sécurité

- Utilisez toujours HTTPS pour l'API et le dashboard
- Limitez l'accès à l'API avec une liste blanche d'IPs
- Utilisez une clé API forte et changez-la régulièrement
- Stockez les clés privées de manière sécurisée
- Utilisez un pare-feu pour limiter l'accès aux ports
- Mettez régulièrement à jour le système et les dépendances

### 6.2 Vérification de la sécurité

Exécutez le script de test de sécurité pour vérifier la configuration :

```bash
python security_test.py
```

## 7. Maintenance

### 7.1 Sauvegardes

Des sauvegardes sont automatiquement créées lors du déploiement. Pour créer une sauvegarde manuelle :

```bash
python deploy_production.py  # Avec l'option backup_before_deploy=true
```

Les sauvegardes sont stockées dans le répertoire `backups/`.

### 7.2 Mise à jour

Pour mettre à jour GBPBot :

1. Arrêtez les services :
```bash
sudo systemctl stop gbpbot
```

2. Mettez à jour le code :
```bash
git pull
```

3. Mettez à jour les dépendances :
```bash
pip install -r requirements.txt
```

4. Redéployez :
```bash
python deploy_production.py
```

## 8. Résolution des problèmes

### 8.1 Logs

Les logs sont stockés dans les fichiers suivants :
- `bot.log` : Log principal du bot
- `gbpbot_api.log` : Log de l'API
- `gbpbot_dashboard.log` : Log du dashboard
- `monitor.log` : Log du moniteur de production
- `deployment.log` : Log du déploiement

### 8.2 Problèmes courants

- **L'API ne démarre pas** : Vérifiez les logs et assurez-vous que le port n'est pas déjà utilisé
- **Erreurs de connexion Web3** : Vérifiez votre URL de fournisseur et votre connexion Internet
- **Transactions échouées** : Vérifiez le solde de votre portefeuille et les frais de gas
- **Erreurs SSL** : Vérifiez que vos certificats sont valides et correctement configurés

## 9. Contact et support

Pour toute question ou problème, contactez l'équipe de support :
- Email : support@gbpbot.com
- Telegram : @GBPBotSupport

---

© 2023 GBPBot Team. Tous droits réservés. 