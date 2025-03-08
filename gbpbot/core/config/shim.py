
# Stub pour contourner les erreurs
def get(key, default=None):
    return default

# Ajouter ce fichier à l'import du package
if __name__ != "__main__":
    import sys
    import os
    current_dir = os.path.abspath(os.path.dirname(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # S'assurer que ce module est accessible
    try:
        from gbpbot.core.config import get
    except ImportError:
        # Si le module est déjà défini, ne pas le redéfinir
        pass
