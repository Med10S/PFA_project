# Script PowerShell pour démarrer le service de détection en temps réel
# start_detection_service.ps1

Write-Host "🚀 Démarrage du Service de Détection d'Intrusion Temps Réel" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green

# Vérification de Python
Write-Host "🔍 Vérification de Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python trouvé: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Python non trouvé. Veuillez installer Python 3.8+" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Erreur lors de la vérification de Python" -ForegroundColor Red
    exit 1
}

# Vérification du répertoire de travail
$currentDir = Get-Location
Write-Host "📁 Répertoire de travail: $currentDir" -ForegroundColor Cyan

# Vérification des fichiers requis
$requiredFiles = @(
    "realtime_detection_service.py",
    "config.py", 
    "/functions/model_loader.py",
    "/functions/preprocessing.py",
    "/functions/ensemble_models.py",
    "requirements.txt"
)

Write-Host "🔍 Vérification des fichiers requis..." -ForegroundColor Yellow
$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file manquant" -ForegroundColor Red
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ Fichiers manquants: $($missingFiles -join ', ')" -ForegroundColor Red
    exit 1
}

# Vérification des modèles
Write-Host "🤖 Vérification des modèles pré-entraînés..." -ForegroundColor Yellow
$modelFiles = @(
    "models/KNN_best.pkl",
    "models/mlp_best.pkl", 
    "models/xgb_best.pkl",
    "models/scaler.pkl",
    "models/label_encoders.pkl"
)

$missingModels = @()
foreach ($model in $modelFiles) {
    if (Test-Path $model) {
        Write-Host "✅ $model" -ForegroundColor Green
    } else {
        Write-Host "❌ $model manquant" -ForegroundColor Red
        $missingModels += $model
    }
}

if ($missingModels.Count -gt 0) {
    Write-Host "❌ Modèles manquants: $($missingModels -join ', ')" -ForegroundColor Red
    Write-Host "Assurez-vous d'avoir exécuté l'entraînement des modèles d'abord." -ForegroundColor Yellow
    exit 1
}

# Installation des dépendances
Write-Host "📦 Installation des dépendances..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dépendances installées avec succès" -ForegroundColor Green
    } else {
        Write-Host "❌ Erreur lors de l'installation des dépendances" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Erreur lors de l installation: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Vérification du port
$port = 8000
Write-Host "🔌 Vérification du port $port..." -ForegroundColor Yellow
try {
    $portTest = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($portTest) {
        Write-Host "⚠️  Le port $port est déjà utilisé" -ForegroundColor Yellow
        $response = Read-Host "Voulez-vous continuer quand même ? (o/N)"
        if ($response -ne "o" -and $response -ne "O") {
            Write-Host "❌ Démarrage annulé" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✅ Port $port disponible" -ForegroundColor Green
    }
} catch {
    Write-Host "✅ Port $port semble disponible" -ForegroundColor Green
}

# Démarrage du service
Write-Host "🚀 Démarrage du service FastAPI..." -ForegroundColor Green
Write-Host "Service sera disponible sur: http://localhost:$port" -ForegroundColor Cyan
Write-Host "Documentation API: http://localhost:$port/docs" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "Appuyez sur Ctrl+C pour arrêter le service" -ForegroundColor Yellow
Write-Host "=============================================================" -ForegroundColor Green

try {
    # Démarrage avec uvicorn
    uvicorn realtime_detection_service:app --host 0.0.0.0 --port $port --reload
} catch {
    Write-Host "❌ Erreur lors du démarrage: $($_.Exception.Message)" -ForegroundColor Red
    
    # Alternative avec python directement
    Write-Host "🔄 Tentative de démarrage alternatif..." -ForegroundColor Yellow
    try {
        python realtime_detection_service.py
    } catch {
        Write-Host "❌ Impossible de démarrer le service: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Service arrêté" -ForegroundColor Yellow
