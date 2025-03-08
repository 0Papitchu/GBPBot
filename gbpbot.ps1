#!/usr/bin/env pwsh
# ----------------------------------------------------------------
# GBPBot - Script de lancement principal
# ----------------------------------------------------------------
# Ce script permet de lancer facilement le GBPBot avec différentes options
# Il sert de point d'entrée unique pour toutes les fonctionnalités du bot

param (
    [string]$mode = "",
    [switch]$arbitrage = $false,
    [switch]$sniper = $false,
    [switch]$auto = $false,
    [switch]$config = $false,
    [switch]$stats = $false,
    [switch]$verify = $false,
    [switch]$update = $false,
    [switch]$help = $false
)

# Fonction pour afficher l'aide
function Show-Help {
    Write-Host @"
GBPBot - Script de lancement principal
----------------------------------------

UTILISATION:
    ./gbpbot.ps1 [OPTIONS]

OPTIONS:
    -mode <nom>        Mode de lancement (arbitrage, sniper, auto)
    -arbitrage         Lancer directement le mode arbitrage
    -sniper            Lancer directement le mode sniper de tokens
    -auto              Lancer en mode automatique (arbitrage et sniper)
    -config            Modifier la configuration du bot
    -stats             Afficher les statistiques et logs
    -verify            Vérifier le code (lint, format, tests)
    -update            Mettre à jour les dépendances
    -help              Afficher cette aide

EXEMPLES:
    ./gbpbot.ps1                       # Lancer le menu principal
    ./gbpbot.ps1 -mode arbitrage       # Lancer le mode arbitrage
    ./gbpbot.ps1 -sniper               # Lancer le mode sniper
    ./gbpbot.ps1 -verify               # Vérifier le code
    ./gbpbot.ps1 -config               # Modifier la configuration

REMARQUE:
    Exécutez ce script depuis le répertoire racine du projet GBPBot.
"@
    exit 0
}

# Vérifier le répertoire d'exécution
if (-not (Test-Path "gbpbot" -PathType Container)) {
    Write-Host "Erreur: Ce script doit être exécuté depuis le répertoire racine du projet GBPBot." -ForegroundColor Red
    exit 1
}

# Vérifier si Python est installé
try {
    $pythonVersion = python --version
    Write-Host "Python détecté: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Erreur: Python n'est pas installé ou n'est pas accessible. Veuillez installer Python 3.8 ou supérieur." -ForegroundColor Red
    exit 1
}

# Vérifier l'existence de l'environnement virtuel ou le créer
$venvPath = "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Environnement virtuel non trouvé. Création en cours..." -ForegroundColor Yellow
    python -m venv $venvPath
    
    if (-not $?) {
        Write-Host "Erreur lors de la création de l'environnement virtuel." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Environnement virtuel créé avec succès!" -ForegroundColor Green
}

# Fonction pour activer l'environnement virtuel
function Activate-Venv {
    if ($IsWindows) {
        & "$venvPath\Scripts\Activate.ps1"
    }
    else {
        . "$venvPath/bin/Activate.ps1"
    }
    
    if (-not $?) {
        Write-Host "Erreur lors de l'activation de l'environnement virtuel." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Environnement virtuel activé!" -ForegroundColor Green
}

# Fonction pour installer ou mettre à jour les dépendances
function Update-Dependencies {
    Write-Host "Installation/Mise à jour des dépendances..." -ForegroundColor Cyan
    
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt --upgrade
        
        if (-not $?) {
            Write-Host "Erreur lors de l'installation des dépendances." -ForegroundColor Red
            return $false
        }
        
        Write-Host "Dépendances installées/mises à jour avec succès!" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "Erreur: Fichier requirements.txt non trouvé." -ForegroundColor Red
        return $false
    }
}

# Fonction pour lancer le bot dans un mode spécifique
function Start-Bot {
    param (
        [string]$runMode
    )
    
    Write-Host "Lancement du GBPBot en mode: $runMode" -ForegroundColor Cyan
    
    if ($runMode -eq "arbitrage") {
        python run_gbpbot.py --mode arbitrage
    }
    elseif ($runMode -eq "sniper") {
        python run_gbpbot.py --mode sniper
    }
    elseif ($runMode -eq "auto") {
        python run_gbpbot.py --mode auto
    }
    else {
        python run_gbpbot.py
    }
    
    if (-not $?) {
        Write-Host "Erreur lors du lancement du GBPBot." -ForegroundColor Red
        return $false
    }
    
    return $true
}

# Fonction pour configurer le bot
function Configure-Bot {
    Write-Host "Configuration du GBPBot..." -ForegroundColor Cyan
    
    # Vérifier si le fichier .env existe, sinon le créer à partir de .env.example
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Host "Fichier de configuration .env créé à partir du modèle .env.example" -ForegroundColor Green
        }
        else {
            Write-Host "Avertissement: Modèle .env.example non trouvé. Création d'un fichier .env vide." -ForegroundColor Yellow
            New-Item -Path ".env" -ItemType File
        }
    }
    
    # Ouvrir le fichier .env dans l'éditeur par défaut
    if ($IsWindows) {
        Start-Process notepad ".env"
    }
    else {
        # Tenter d'utiliser des éditeurs de texte courants sur Linux/macOS
        $editors = @("nano", "vim", "vi", "gedit", "code")
        $editorFound = $false
        
        foreach ($editor in $editors) {
            try {
                $null = Get-Command $editor -ErrorAction SilentlyContinue
                Start-Process $editor ".env"
                $editorFound = $true
                break
            }
            catch {
                continue
            }
        }
        
        if (-not $editorFound) {
            Write-Host "Aucun éditeur de texte trouvé. Veuillez modifier manuellement le fichier .env" -ForegroundColor Yellow
        }
    }
    
    Write-Host "N'oubliez pas de sauvegarder vos modifications avant de quitter l'éditeur!" -ForegroundColor Yellow
}

# Fonction pour afficher les statistiques et logs
function Show-Stats {
    Write-Host "Affichage des statistiques et logs du GBPBot..." -ForegroundColor Cyan
    
    # Chercher et afficher les derniers fichiers de log
    $logFiles = Get-ChildItem -Path "logs" -Filter "*.log" | Sort-Object LastWriteTime -Descending
    
    if ($logFiles.Count -eq 0) {
        Write-Host "Aucun fichier de log trouvé." -ForegroundColor Yellow
        return
    }
    
    Write-Host "Derniers fichiers de log:" -ForegroundColor Cyan
    $counter = 1
    
    foreach ($log in $logFiles | Select-Object -First 5) {
        $size = "{0:N2} KB" -f ($log.Length / 1KB)
        $lastWrite = $log.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host "$counter. $($log.Name) - $size - $lastWrite"
        $counter++
    }
    
    $choice = Read-Host "Entrez le numéro du fichier de log à afficher (ou 'q' pour quitter)"
    
    if ($choice -eq 'q') {
        return
    }
    
    try {
        $selectedLog = $logFiles[$choice - 1]
        
        # Afficher les 50 dernières lignes du fichier de log
        Write-Host "`nAffichage des 50 dernières lignes de $($selectedLog.Name):" -ForegroundColor Cyan
        Get-Content $selectedLog.FullName -Tail 50
    }
    catch {
        Write-Host "Erreur: Fichier de log non trouvé ou choix invalide." -ForegroundColor Red
    }
}

# Fonction pour vérifier le code
function Verify-Code {
    Write-Host "Lancement de la vérification du code..." -ForegroundColor Cyan
    
    if (Test-Path "tools\verify_code.ps1") {
        & "tools\verify_code.ps1" -all
    }
    else {
        Write-Host "Erreur: Script de vérification du code non trouvé." -ForegroundColor Red
    }
}

# Traitement des arguments
if ($help) {
    Show-Help
}

# Activer l'environnement virtuel
Activate-Venv

# Mettre à jour les dépendances si demandé
if ($update) {
    Update-Dependencies
}

# Vérifier le code si demandé
if ($verify) {
    Verify-Code
}

# Configuration si demandée
if ($config) {
    Configure-Bot
}

# Afficher les statistiques si demandé
if ($stats) {
    Show-Stats
}

# Lancer le bot dans le mode spécifié
if ($arbitrage -or $mode -eq "arbitrage") {
    Start-Bot -runMode "arbitrage"
}
elseif ($sniper -or $mode -eq "sniper") {
    Start-Bot -runMode "sniper"
}
elseif ($auto -or $mode -eq "auto") {
    Start-Bot -runMode "auto"
}
elseif ($mode -ne "") {
    Start-Bot -runMode $mode
}
elseif (-not ($config -or $stats -or $verify -or $update)) {
    # Si aucune option spécifique n'est fournie, lancer le menu principal
    Start-Bot -runMode ""
}

Write-Host "Opération terminée!" -ForegroundColor Green 