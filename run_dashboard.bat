@echo off
REM Script de lancement du Dashboard GBPBot pour Windows

echo =====================================
echo      GBPBot Dashboard Launcher
echo =====================================
echo.

REM Vérifier que Python est installé
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.8 ou supérieur.
    pause
    exit /b 1
)

REM Vérifier la version de Python
for /f "tokens=2" %%V in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%V
for /f "tokens=1 delims=." %%M in ("%PYTHON_VERSION%") do set PYTHON_VERSION_MAJOR=%%M
for /f "tokens=2 delims=." %%m in ("%PYTHON_VERSION%") do set PYTHON_VERSION_MINOR=%%m

if %PYTHON_VERSION_MAJOR% LSS 3 (
    echo [X] Python 3.8 ou supérieur est requis. Version détectée: %PYTHON_VERSION%
    pause
    exit /b 1
)

if %PYTHON_VERSION_MAJOR% EQU 3 (
    if %PYTHON_VERSION_MINOR% LSS 8 (
        echo [X] Python 3.8 ou supérieur est requis. Version détectée: %PYTHON_VERSION%
        pause
        exit /b 1
    )
)

echo [V] Python %PYTHON_VERSION% détecté

REM Vérifier que le dossier GBPBot existe
if not exist "gbpbot" (
    echo [X] Le dossier 'gbpbot' n'existe pas dans le répertoire courant.
    echo Veuillez exécuter ce script depuis le répertoire racine du projet GBPBot.
    pause
    exit /b 1
)

REM Vérifier que le module dashboard existe
if not exist "gbpbot\dashboard" (
    echo [X] Le module dashboard n'existe pas dans le projet GBPBot.
    echo Veuillez vérifier l'installation du projet.
    pause
    exit /b 1
)

REM Vérifier les dépendances
echo [?] Vérification des dépendances...

set MISSING_DEPS=0
set DEPS=fastapi uvicorn pydantic websockets

for %%d in (%DEPS%) do (
    python -c "import %%d" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [X] Module Python '%%d' manquant
        set MISSING_DEPS=1
    )
)

if %MISSING_DEPS% EQU 1 (
    echo.
    set /p INSTALL="Des dépendances sont manquantes. Voulez-vous les installer maintenant? (o/n): "
    if /i "%INSTALL%" EQU "o" (
        echo Installation des dépendances...
        pip install -r requirements.txt
    ) else (
        echo Installation annulée. Certaines fonctionnalités peuvent ne pas fonctionner.
    )
)

REM Demander les options de lancement
echo.
echo Options de lancement du dashboard:
echo.
echo 1. Lancement standard (localhost:8000)
echo 2. Accès réseau (0.0.0.0:8000)
echo 3. Mode simulation (génération de données fictives)
echo 4. Mode développement (simulation + debug)
echo 5. Mode personnalisé
echo 6. Quitter
echo.
set /p OPTION="Choisissez une option (1-6): "

if "%OPTION%" EQU "1" (
    echo [>] Lancement du dashboard en mode standard...
    python -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000
) else if "%OPTION%" EQU "2" (
    echo [>] Lancement du dashboard avec accès réseau...
    python -m gbpbot.dashboard.run_dashboard --host 0.0.0.0 --port 8000
) else if "%OPTION%" EQU "3" (
    echo [>] Lancement du dashboard en mode simulation...
    python -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000 --simulate
) else if "%OPTION%" EQU "4" (
    echo [>] Lancement du dashboard en mode développement...
    python -m gbpbot.dashboard.run_dashboard --host 127.0.0.1 --port 8000 --simulate --log-level DEBUG
) else if "%OPTION%" EQU "5" (
    set /p HOST="Adresse d'hôte (défaut: 127.0.0.1): "
    if "%HOST%" EQU "" set HOST=127.0.0.1
    
    set /p PORT="Port (défaut: 8000): "
    if "%PORT%" EQU "" set PORT=8000
    
    set /p SIMULATE="Activer la simulation? (o/n, défaut: n): "
    if /i "%SIMULATE%" EQU "o" (
        set SIMULATE_FLAG=--simulate
    ) else (
        set SIMULATE_FLAG=
    )
    
    set /p LOG_LEVEL="Niveau de log (DEBUG/INFO/WARNING/ERROR/CRITICAL, défaut: INFO): "
    if "%LOG_LEVEL%" EQU "" set LOG_LEVEL=INFO
    
    echo [>] Lancement du dashboard avec les options personnalisées...
    python -m gbpbot.dashboard.run_dashboard --host %HOST% --port %PORT% %SIMULATE_FLAG% --log-level %LOG_LEVEL%
) else if "%OPTION%" EQU "6" (
    echo Au revoir!
    exit /b 0
) else (
    echo [X] Option non valide
    exit /b 1
)

pause 