@echo off
setlocal enabledelayedexpansion

:: Script de démarrage GBPBot pour Windows
:: Ce script vérifie les prérequis puis lance GBPBot

title GBPBot - Démarrage

:: Définir les couleurs
set "BLUE=[94m"
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "RESET=[0m"

echo %BLUE%============================================================%RESET%
echo %BLUE%                     GBPBot - Démarrage                     %RESET%
echo %BLUE%============================================================%RESET%
echo.

:: Vérifier si Python est installé
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo %RED%Python n'est pas installé ou n'est pas dans le PATH.%RESET%
    echo %RED%Veuillez installer Python 3.9+ depuis https://www.python.org/%RESET%
    echo.
    pause
    exit /b 1
)

:: Vérifier la version de Python (doit être 3.9+)
for /f "tokens=2" %%V in ('python -c "import sys; print(sys.version_info.major)"') do set "py_major=%%V"
for /f "tokens=2" %%V in ('python -c "import sys; print(sys.version_info.minor)"') do set "py_minor=%%V"

if %py_major% lss 3 (
    echo %RED%Version de Python incompatible. Python 3.9+ requis.%RESET%
    echo %RED%Version installée: %py_major%.%py_minor%%RESET%
    echo.
    pause
    exit /b 1
)

if %py_major% equ 3 (
    if %py_minor% lss 9 (
        echo %RED%Version de Python incompatible. Python 3.9+ requis.%RESET%
        echo %RED%Version installée: %py_major%.%py_minor%%RESET%
        echo.
        pause
        exit /b 1
    )
)

echo %GREEN%Python %py_major%.%py_minor% OK%RESET%

:: Créer un environnement virtuel si nécessaire
if not exist "venv" (
    echo %YELLOW%Création de l'environnement virtuel...%RESET%
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo %RED%Erreur lors de la création de l'environnement virtuel.%RESET%
        pause
        exit /b 1
    )
)

:: Activer l'environnement virtuel
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo %RED%Erreur lors de l'activation de l'environnement virtuel.%RESET%
    pause
    exit /b 1
)

:: Installer/mettre à jour les dépendances
echo %YELLOW%Installation/mise à jour des dépendances...%RESET%
pip install -q -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo %RED%Erreur lors de l'installation des dépendances.%RESET%
    pause
    exit /b 1
)

:: Vérifier l'existence du fichier .env
if not exist ".env" (
    if exist ".env.example" (
        echo %YELLOW%.env non trouvé. Copie du fichier exemple...%RESET%
        copy ".env.example" ".env" >nul
        echo %YELLOW%Veuillez configurer le fichier .env avec vos paramètres.%RESET%
        echo %YELLOW%Exécutez scripts\setup_run_environment.py pour configurer.%RESET%
        pause
        exit /b 1
    ) else (
        echo %RED%Fichier .env ou .env.example introuvable!%RESET%
        pause
        exit /b 1
    )
)

:: Vérifier si le système est prêt
echo %YELLOW%Vérification de l'environnement...%RESET%
python scripts\system_check.py
if %ERRORLEVEL% neq 0 (
    echo %RED%Des problèmes ont été détectés lors de la vérification du système.%RESET%
    echo %YELLOW%Consultez les logs pour plus de détails.%RESET%
    echo %YELLOW%Voulez-vous continuer quand même? (O/N)%RESET%
    choice /c ON /n
    if %ERRORLEVEL% equ 2 (
        exit /b 1
    )
)

:: Afficher le menu de démarrage
echo.
echo %BLUE%============================================================%RESET%
echo %BLUE%                   GBPBot - Mode de lancement                %RESET%
echo %BLUE%============================================================%RESET%
echo.
echo %YELLOW%Choisissez le mode de lancement:%RESET%
echo %YELLOW%1. Mode normal (CLI)%RESET%
echo %YELLOW%2. Mode simulation (sans transactions réelles)%RESET%
echo %YELLOW%3. Mode debug (plus de logs)%RESET%
echo %YELLOW%4. Dashboard web%RESET%
echo %YELLOW%5. Quitter%RESET%
echo.

choice /c 12345 /n
set choice=%ERRORLEVEL%

if %choice% equ 1 (
    echo %GREEN%Démarrage de GBPBot en mode normal...%RESET%
    python run_gbpbot.py
) else if %choice% equ 2 (
    echo %GREEN%Démarrage de GBPBot en mode simulation...%RESET%
    python run_gbpbot.py --simulation
) else if %choice% equ 3 (
    echo %GREEN%Démarrage de GBPBot en mode debug...%RESET%
    python run_gbpbot.py --debug
) else if %choice% equ 4 (
    echo %GREEN%Démarrage du dashboard web...%RESET%
    python run_dashboard.py
) else if %choice% equ 5 (
    echo %YELLOW%Au revoir!%RESET%
    exit /b 0
)

:: Fin du script
echo.
echo %BLUE%============================================================%RESET%
echo %BLUE%                     GBPBot - Terminé                        %RESET%
echo %BLUE%============================================================%RESET%

pause 