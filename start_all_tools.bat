@echo off
echo ===================================================
echo     GBPBot - Demarrage des Outils d'Optimisation
echo ===================================================
echo.

echo [1/4] Verification de l'environnement...
if not exist "monitor_performance.py" (
    echo ERREUR: Le fichier monitor_performance.py est introuvable.
    goto :error
)
if not exist "auto_optimizer.py" (
    echo ERREUR: Le fichier auto_optimizer.py est introuvable.
    goto :error
)

echo [2/4] Demarrage du moniteur de performances...
start "GBPBot - Moniteur de Performances" cmd /c "python monitor_performance.py"
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de demarrer le moniteur de performances.
    goto :error
)

echo [3/4] Attente de demarrage du moniteur (2 secondes)...
timeout /t 2 /nobreak > nul

echo [4/4] Demarrage de l'optimiseur automatique...
start "GBPBot - Optimiseur Automatique" cmd /c "python auto_optimizer.py"
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de demarrer l'optimiseur automatique.
    goto :error
)

echo.
echo ===================================================
echo            Outils d'optimisation demarres !
echo ===================================================
echo.
echo Les outils suivants sont en cours d'execution :
echo  - Moniteur de Performances (fenetre separee)
echo  - Optimiseur Automatique (fenetre separee)
echo.
echo Pour arreter les outils, fermez les fenetres correspondantes.
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause > nul
goto :end

:error
echo.
echo Une erreur s'est produite lors du demarrage des outils.
echo Verifiez que tous les fichiers necessaires sont presents.
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause > nul

:end 