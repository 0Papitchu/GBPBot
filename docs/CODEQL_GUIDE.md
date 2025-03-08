# Guide d'utilisation de CodeQL pour GBPBot

## Introduction

CodeQL est un outil d'analyse de code puissant qui permet de détecter les vulnérabilités de sécurité et les problèmes de qualité de code. Ce guide explique comment configurer et utiliser CodeQL avec le projet GBPBot.

## Activation de CodeQL dans GitHub

Pour activer CodeQL dans votre dépôt GitHub:

1. Accédez à l'onglet **Settings** de votre dépôt
2. Cliquez sur **Security & analysis** dans le menu de gauche
3. Trouvez **Code scanning** et cliquez sur **Set up** ou **Enable**
4. Sélectionnez **GitHub Advanced Security** pour activer toutes les fonctionnalités

## Configuration de CodeQL

Le projet GBPBot utilise une configuration personnalisée pour CodeQL, définie dans le fichier `.github/codeql/codeql-config.yml`. Cette configuration:

- Limite l'analyse aux répertoires pertinents (`gbpbot`, `scripts`, `tests`)
- Exclut les répertoires non pertinents (environnements virtuels, fichiers de documentation, etc.)
- Définit des règles spécifiques pour l'analyse du code Python

## Workflow GitHub Actions

Le workflow CodeQL est défini dans `.github/workflows/codeql-analysis.yml`. Ce workflow:

- S'exécute automatiquement sur les branches principales (`main`, `master`, `dev`)
- S'exécute lors des pull requests vers les branches principales
- S'exécute selon un calendrier hebdomadaire (tous les lundis à minuit)
- Installe les dépendances nécessaires avant l'analyse
- Assure que la structure de répertoires requise existe
- Exécute l'analyse CodeQL et publie les résultats

## Résolution des problèmes courants

### Erreur "No such file or directory: 'core'"

Cette erreur se produit lorsque CodeQL ne trouve pas la structure de répertoires attendue. Le workflow inclut une étape pour créer cette structure si elle n'existe pas:

```yaml
- name: Ensure directory structure
  run: |
    mkdir -p gbpbot/core
    touch gbpbot/core/__init__.py
    mkdir -p scripts
    touch scripts/__init__.py
```

### Erreur "Code scanning is not enabled for this repository"

Cette erreur indique que l'analyse de code n'est pas activée dans les paramètres du dépôt. Suivez les étapes d'activation décrites ci-dessus.

### Problèmes avec les dépendances Python

Si l'analyse échoue en raison de problèmes de dépendances, assurez-vous que:

1. Les fichiers `requirements.txt` et `requirements-core.txt` sont à jour
2. Toutes les dépendances nécessaires sont installées dans l'étape d'installation
3. L'option `setup-python-dependencies: true` est définie dans la configuration CodeQL

## Interprétation des résultats

Les résultats de l'analyse CodeQL sont disponibles dans l'onglet **Security** de votre dépôt GitHub, sous **Code scanning alerts**. Les alertes sont classées par:

- **Sévérité**: Critique, Élevée, Moyenne, Faible
- **Type**: Sécurité, Maintenabilité, Fiabilité
- **Tag**: Injection SQL, XSS, Fuite de mémoire, etc.

## Bonnes pratiques

1. **Résolvez rapidement les alertes critiques**: Les problèmes de sécurité critiques doivent être traités en priorité
2. **Vérifiez régulièrement les résultats**: Consultez les résultats après chaque analyse
3. **Améliorez la configuration**: Ajustez le fichier de configuration pour réduire les faux positifs
4. **Intégrez dans le processus de développement**: Utilisez les résultats pour améliorer la qualité du code

## Ressources supplémentaires

- [Documentation officielle de CodeQL](https://codeql.github.com/docs/)
- [Langage de requête CodeQL](https://codeql.github.com/docs/writing-codeql-queries/ql-language-reference/)
- [Bibliothèque de requêtes CodeQL](https://github.com/github/codeql)

## Support

Si vous rencontrez des problèmes avec CodeQL dans le projet GBPBot, veuillez ouvrir une issue sur GitHub en incluant:

1. Le message d'erreur complet
2. Les étapes pour reproduire le problème
3. Les logs pertinents
4. La version de CodeQL utilisée 