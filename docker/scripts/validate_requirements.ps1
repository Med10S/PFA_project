# Script de validation des requirements par service
# Teste l'installation de chaque fichier requirements.txt

param(
    [string]$Service = "all"
)

$services = @(
    "ml-api",
    "alerts", 
    "capture",
    "extractor",
    "monitoring",
    "backup"
)

function Test-Requirements {
    param(
        [string]$ServiceName
    )
    
    Write-Host "🔍 Test des requirements pour $ServiceName..." -ForegroundColor Cyan
    
    $requirementsPath = "docker/services/$ServiceName/requirements.txt"
    
    if (-not (Test-Path $requirementsPath)) {
        Write-Host "❌ Fichier requirements.txt introuvable: $requirementsPath" -ForegroundColor Red
        return $false
    }
    
    try {
        # Création d'un environnement virtuel temporaire
        $venvPath = "temp_venv_$ServiceName"
        python -m venv $venvPath
        
        # Activation de l'environnement virtuel
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            & "$venvPath\Scripts\Activate.ps1"
        } else {
            & "$venvPath/bin/activate"
        }
        
        # Installation des requirements
        Write-Host "📦 Installation des dépendances pour $ServiceName..."
        pip install --quiet -r $requirementsPath
        
        # Vérification des conflits
        $conflicts = pip check 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  Conflits détectés pour $ServiceName :" -ForegroundColor Yellow
            Write-Host $conflicts -ForegroundColor Yellow
        } else {
            Write-Host "✅ Requirements OK pour $ServiceName" -ForegroundColor Green
        }
        
        # Nettoyage
        deactivate 2>$null
        Remove-Item -Recurse -Force $venvPath
        
        return $true
    }
    catch {
        Write-Host "❌ Erreur lors du test de $ServiceName : $_" -ForegroundColor Red
        
        # Nettoyage en cas d'erreur
        deactivate 2>$null
        if (Test-Path $venvPath) {
            Remove-Item -Recurse -Force $venvPath
        }
        
        return $false
    }
}

function Test-DockerBuild {
    param(
        [string]$ServiceName
    )
    
    Write-Host "🐳 Test de build Docker pour $ServiceName..." -ForegroundColor Cyan
    
    try {
        $dockerfilePath = "docker/services/$ServiceName/Dockerfile"
        $imageName = "ids-$ServiceName-test"
        
        # Build de l'image
        docker build -f $dockerfilePath -t $imageName . --quiet
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Build Docker OK pour $ServiceName" -ForegroundColor Green
            
            # Nettoyage de l'image test
            docker rmi $imageName --force 2>$null
            return $true
        } else {
            Write-Host "❌ Échec du build Docker pour $ServiceName" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Erreur Docker pour $ServiceName : $_" -ForegroundColor Red
        return $false
    }
}

# Fonction principale
Write-Host "🚀 Validation des Requirements par Service" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

if ($Service -eq "all") {
    $servicesToTest = $services
} else {
    $servicesToTest = @($Service)
}

$results = @{}

foreach ($service in $servicesToTest) {
    Write-Host "`n--- Testing $service ---" -ForegroundColor Blue
    
    # Test des requirements Python
    $reqResult = Test-Requirements -ServiceName $service
    
    # Test du build Docker
    $dockerResult = Test-DockerBuild -ServiceName $service
    
    $results[$service] = @{
        "Requirements" = $reqResult
        "Docker" = $dockerResult
    }
}

# Rapport final
Write-Host "`n📊 RAPPORT FINAL" -ForegroundColor Green
Write-Host "=================" -ForegroundColor Green

foreach ($service in $servicesToTest) {
    $req = if ($results[$service]["Requirements"]) { "✅" } else { "❌" }
    $docker = if ($results[$service]["Docker"]) { "✅" } else { "❌" }
    
    Write-Host "$service : Requirements $req | Docker $docker"
}

# Commandes utiles
Write-Host "`n🔧 COMMANDES UTILES:" -ForegroundColor Yellow
Write-Host "Build individuel: docker build -f docker/services/[service]/Dockerfile -t ids-[service] ."
Write-Host "Build tous: docker-compose build"
Write-Host "Test service: .\validate_requirements.ps1 -Service [service-name]"

Write-Host "`nValidation terminée!" -ForegroundColor Green
