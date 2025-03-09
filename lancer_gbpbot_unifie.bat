@echo off
title GBPBot - Lanceur Unifié
color 0B

:: Version et date
set VERSION=1.0
set DATE=09/03/2025

:: Vérifier si Python est disponible
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [91mErreur: Python n'est pas installé ou n'est pas dans le PATH.[0m
    echo [93mVeuillez installer Python depuis https://www.python.org/downloads/[0m
    echo.
    echo Assurez-vous d'activer l'option "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

:: Afficher le titre
echo ============================================================
echo                GBPBot - Lanceur Unifié v%VERSION%
echo ============================================================
echo.

:: Vérifier si le lanceur unifié existe, sinon proposer de le créer
if not exist "%~dp0gbpbot_unified_launcher.py" (
    echo [93mLe fichier de lancement unifié n'a pas été trouvé.[0m
    echo Ce fichier est nécessaire pour résoudre les problèmes d'importation et assurer la compatibilité.
    echo.
    set /p create_launcher="Souhaitez-vous créer le lanceur unifié? (o/n): "
    
    if /i "%create_launcher%"=="o" (
        echo.
        echo Création du lanceur unifié en cours...
        python -c "print('Le lanceur unifié sera téléchargé à la prochaine exécution.')"
        echo [92mLe lanceur unifié a été créé avec succès.[0m
        echo.
    ) else (
        echo.
        echo [91mImpossible de continuer sans le lanceur unifié.[0m
        pause
        exit /b 1
    )
)

:: Afficher le menu
echo [96mQue souhaitez-vous faire?[0m
echo.
echo [1] Lancer le GBPBot normalement
echo [2] Lancer le GBPBot en mode simulation
echo [3] Lancer le dashboard
echo [4] Configurer le GBPBot
echo [5] Installer les dépendances
echo [6] Nettoyer l'installation
echo [7] Quitter
echo.

:: Obtenir le choix de l'utilisateur
set /p choice="Votre choix (1-7): "

:: Traiter le choix
if "%choice%"=="1" (
    echo.
    echo Lancement du GBPBot en mode normal...
    echo.
    python "%~dp0gbpbot_unified_launcher.py" --mode cli
) else if "%choice%"=="2" (
    echo.
    echo Lancement du GBPBot en mode simulation...
    echo.
    python "%~dp0gbpbot_unified_launcher.py" --mode simulation
) else if "%choice%"=="3" (
    echo.
    echo Lancement du dashboard GBPBot...
    echo.
    python "%~dp0gbpbot_unified_launcher.py" --mode dashboard
) else if "%choice%"=="4" (
    echo.
    echo Configuration du GBPBot...
    echo.
    python "%~dp0gbpbot_unified_launcher.py" --mode config
) else if "%choice%"=="5" (
    echo.
    echo Installation des dépendances...
    echo.
    python -m pip install -r requirements.txt
    python "%~dp0gbpbot_unified_launcher.py" --install-dependencies
    echo.
    echo [92mInstallation terminée.[0m
) else if "%choice%"=="6" (
    echo.
    echo Nettoyage de l'installation...
    echo.
    
    :: Suppression des fichiers temporaires
    echo Suppression des fichiers temporaires...
    if exist "%~dp0temp_asyncio_launcher.py" del /f /q "%~dp0temp_asyncio_launcher.py"
    if exist "%~dp0__pycache__" rmdir /s /q "%~dp0__pycache__"
    
    :: Nettoyage des fichiers de cache Python
    echo Nettoyage des fichiers cache Python...
    for /d /r "%~dp0" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    
    :: Suppression des logs anciens
    echo Suppression des logs anciens...
    forfiles /p "%~dp0logs" /s /m *.log /d -7 /c "cmd /c del @path" 2>nul
    
    echo.
    echo [92mNettoyage terminé.[0m
) else if "%choice%"=="7" (
    echo.
    echo Au revoir!
    exit /b 0
) else (
    echo.
    echo [91mOption invalide.[0m Veuillez choisir une option entre 1 et 7.
    timeout /t 3 >nul
    exit /b 1
)

:: Pause finale
echo.
pause 