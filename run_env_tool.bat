@echo off
set SCRIPT_PATH=%~dp0
cd %SCRIPT_PATH%

echo === Outil de gestion des fichiers d'environnement GBPBot ===
echo.
echo Ce script permet de gérer vos fichiers .env

if not exist "scripts\setup_env.py" (
    echo Erreur: Le fichier scripts\setup_env.py n'a pas été trouvé!
    echo Chemin actuel: %CD%
    echo.
    echo Contenu du répertoire scripts:
    dir scripts\
    pause
    exit /b 1
)

echo Menu:
echo 1. Créer une sauvegarde du fichier .env
echo 2. Copier .env.local vers .env
echo 3. Valider le fichier .env
echo 4. Quitter
echo.

choice /c 1234 /n /m "Votre choix (1-4): "

if errorlevel 4 goto :eof
if errorlevel 3 goto validate
if errorlevel 2 goto copy
if errorlevel 1 goto backup

:backup
echo.
echo Création d'une sauvegarde...
python scripts\setup_env.py 1
goto end

:copy
echo.
echo Initialisation du fichier .env...
python scripts\setup_env.py 2
goto end

:validate
echo.
echo Validation du fichier .env...
python scripts\setup_env.py 3
goto end

:end
echo.
pause 