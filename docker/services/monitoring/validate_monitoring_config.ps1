# Script de validation des variables d'environnement pour le service de monitoring
# Auteur: Assistant IA
# Date: $(Get-Date)

param(
    [switch]$Verbose,
    [string]$EnvFile = ".env"
)

Write-Host "=== Validation de la configuration du service de monitoring ===" -ForegroundColor Green

# Configuration par défaut
$DefaultConfig = @{
    # Logging
    "LOG_LEVEL" = "INFO"
    "LOG_FILE" = "monitoring.log"
    "LOG_FORMAT" = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Redis
    "REDIS_HOST" = "redis"
    "REDIS_PORT" = "6379"
    "REDIS_DB" = "0"
    
    # Flask
    "FLASK_HOST" = "0.0.0.0"
    "FLASK_PORT" = "9000"
    "FLASK_DEBUG" = "false"
    
    # Monitoring
    "MONITORING_INTERVAL" = "30"
    "HISTORY_LIMIT" = "1000"
    "DASHBOARD_REFRESH" = "30"
    
    # Seuils d'alerte
    "CPU_ALERT_THRESHOLD" = "90"
    "MEMORY_ALERT_THRESHOLD" = "90"
    "DISK_ALERT_THRESHOLD" = "90"
    
    # Services
    "SERVICE_CHECK_INTERVAL" = "30"
    "SERVICE_TIMEOUT" = "5"
}

# Services configurables
$Services = @("PACKET_CAPTURE", "FEATURE_EXTRACTOR", "ML_API", "ALERT_MANAGER", "BACKUP_SERVICE")

# Fonction pour charger le fichier .env
function Load-EnvFile {
    param([string]$FilePath)
    
    $envVars = @{}
    if (Test-Path $FilePath) {
        Get-Content $FilePath | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)$") {
                $envVars[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
        Write-Host "✓ Fichier .env chargé: $FilePath" -ForegroundColor Green
    } else {
        Write-Host "⚠ Fichier .env non trouvé: $FilePath" -ForegroundColor Yellow
        Write-Host "  Utilisation des variables d'environnement système et valeurs par défaut" -ForegroundColor Yellow
    }
    return $envVars
}

# Fonction pour obtenir une valeur de configuration
function Get-ConfigValue {
    param(
        [string]$Key,
        [hashtable]$EnvVars,
        [hashtable]$DefaultConfig
    )
    
    # Priorité: Variable d'environnement système > Fichier .env > Valeur par défaut
    $value = [Environment]::GetEnvironmentVariable($Key)
    if (-not $value -and $EnvVars.ContainsKey($Key)) {
        $value = $EnvVars[$Key]
    }
    if (-not $value -and $DefaultConfig.ContainsKey($Key)) {
        $value = $DefaultConfig[$Key]
    }
    
    return $value
}

# Fonction de validation des valeurs numériques
function Test-NumericValue {
    param(
        [string]$Value,
        [int]$Min = 0,
        [int]$Max = [int]::MaxValue
    )
    
    try {
        $numValue = [int]$Value
        return ($numValue -ge $Min -and $numValue -le $Max)
    } catch {
        return $false
    }
}

# Fonction de validation des niveaux de log
function Test-LogLevel {
    param([string]$Level)
    
    $validLevels = @("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    return $validLevels -contains $Level.ToUpper()
}

# Fonction de validation des valeurs booléennes
function Test-BooleanValue {
    param([string]$Value)
    
    $validValues = @("true", "false", "1", "0", "yes", "no")
    return $validValues -contains $Value.ToLower()
}

# Chargement du fichier .env
$envVars = Load-EnvFile -FilePath $EnvFile

Write-Host "`n--- Validation de la configuration principale ---" -ForegroundColor Cyan

$errors = @()
$warnings = @()

# Validation du logging
$logLevel = Get-ConfigValue -Key "LOG_LEVEL" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-LogLevel $logLevel)) {
    $errors += "LOG_LEVEL invalide: $logLevel (doit être DEBUG, INFO, WARNING, ERROR, ou CRITICAL)"
} else {
    Write-Host "✓ LOG_LEVEL: $logLevel" -ForegroundColor Green
}

# Validation Redis
$redisPort = Get-ConfigValue -Key "REDIS_PORT" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $redisPort -Min 1 -Max 65535)) {
    $errors += "REDIS_PORT invalide: $redisPort (doit être entre 1 et 65535)"
} else {
    Write-Host "✓ REDIS_PORT: $redisPort" -ForegroundColor Green
}

$redisDb = Get-ConfigValue -Key "REDIS_DB" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $redisDb -Min 0 -Max 15)) {
    $errors += "REDIS_DB invalide: $redisDb (doit être entre 0 et 15)"
} else {
    Write-Host "✓ REDIS_DB: $redisDb" -ForegroundColor Green
}

# Validation Flask
$flaskPort = Get-ConfigValue -Key "FLASK_PORT" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $flaskPort -Min 1 -Max 65535)) {
    $errors += "FLASK_PORT invalide: $flaskPort (doit être entre 1 et 65535)"
} else {
    Write-Host "✓ FLASK_PORT: $flaskPort" -ForegroundColor Green
}

$flaskDebug = Get-ConfigValue -Key "FLASK_DEBUG" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-BooleanValue $flaskDebug)) {
    $warnings += "FLASK_DEBUG format non standard: $flaskDebug (recommandé: true/false)"
} else {
    Write-Host "✓ FLASK_DEBUG: $flaskDebug" -ForegroundColor Green
}

# Validation des intervalles
$monitoringInterval = Get-ConfigValue -Key "MONITORING_INTERVAL" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $monitoringInterval -Min 5 -Max 3600)) {
    $errors += "MONITORING_INTERVAL invalide: $monitoringInterval (doit être entre 5 et 3600 secondes)"
} else {
    Write-Host "✓ MONITORING_INTERVAL: $monitoringInterval secondes" -ForegroundColor Green
}

$dashboardRefresh = Get-ConfigValue -Key "DASHBOARD_REFRESH" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $dashboardRefresh -Min 5 -Max 3600)) {
    $errors += "DASHBOARD_REFRESH invalide: $dashboardRefresh (doit être entre 5 et 3600 secondes)"
} else {
    Write-Host "✓ DASHBOARD_REFRESH: $dashboardRefresh secondes" -ForegroundColor Green
}

# Validation des seuils d'alerte
$cpuThreshold = Get-ConfigValue -Key "CPU_ALERT_THRESHOLD" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $cpuThreshold -Min 1 -Max 100)) {
    $errors += "CPU_ALERT_THRESHOLD invalide: $cpuThreshold (doit être entre 1 et 100)"
} else {
    Write-Host "✓ CPU_ALERT_THRESHOLD: $cpuThreshold%" -ForegroundColor Green
}

$memoryThreshold = Get-ConfigValue -Key "MEMORY_ALERT_THRESHOLD" -EnvVars $envVars -DefaultConfig $DefaultConfig
if (-not (Test-NumericValue $memoryThreshold -Min 1 -Max 100)) {
    $errors += "MEMORY_ALERT_THRESHOLD invalide: $memoryThreshold (doit être entre 1 et 100)"
} else {
    Write-Host "✓ MEMORY_ALERT_THRESHOLD: $memoryThreshold%" -ForegroundColor Green
}

# Validation des services
Write-Host "`n--- Validation de la configuration des services ---" -ForegroundColor Cyan

foreach ($service in $Services) {
    $host = Get-ConfigValue -Key "${service}_HOST" -EnvVars $envVars -DefaultConfig @{}
    $port = Get-ConfigValue -Key "${service}_PORT" -EnvVars $envVars -DefaultConfig @{}
    $enabled = Get-ConfigValue -Key "${service}_ENABLED" -EnvVars $envVars -DefaultConfig @{}
    
    if ($host) {
        Write-Host "✓ ${service}_HOST: $host" -ForegroundColor Green
    }
    
    if ($port -and (Test-NumericValue $port -Min 1 -Max 65535)) {
        Write-Host "✓ ${service}_PORT: $port" -ForegroundColor Green
    } elseif ($port) {
        $errors += "${service}_PORT invalide: $port"
    }
    
    if ($enabled -and (Test-BooleanValue $enabled)) {
        Write-Host "✓ ${service}_ENABLED: $enabled" -ForegroundColor Green
    } elseif ($enabled) {
        $warnings += "${service}_ENABLED format non standard: $enabled"
    }
}

# Test de connectivité Redis (si possible)
Write-Host "`n--- Test de connectivité ---" -ForegroundColor Cyan

$redisHost = Get-ConfigValue -Key "REDIS_HOST" -EnvVars $envVars -DefaultConfig $DefaultConfig
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.ConnectAsync($redisHost, $redisPort).Wait(3000)
    if ($tcpClient.Connected) {
        Write-Host "✓ Connexion Redis réussie ($redisHost:$redisPort)" -ForegroundColor Green
        $tcpClient.Close()
    } else {
        $warnings += "Impossible de se connecter à Redis ($redisHost:$redisPort)"
    }
} catch {
    $warnings += "Impossible de tester la connexion Redis: $($_.Exception.Message)"
}

# Résumé
Write-Host "`n=== RÉSUMÉ DE LA VALIDATION ===" -ForegroundColor Yellow

if ($errors.Count -eq 0) {
    Write-Host "✓ Configuration valide!" -ForegroundColor Green
} else {
    Write-Host "✗ Erreurs détectées:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

if ($warnings.Count -gt 0) {
    Write-Host "⚠ Avertissements:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "  - $warning" -ForegroundColor Yellow
    }
}

# Affichage des recommandations
Write-Host "`n--- Recommandations ---" -ForegroundColor Cyan
Write-Host "1. Utilisez un fichier .env pour centraliser la configuration" -ForegroundColor White
Write-Host "2. En production, définissez CPU_ALERT_THRESHOLD >= 95" -ForegroundColor White
Write-Host "3. Configurez MONITORING_INTERVAL selon vos besoins (plus court = plus de surveillance)" -ForegroundColor White
Write-Host "4. Assurez-vous que tous les services cibles sont accessibles" -ForegroundColor White

if ($Verbose) {
    Write-Host "`n--- Configuration complète ---" -ForegroundColor Cyan
    foreach ($key in $DefaultConfig.Keys | Sort-Object) {
        $value = Get-ConfigValue -Key $key -EnvVars $envVars -DefaultConfig $DefaultConfig
        Write-Host "$key = $value" -ForegroundColor Gray
    }
}

# Code de sortie
if ($errors.Count -gt 0) {
    exit 1
} else {
    exit 0
}
