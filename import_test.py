try:
    import xprocess
    print('xprocess importé avec succès')
except ImportError as e:
    print(f'Erreur: {e}')

try:
    import pytest_xprocess
    print('pytest_xprocess importé avec succès')
except ImportError as e:
    print(f'Erreur: {e}')

try:
    from pytest_xprocess import getrootdir
    print('pytest_xprocess.getrootdir importé avec succès')
except ImportError as e:
    print(f'Erreur: {e}') 