@echo off
REM Script de démarrage du moniteur de performances GBPBot
REM Auteur: GBPBot Team
REM Date: 2025-03-06

echo ===================================================
echo    GBPBot - Démarrage du Moniteur de Performances
echo ===================================================
echo.

REM Vérification de Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python 3.7+ et réessayer.
    pause
    exit /b 1
)

REM Vérification des dépendances
if not exist monitor_performance.py (
    echo [ERREUR] Le fichier monitor_performance.py est introuvable.
    echo Assurez-vous d'être dans le bon répertoire.
    pause
    exit /b 1
)

echo [INFO] Vérification des dépendances...
python -c "import psutil, matplotlib" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installation des dépendances requises...
    python install_performance_monitor.py
    if %ERRORLEVEL% NEQ 0 (
        echo [ERREUR] L'installation des dépendances a échoué.
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Démarrage du moniteur de performances...
echo [INFO] Appuyez sur Ctrl+C pour arrêter le moniteur.
echo.

REM Recherche du processus GBPBot
for /f "tokens=1" %%i in ('tasklist /fi "IMAGENAME eq python.exe" /fo csv /nh ^| findstr /i "gbpbot main.py"') do (
    set GBPBOT_PID=%%i
    echo [INFO] Processus GBPBot trouvé avec PID: %%i
    goto :start_monitor
)

:start_monitor
if defined GBPBOT_PID (
    echo [INFO] Surveillance du processus GBPBot (PID: %GBPBOT_PID%)
    python monitor_performance.py --pid %GBPBOT_PID%
) else (
    echo [INFO] Aucun processus GBPBot trouvé, surveillance du système uniquement.
    python monitor_performance.py
)

echo.
echo [INFO] Moniteur de performances arrêté.
pause 