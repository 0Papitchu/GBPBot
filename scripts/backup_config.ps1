# ============================================================
# Script de sauvegarde automatique des configurations GBPBot
# ============================================================
#
# Ce script crée des sauvegardes horodatées des fichiers de configuration
# critiques du GBPBot, incluant les fichiers d'environnement, les configurations
# YAML et les fichiers de wallets.
#
# Fonctionnalités:
# - Sauvegarde des fichiers .env et .env.local
# - Sauvegarde des configurations YAML dans le dossier config/
# - Sauvegarde des wallets et autres fichiers sensibles
# - Stockage des sauvegardes dans un dossier dédié avec horodatage
# - Conservation des 10 dernières sauvegardes uniquement
#
# Utilisation: .\backup_config.ps1 [destination]
# Si aucune destination n'est spécifiée, les sauvegardes sont stockées
# dans le dossier "config_backups" à la racine du projet.

# Paramètres
param (
    [string]$BackupDestination = ""
)

# Fonction pour afficher des messages colorés
function Write-ColorOutput {
    param (
        [string]$Message,
        [string]$Color = "White"
    )
    
    Write-Host $Message -ForegroundColor $Color
}

# Fonction pour créer un dossier s'il n'existe pas
function Ensure-Directory {
    param (
        [string]$Path
    )
    
    if (-not (Test-Path -Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-ColorOutput "Dossier créé: $Path" "Yellow"
    }
}

# Obtenir le chemin racine du projet
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootPath = Split-Path -Parent $scriptPath

# Définir le dossier de destination des sauvegardes
if ([string]::IsNullOrEmpty($BackupDestination)) {
    $backupRoot = Join-Path -Path $rootPath -ChildPath "config_backups"
} else {
    $backupRoot = $BackupDestination
}

# Créer le dossier de sauvegarde s'il n'existe pas
Ensure-Directory -Path $backupRoot

# Créer un horodatage pour le nom du dossier de sauvegarde
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path -Path $backupRoot -ChildPath "backup_$timestamp"
$tempBackupDir = Join-Path -Path $backupRoot -ChildPath "temp_backup_$timestamp"

# Créer le dossier temporaire de sauvegarde
Ensure-Directory -Path $tempBackupDir

# Afficher l'en-tête
Write-ColorOutput "`n============================================================" "Cyan"
Write-ColorOutput "  SAUVEGARDE DES CONFIGURATIONS GBPBOT" "Cyan"
Write-ColorOutput "============================================================`n" "Cyan"
Write-ColorOutput "Date et heure: $(Get-Date)" "White"
Write-ColorOutput "Dossier de sauvegarde: $backupDir`n" "White"

# Définir les fichiers et dossiers à sauvegarder
$configItems = @(
    # Fichiers d'environnement
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath ".env"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath ".env"
        "Type" = "File"
        "Description" = "Fichier d'environnement principal"
    },
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath ".env.local"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath ".env.local"
        "Type" = "File"
        "Description" = "Fichier d'environnement local"
    },
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath ".env.optimized"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath ".env.optimized"
        "Type" = "File"
        "Description" = "Fichier d'environnement optimisé"
    },
    
    # Dossier de configuration
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath "config"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath "config"
        "Type" = "Directory"
        "Description" = "Dossier de configuration"
    },
    
    # Dossier des wallets
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath "wallets"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath "wallets"
        "Type" = "Directory"
        "Description" = "Dossier des wallets"
    },
    
    # Autres fichiers de configuration importants
    @{
        "Source" = Join-Path -Path $rootPath -ChildPath "gbpbot/config"
        "Destination" = Join-Path -Path $tempBackupDir -ChildPath "gbpbot_config"
        "Type" = "Directory"
        "Description" = "Configuration interne GBPBot"
    }
)

# Compteurs pour les statistiques
$totalItems = 0
$successItems = 0
$skippedItems = 0

# Sauvegarder chaque élément
Write-ColorOutput "Sauvegarde des fichiers de configuration..." "White"
foreach ($item in $configItems) {
    $source = $item.Source
    $destination = $item.Destination
    $type = $item.Type
    $description = $item.Description
    
    # Vérifier si la source existe
    if (Test-Path -Path $source) {
        $totalItems++
        
        try {
            # Copier le fichier ou le dossier
            if ($type -eq "File") {
                Copy-Item -Path $source -Destination $destination -Force
                $successItems++
                Write-ColorOutput "✓ $description sauvegardé" "Green"
            } elseif ($type -eq "Directory") {
                Copy-Item -Path $source -Destination $destination -Recurse -Force
                $successItems++
                Write-ColorOutput "✓ $description sauvegardé" "Green"
            }
        } catch {
            Write-ColorOutput "✗ Erreur lors de la sauvegarde de $description : $_" "Red"
        }
    } else {
        $skippedItems++
        Write-ColorOutput "! $description non trouvé, ignoré" "Yellow"
    }
}

# Créer une archive ZIP de la sauvegarde
Write-ColorOutput "`nCréation de l'archive de sauvegarde..." "White"
try {
    Compress-Archive -Path "$tempBackupDir\*" -DestinationPath "$backupDir.zip" -Force
    Write-ColorOutput "✓ Archive créée: $backupDir.zip" "Green"
    
    # Supprimer le dossier temporaire
    Remove-Item -Path $tempBackupDir -Recurse -Force
    Write-ColorOutput "✓ Dossier temporaire supprimé" "Green"
} catch {
    Write-ColorOutput "✗ Erreur lors de la création de l'archive: $_" "Red"
}

# Nettoyer les anciennes sauvegardes (conserver uniquement les 10 plus récentes)
Write-ColorOutput "`nNettoyage des anciennes sauvegardes..." "White"
try {
    $backups = Get-ChildItem -Path $backupRoot -Filter "backup_*.zip" | Sort-Object -Property LastWriteTime -Descending
    
    if ($backups.Count -gt 10) {
        $toDelete = $backups | Select-Object -Skip 10
        
        foreach ($backup in $toDelete) {
            Remove-Item -Path $backup.FullName -Force
            Write-ColorOutput "✓ Ancienne sauvegarde supprimée: $($backup.Name)" "Yellow"
        }
        
        Write-ColorOutput "✓ Conservation des 10 sauvegardes les plus récentes" "Green"
    } else {
        Write-ColorOutput "✓ Moins de 10 sauvegardes existantes, aucune suppression nécessaire" "Green"
    }
} catch {
    Write-ColorOutput "✗ Erreur lors du nettoyage des anciennes sauvegardes: $_" "Red"
}

# Afficher le résumé
Write-ColorOutput "`n============================================================" "Cyan"
Write-ColorOutput "  RÉSUMÉ DE LA SAUVEGARDE" "Cyan"
Write-ColorOutput "============================================================" "Cyan"
Write-ColorOutput "Éléments traités: $totalItems" "White"
Write-ColorOutput "Éléments sauvegardés: $successItems" "Green"
Write-ColorOutput "Éléments ignorés: $skippedItems" "Yellow"
Write-ColorOutput "Sauvegarde stockée dans: $backupDir.zip" "White"
Write-ColorOutput "============================================================`n" "Cyan"

# Vérifier si la sauvegarde a réussi
if ($successItems -gt 0) {
    Write-ColorOutput "Sauvegarde terminée avec succès!" "Green"
    exit 0
} else {
    Write-ColorOutput "Échec de la sauvegarde: aucun élément sauvegardé." "Red"
    exit 1
} 