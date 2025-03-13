#!/bin/bash
echo "Lancement de l'Agent IA GBPBot..."
cd "$(dirname "$0")"
source env/bin/activate
python -m gbpbot.agent_example 