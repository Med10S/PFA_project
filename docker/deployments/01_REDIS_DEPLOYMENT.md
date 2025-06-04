# Redis Deployment Guide - GNS3 Topology

## Service Overview
Redis serves as the central message queue and data store for the IDS distributed system. All services communicate through Redis channels and store temporary data in Redis databases.

## Prerequisites
- Docker Engine installed and running
- GNS3 network `ids-network` created
- Subnet: `172.20.0.0/16`

## Configuration Files

### 1. Create Redis Configuration Directory
```powershell
mkdir "c:\ids-deployment\redis\config"
```

### 2. Redis Configuration File (`redis.conf`)
Create `c:\ids-deployment\redis\config\redis.conf`:

```conf
# Redis Configuration for IDS System
bind 0.0.0.0
port 6379
protected-mode yes
requirepass ${REDIS_PASSWORD}

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Logging
loglevel notice
logfile /var/log/redis/redis.log

# Client Management
timeout 300
tcp-keepalive 300
maxclients 1000

# Performance
tcp-backlog 511
databases 16
```

### 3. Environment File (`.env`)
Create `c:\ids-deployment\redis\.env`:

```env
# Redis Configuration
REDIS_PASSWORD=""
REDIS_PORT=6379
REDIS_HOST=172.20.0.10
REDIS_DATABASES=16
REDIS_MAX_MEMORY=512mb
REDIS_LOG_LEVEL=notice

# Persistence Settings
REDIS_SAVE_INTERVAL_1=900 1
REDIS_SAVE_INTERVAL_2=300 10
REDIS_SAVE_INTERVAL_3=60 10000
REDIS_APPENDONLY=yes
REDIS_APPENDFSYNC=everysec

# Security Settings
REDIS_PROTECTED_MODE=yes
REDIS_TIMEOUT=300
REDIS_TCP_KEEPALIVE=300
REDIS_MAX_CLIENTS=1000
```

## Docker Build

### 1. Navigate to Redis Service Directory
```powershell
cd "C:\Users\pc\personnel\etude_GTR2\S4\PFA\docker\services\redis"
```

### 2. Build Custom Redis Image
```powershell
docker build -t ids-redis:latest .
```

The custom Dockerfile includes:
- Security hardening with non-root user
- Comprehensive environment variable support
- Built-in health checks and monitoring scripts
- IDS-specific optimizations
- Dynamic configuration generation

## Container Deployment

### 1. Create Docker Network (if not exists)
```powershell
docker network create --driver bridge --subnet=172.20.0.0/16 --gateway=172.20.0.1 ids-network
```

### 2. Create Required Directories
```powershell
mkdir "c:\ids-deployment\redis\data"
mkdir "c:\ids-deployment\redis\logs"
```

### 3. Deploy Redis Container
```powershell
# Deploy with custom IDS-optimized image
docker run -d `
  --name ids-redis `
  --network ids-network `
  --ip 172.20.0.10 `
  -p 6379:6379 `
  -v "c:\ids-deployment\redis\data:/data" `
  -v "c:\ids-deployment\redis\logs:/var/log/redis" `
  -e REDIS_PASSWORD="SecureRedisPassword123!" `
  -e REDIS_MAXMEMORY="512mb" `
  -e REDIS_LOGLEVEL="notice" `
  -e REDIS_LOGFILE="/var/log/redis/redis.log" `
  --restart unless-stopped `
  ids-redis:latest
```

### Alternative: Production Deployment with Extended Configuration
```powershell
docker run -d `
  --name ids-redis `
  --network ids-network `
  --ip 172.20.0.10 `
  -p 6379:6379 `
  -v "c:\ids-deployment\redis\data:/data" `
  -v "c:\ids-deployment\redis\logs:/var/log/redis" `
  -e REDIS_PASSWORD="SecureRedisPassword123!" `
  -e REDIS_MAXMEMORY="1gb" `
  -e REDIS_MAXMEMORY_POLICY="allkeys-lru" `
  -e REDIS_DATABASES="16" `
  -e REDIS_SAVE_INTERVAL="900 1 300 10 60 10000" `
  -e REDIS_APPENDONLY="yes" `
  -e REDIS_APPENDFSYNC="everysec" `
  -e REDIS_LOGLEVEL="notice" `
  -e REDIS_LOGFILE="/var/log/redis/redis.log" `
  -e REDIS_TIMEOUT="300" `
  -e REDIS_TCP_KEEPALIVE="300" `
  -e REDIS_MAXCLIENTS="10000" `
  --restart unless-stopped `
  ids-redis:latest
```

## Container Management Commands

### Check Container Status
```powershell
docker ps -f name=ids-redis
```

### View Container Logs
```powershell
docker logs ids-redis
```

### Access Redis CLI
```powershell
# With password authentication
docker exec -it ids-redis redis-cli -a SecureRedisPassword123!
```

### Restart Container
```powershell
docker restart ids-redis
```

### Stop Container
```powershell
docker stop ids-redis
```

### Remove Container
```powershell
docker rm ids-redis
```

## Health Checks

### 1. Container Health (Built-in Health Check)
```powershell
# Use built-in health check script
docker exec ids-redis /usr/local/bin/redis-health-check.sh

# Traditional ping test
docker exec ids-redis redis-cli -a SecureRedisPassword123! ping
# Expected output: PONG
```

### 2. Network Connectivity Test
```powershell
# From another container in the same network
docker run --rm --network ids-network redis:7-alpine redis-cli -h 172.20.0.10 -a SecureRedisPassword123! ping
```

### 3. Memory Usage Check
```powershell
docker exec ids-redis redis-cli -a SecureRedisPassword123! info memory
```

### 4. Connection Count
```powershell
docker exec ids-redis redis-cli -a SecureRedisPassword123! info clients
```

### 5. Comprehensive Monitoring
```powershell
# Use built-in monitoring dashboard
docker exec ids-redis /usr/local/bin/redis-monitor.sh
```

## Configuration Validation

### Redis Configuration Test Script
Create `validate_redis.ps1`:

```powershell
# Redis Configuration Validation Script
Write-Host "Validating Redis Configuration..." -ForegroundColor Yellow

# Check if container is running
$containerStatus = docker ps -f name=ids-redis --format "{{.Status}}"
if ($containerStatus -like "*Up*") {
    Write-Host "✓ Redis container is running" -ForegroundColor Green
} else {
    Write-Host "✗ Redis container is not running" -ForegroundColor Red
    exit 1
}

# Test Redis connection using built-in health check
try {
    $healthCheck = docker exec ids-redis /usr/local/bin/redis-health-check.sh 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Redis health check passed" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis health check failed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Redis health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test traditional ping
try {
    $pingResult = docker exec ids-redis redis-cli -a SecureRedisPassword123! ping 2>$null
    if ($pingResult -eq "PONG") {
        Write-Host "✓ Redis ping successful" -ForegroundColor Green
    } else {
        Write-Host "✗ Redis ping failed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Redis ping failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Check Redis configuration
$config = docker exec ids-redis redis-cli -a SecureRedisPassword123! config get "*" 2>$null
if ($config) {
    Write-Host "✓ Redis configuration accessible" -ForegroundColor Green
} else {
    Write-Host "✗ Cannot access Redis configuration" -ForegroundColor Red
}

# Run comprehensive monitoring
Write-Host "Running comprehensive Redis monitoring..." -ForegroundColor Yellow
try {
    $monitorResult = docker exec ids-redis /usr/local/bin/redis-monitor.sh 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Redis monitoring dashboard accessible" -ForegroundColor Green
        Write-Host "Monitor output preview:" -ForegroundColor Cyan
        $monitorResult | Select-Object -First 10 | ForEach-Object { 
            Write-Host "  $_" -ForegroundColor White
        }
    } else {
        Write-Host "✗ Redis monitoring dashboard failed" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Redis monitoring failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Check IDS-specific message queues
Write-Host "Checking IDS message queues..." -ForegroundColor Yellow
$queues = @("alert_queue", "ml_predictions", "monitoring_data", "backup_requests")
foreach ($queue in $queues) {
    try {
        $queueLength = docker exec ids-redis redis-cli -a SecureRedisPassword123! llen $queue 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Queue '$queue': $queueLength items" -ForegroundColor Cyan
        } else {
            Write-Host "  Queue '$queue': Not initialized (normal for new deployment)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Queue '$queue': Error checking - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Redis validation completed." -ForegroundColor Yellow
```

Run validation:
```powershell
powershell.exe -ExecutionPolicy Bypass -File validate_redis.ps1
```

## Monitoring and Maintenance

### 1. Monitor Redis Logs
```powershell
docker logs -f ids-redis
```

### 2. Monitor Resource Usage
```powershell
docker stats ids-redis
```

### 3. Backup Redis Data
```powershell
# Create backup
docker exec ids-redis redis-cli -a SecureRedisPassword123! bgsave

# Copy backup file
docker cp ids-redis:/data/dump.rdb "c:\ids-deployment\redis\backups\dump_$(Get-Date -Format 'yyyyMMdd_HHmmss').rdb"
```

### 4. Restore Redis Data
```powershell
# Stop container
docker stop ids-redis

# Replace data file
copy "c:\ids-deployment\redis\backups\dump_backup.rdb" "c:\ids-deployment\redis\data\dump.rdb"

# Start container
docker start ids-redis
```

## Security Considerations

### 1. Password Security
- Use strong passwords (minimum 16 characters)
- Include uppercase, lowercase, numbers, and symbols
- Rotate passwords regularly

### 2. Network Security
- Bind to specific IP address (172.20.0.10)
- Use internal network communication only
- Disable dangerous commands (FLUSHDB, FLUSHALL, DEBUG)

### 3. Access Control
- Enable protected mode
- Set client timeout
- Limit maximum clients
- Monitor connection attempts

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```powershell
# Check Docker logs
docker logs ids-redis

# Common causes:
# - Port already in use
# - Invalid configuration file
# - Insufficient disk space
# - Permission issues
```

#### 2. Connection Refused
```powershell
# Check if Redis is listening
docker exec ids-redis netstat -tlnp | grep 6379

# Check Redis configuration
docker exec ids-redis redis-cli -a SecureRedisPassword123! config get bind
```

#### 3. Authentication Failed
```powershell
# Verify password in configuration
docker exec ids-redis redis-cli -a SecureRedisPassword123! config get requirepass

# Reset password if needed
docker exec ids-redis redis-cli -a SecureRedisPassword123! config set requirepass NewPassword123!
```

#### 4. High Memory Usage
```powershell
# Check memory usage
docker exec ids-redis redis-cli -a SecureRedisPassword123! info memory

# Check key count
docker exec ids-redis redis-cli -a SecureRedisPassword123! dbsize

# Clear specific keys if needed
docker exec ids-redis redis-cli -a SecureRedisPassword123! del key_pattern*
```

## Integration with Other Services

### Service Configuration
All other IDS services should use these Redis connection settings:
```env
REDIS_HOST=172.20.0.10
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisPassword123!
```

### Redis Channels Used by IDS System
- `packet_queue`: Raw packet data from capture service
- `feature_queue`: Extracted features from feature extractor
- `detection_queue`: ML detection results
- `alert_queue`: Generated alerts
- `monitoring_data`: System monitoring metrics
- `backup_requests`: Backup service requests

## Next Steps
After Redis deployment is complete and validated:
1. Deploy Monitoring Service
2. Verify Redis connectivity from monitoring service
3. Continue with remaining services in deployment order

## Support
- Redis Documentation: https://redis.io/documentation
- Docker Redis: https://hub.docker.com/_/redis
- Configuration Reference: https://redis.io/docs/management/config/
