@echo off
echo Lancement de l'Agent IA GBPBot...
cd %~dp0
call env\Scripts\activate.bat
python -m gbpbot.agent_example
pause 