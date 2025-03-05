# Documentation GBPBot

Ce répertoire contient la documentation de GBPBot générée avec Sphinx.

## Structure de la documentation

La documentation est organisée comme suit :

- `source/` : Contient les fichiers source de la documentation (fichiers RST)
- `build/` : Contient la documentation générée (HTML, PDF, etc.)
- `generate_autodoc.py` : Script pour générer automatiquement la documentation à partir des docstrings
- `build_docs.py` : Script pour générer la documentation HTML

## Prérequis

Pour générer la documentation, vous devez avoir installé :

- Python 3.8+
- Sphinx (`pip install sphinx`)
- Thème ReadTheDocs (`pip install sphinx-rtd-theme`)

## Génération de la documentation

### Installation initiale

Si vous n'avez pas encore configuré la documentation, exécutez le script de configuration :

```bash
python setup_documentation.py
```

Ce script va :
1. Installer Sphinx et le thème ReadTheDocs si nécessaire
2. Initialiser la structure de documentation
3. Configurer le thème ReadTheDocs
4. Créer les fichiers RST de base
5. Créer les scripts de génération de documentation

### Génération de la documentation HTML

Pour générer la documentation HTML, exécutez :

```bash
cd docs
python build_docs.py
```

La documentation générée sera disponible dans `docs/build/html/`. Ouvrez `index.html` dans votre navigateur pour la consulter.

## Mise à jour de la documentation

### Mise à jour automatique

Un hook pre-commit a été configuré pour vérifier si la documentation est à jour avant chaque commit. Si la documentation n'est pas à jour, le commit sera refusé.

Pour mettre à jour la documentation manuellement :

```bash
cd docs
python generate_autodoc.py
```

### Ajout de nouvelles pages

Pour ajouter une nouvelle page à la documentation :

1. Créez un nouveau fichier RST dans `docs/source/`
2. Ajoutez-le à la table des matières dans `docs/source/index.rst`

## Bonnes pratiques pour les docstrings

Pour que la documentation soit générée correctement, suivez ces bonnes pratiques pour les docstrings :

### Format des docstrings

Utilisez le format Google pour les docstrings :

```python
def fonction(param1, param2):
    """
    Description de la fonction.
    
    Args:
        param1: Description du paramètre 1.
        param2: Description du paramètre 2.
    
    Returns:
        Description de la valeur de retour.
    
    Raises:
        ExceptionType: Description de l'exception.
    
    Examples:
        >>> fonction(1, 2)
        3
    """
    return param1 + param2
```

### Documentation des classes

Pour les classes, documentez :
- La classe elle-même
- Les attributs de la classe
- Les méthodes de la classe

```python
class MaClasse:
    """
    Description de la classe.
    
    Attributes:
        attr1: Description de l'attribut 1.
        attr2: Description de l'attribut 2.
    """
    
    def __init__(self, param):
        """
        Initialise une nouvelle instance.
        
        Args:
            param: Description du paramètre.
        """
        self.attr1 = param
        self.attr2 = None
```

### Types

Utilisez les annotations de type Python pour documenter les types :

```python
from typing import Dict, List, Optional

def fonction(param1: int, param2: Optional[str] = None) -> Dict[str, List[int]]:
    """
    Description de la fonction.
    
    Args:
        param1: Description du paramètre 1.
        param2: Description du paramètre 2. Par défaut None.
    
    Returns:
        Dictionnaire avec des listes d'entiers.
    """
    return {"resultat": [param1]}
```

## Exemple

Consultez le fichier `docstring_example.py` pour un exemple complet de documentation avec docstrings.

## Ressources

- [Documentation Sphinx](https://www.sphinx-doc.org/)
- [Documentation du thème ReadTheDocs](https://sphinx-rtd-theme.readthedocs.io/)
- [Guide des docstrings Google](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) 