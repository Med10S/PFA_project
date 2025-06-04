# Script de build optimisé pour tous les services Docker
# Construit les images avec cache et parallélisation

param(
    [string]$Action = "build",
    [string]$Service = "all",
    [switch]$NoCache,
    [switch]$Parallel
)

$services = @(
    @{ Name = "ml-api"; Port = 5000; Priority = 1 },
    @{ Name = "alerts"; Port = 9003; Priority = 2 },
    @{ Name = "capture"; Port = 9001; Priority = 3 },
    @{ Name = "extractor"; Port = 9002; Priority = 3 },
    @{ Name = "monitoring"; Port = 9000; Priority = 4 },
    @{ Name = "backup"; Port = 9004; Priority = 5 }
)

function Build-Service {
    param(
        [hashtable]$ServiceInfo,
        [bool]$UseCache = $true
    )
    
    $serviceName = $ServiceInfo.Name
    $port = $ServiceInfo.Port
    
    Write-Host "🔨 Construction de $serviceName..." -ForegroundColor Cyan
    
    $dockerfilePath = "docker/services/$serviceName/Dockerfile"
    $imageName = "ids-$serviceName"
    $buildArgs = @()
    
    if (-not $UseCache) {
        $buildArgs += "--no-cache"
    }
    
    try {
        $startTime = Get-Date
        
        # Commande de build
        $buildCmd = "docker build -f $dockerfilePath -t $imageName $($buildArgs -join ' ') ."
        
        Write-Host "   Commande: $buildCmd" -ForegroundColor Gray
        Invoke-Expression $buildCmd
        
        $duration = (Get-Date) - $startTime
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $serviceName construit avec succès ($($duration.TotalSeconds.ToString('F1'))s)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Échec de construction pour $serviceName" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Erreur lors de la construction de $serviceName : $_" -ForegroundColor Red
        return $false
    }
}

function Test-Service {
    param(
        [hashtable]$ServiceInfo
    )
    
    $serviceName = $ServiceInfo.Name
    $port = $ServiceInfo.Port
    $imageName = "ids-$serviceName"
    
    Write-Host "🧪 Test de $serviceName..." -ForegroundColor Yellow
    
    try {
        # Test de démarrage du conteneur
        $containerName = "test-$serviceName-$(Get-Random)"
        
        docker run -d --name $containerName $imageName
        
        Start-Sleep -Seconds 5
        
        # Vérification que le conteneur fonctionne
        $status = docker ps --filter "name=$containerName" --format "{{.Status}}"
        
        if ($status -like "Up*") {
            Write-Host "✅ $serviceName fonctionne correctement" -ForegroundColor Green
            $result = $true
        } else {
            Write-Host "❌ $serviceName ne démarre pas correctement" -ForegroundColor Red
            # Affichage des logs pour diagnostic
            Write-Host "Logs de $serviceName :" -ForegroundColor Yellow
            docker logs $containerName
            $result = $false
        }
        
        # Nettoyage
        docker stop $containerName 2>$null
        docker rm $containerName 2>$null
        
        return $result
    }
    catch {
        Write-Host "❌ Erreur lors du test de $serviceName : $_" -ForegroundColor Red
        docker stop $containerName 2>$null
        docker rm $containerName 2>$null
        return $false
    }
}

function Show-ImageSizes {
    Write-Host "`n📊 TAILLES DES IMAGES:" -ForegroundColor Green
    Write-Host "======================" -ForegroundColor Green
    
    foreach ($service in $services) {
        $imageName = "ids-$($service.Name)"
        $size = docker images $imageName --format "{{.Size}}" 2>$null
        
        if ($size) {
            Write-Host "$($service.Name.PadRight(12)) : $size" -ForegroundColor Cyan
        } else {
            Write-Host "$($service.Name.PadRight(12)) : Non construite" -ForegroundColor Red
        }
    }
}

function Clean-Images {
    Write-Host "🧹 Nettoyage des images..." -ForegroundColor Yellow
    
    foreach ($service in $services) {
        $imageName = "ids-$($service.Name)"
        docker rmi $imageName --force 2>$null
    }
    
    # Nettoyage des images orphelines
    docker image prune -f
    
    Write-Host "✅ Nettoyage terminé" -ForegroundColor Green
}

# Fonction principale
Write-Host "🐳 CONSTRUCTION DES SERVICES DOCKER" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

$useCache = -not $NoCache

switch ($Action.ToLower()) {
    "build" {
        if ($Service -eq "all") {
            $servicesToBuild = $services | Sort-Object Priority
        } else {
            $servicesToBuild = $services | Where-Object { $_.Name -eq $Service }
            if (-not $servicesToBuild) {
                Write-Host "❌ Service '$Service' non trouvé" -ForegroundColor Red
                exit 1
            }
        }
        
        $results = @{}
        $totalStartTime = Get-Date
        
        if ($Parallel -and $Service -eq "all") {
            Write-Host "🔄 Construction en parallèle..." -ForegroundColor Cyan
            
            # Construction en parallèle par groupes de priorité
            $priorityGroups = $servicesToBuild | Group-Object Priority | Sort-Object Name
            
            foreach ($group in $priorityGroups) {
                Write-Host "`n--- Groupe de priorité $($group.Name) ---" -ForegroundColor Blue
                
                $jobs = @()
                foreach ($service in $group.Group) {
                    $job = Start-Job -ScriptBlock {
                        param($serviceInfo, $useCache)
                        # Import des fonctions nécessaires dans le job
                        # ... (code simplifié pour l'exemple)
                        return Build-Service -ServiceInfo $serviceInfo -UseCache $useCache
                    } -ArgumentList $service, $useCache
                    
                    $jobs += $job
                }
                
                # Attendre que tous les jobs du groupe se terminent
                $jobs | Wait-Job | Receive-Job
                $jobs | Remove-Job
            }
        } else {
            Write-Host "🔄 Construction séquentielle..." -ForegroundColor Cyan
            
            foreach ($service in $servicesToBuild) {
                $result = Build-Service -ServiceInfo $service -UseCache $useCache
                $results[$service.Name] = $result
            }
        }
        
        $totalDuration = (Get-Date) - $totalStartTime
        
        # Rapport
        Write-Host "`n📊 RAPPORT DE CONSTRUCTION" -ForegroundColor Green
        Write-Host "===========================" -ForegroundColor Green
        
        foreach ($service in $servicesToBuild) {
            $status = if ($results[$service.Name]) { "✅ OK" } else { "❌ ÉCHEC" }
            Write-Host "$($service.Name.PadRight(12)) : $status"
        }
        
        Write-Host "`nTemps total: $($totalDuration.TotalMinutes.ToString('F1')) minutes" -ForegroundColor Cyan
        
        Show-ImageSizes
    }
    
    "test" {
        if ($Service -eq "all") {
            $servicesToTest = $services
        } else {
            $servicesToTest = $services | Where-Object { $_.Name -eq $Service }
        }
        
        foreach ($service in $servicesToTest) {
            Test-Service -ServiceInfo $service
        }
    }
    
    "clean" {
        Clean-Images
    }
    
    "size" {
        Show-ImageSizes
    }
    
    default {
        Write-Host "Actions disponibles: build, test, clean, size" -ForegroundColor Yellow
        Write-Host "Usage: .\build_services.ps1 -Action build -Service ml-api" -ForegroundColor Yellow
        Write-Host "       .\build_services.ps1 -Action build -Service all -NoCache" -ForegroundColor Yellow
        Write-Host "       .\build_services.ps1 -Action test" -ForegroundColor Yellow
    }
}

Write-Host "`n🎉 Opération terminée!" -ForegroundColor Green
