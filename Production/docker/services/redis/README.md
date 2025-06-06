# Redis Service for IDS Distributed System

This directory contains the Redis server configuration for the IDS (Intrusion Detection System) distributed architecture. Redis serves as the central message broker and data cache for inter-service communication.

## Files

- `Dockerfile` - Complete Redis container build with security hardening
- `redis.conf` - Redis configuration template
- `README.md` - This documentation file

## Purpose

Redis serves multiple critical functions in the IDS system:

1. **Message Queue**: Inter-service communication between ML-API, Alert Manager, Monitoring, etc.
2. **Session Storage**: Temporary storage for monitoring sessions and analysis data
3. **Cache Layer**: ML model predictions and frequent query results
4. **Alert Aggregation**: Deduplication and correlation of security alerts
5. **Backup Coordination**: Queue management for backup operations

## Environment Variables

The Dockerfile supports extensive configuration through environment variables:

### Connection Settings
- `REDIS_PORT` (default: 6379) - Redis server port
- `REDIS_BIND` (default: 0.0.0.0) - Bind address
- `REDIS_PASSWORD` (default: "") - Authentication password

### Memory Management
- `REDIS_MAXMEMORY` (default: 256mb) - Maximum memory usage
- `REDIS_MAXMEMORY_POLICY` (default: allkeys-lru) - Eviction policy
- `REDIS_DATABASES` (default: 16) - Number of databases

### Persistence
- `REDIS_SAVE_INTERVAL` (default: "900 1 300 10 60 10000") - Save intervals
- `REDIS_APPENDONLY` (default: yes) - Enable AOF persistence
- `REDIS_APPENDFSYNC` (default: everysec) - AOF sync frequency

### Security
- `REDIS_PROTECTED_MODE` (default: yes) - Enable protected mode
- `REDIS_USER` (default: redis) - Non-root user
- `REDIS_GROUP` (default: redis) - User group

### Network
- `REDIS_TIMEOUT` (default: 300) - Client timeout
- `REDIS_TCP_KEEPALIVE` (default: 300) - TCP keepalive
- `REDIS_TCP_BACKLOG` (default: 511) - TCP backlog
- `REDIS_MAXCLIENTS` (default: 10000) - Maximum clients

### Logging
- `REDIS_LOGLEVEL` (default: notice) - Log level
- `REDIS_LOGFILE` (default: "") - Log file path

## Building the Container

```bash
# Build Redis container
docker build -t ids-redis:latest .

# Build with custom tag
docker build -t ids-redis:v1.0 .
```

## Running the Container

### Basic Usage
```bash
# Run with default settings
docker run -d --name ids-redis \
  --network ids-network \
  --ip 172.20.0.10 \
  -p 6379:6379 \
  ids-redis:latest

# Run with password protection
docker run -d --name ids-redis \
  --network ids-network \
  --ip 172.20.0.10 \
  -p 6379:6379 \
  -e REDIS_PASSWORD="your_secure_password" \
  ids-redis:latest
```

### GNS3 Deployment
```bash
# For GNS3 topology with fixed IP
docker run -d --name ids-redis \
  --network ids-network \
  --ip 172.20.0.10 \
  -p 6379:6379 \
  -e REDIS_MAXMEMORY="512mb" \
  -e REDIS_PASSWORD="ids_secure_2024" \
  -v redis-data:/data \
  -v redis-logs:/var/log/redis \
  ids-redis:latest
```

### Production Deployment
```bash
# Production with persistence and monitoring
docker run -d --name ids-redis \
  --network ids-network \
  --ip 172.20.0.10 \
  -p 6379:6379 \
  -e REDIS_PASSWORD="your_production_password" \
  -e REDIS_MAXMEMORY="1gb" \
  -e REDIS_LOGLEVEL="warning" \
  -e REDIS_LOGFILE="/var/log/redis/redis.log" \
  -v /host/redis/data:/data \
  -v /host/redis/logs:/var/log/redis \
  --restart unless-stopped \
  ids-redis:latest
```

## Health Checks

The container includes built-in health check scripts:

```bash
# Check Redis health
docker exec ids-redis /usr/local/bin/redis-health-check.sh

# Monitor Redis performance
docker exec ids-redis /usr/local/bin/redis-monitor.sh
```

## Management Commands

```bash
# Connect to Redis CLI
docker exec -it ids-redis redis-cli

# Connect with password
docker exec -it ids-redis redis-cli -a "your_password"

# View Redis logs
docker logs ids-redis

# Monitor real-time logs
docker logs -f ids-redis

# Check container resource usage
docker stats ids-redis
```

## IDS-Specific Usage

### Message Queues
The Redis instance manages several message queues for the IDS system:

- `alert_queue` - Security alerts from detection services
- `ml_predictions` - ML model predictions and results
- `monitoring_data` - System monitoring metrics
- `backup_requests` - Backup operation requests
- `packet_analysis` - Packet capture analysis results

### Key Patterns
- `session:*` - Monitoring session data
- `cache:ml:*` - ML model prediction cache
- `alert:*` - Alert correlation data
- `stats:*` - System statistics
- `config:*` - Dynamic configuration

## Security Considerations

1. **Authentication**: Always set `REDIS_PASSWORD` in production
2. **Network Security**: Use Docker networks to isolate Redis
3. **Command Restrictions**: Dangerous commands are disabled by default
4. **User Security**: Container runs as non-root `redis` user
5. **File Permissions**: Proper file ownership and permissions

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if container is running
   docker ps | grep ids-redis
   
   # Check logs for errors
   docker logs ids-redis
   ```

2. **Memory Issues**
   ```bash
   # Check memory usage
   docker exec ids-redis redis-cli info memory
   
   # Increase memory limit
   docker run ... -e REDIS_MAXMEMORY="1gb" ...
   ```

3. **Permission Errors**
   ```bash
   # Check data directory permissions
   docker exec ids-redis ls -la /data
   
   # Fix permissions if needed
   docker exec ids-redis chown -R redis:redis /data
   ```

### Performance Monitoring

```bash
# Monitor Redis performance metrics
docker exec ids-redis redis-cli info stats

# Check slow queries
docker exec ids-redis redis-cli slowlog get 10

# Monitor client connections
docker exec ids-redis redis-cli client list
```

## Integration with Other Services

Redis integrates with all IDS services:

1. **ML-API Service** (172.20.0.30) - Stores predictions and results
2. **Alert Manager** (172.20.0.40) - Queues and correlates alerts
3. **Monitoring Service** (172.20.0.20) - Caches metrics and sessions
4. **Backup Service** (172.20.0.50) - Coordinates backup operations
5. **Feature Extractor** (172.20.0.60) - Stores extracted features
6. **Packet Capture** (172.20.0.70) - Queues packet analysis

## Backup and Recovery

```bash
# Create data backup
docker exec ids-redis redis-cli BGSAVE

# Copy backup file
docker cp ids-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb

# Restore from backup
docker cp ./redis-backup.rdb ids-redis:/data/dump.rdb
docker restart ids-redis
```

## Version Information

- **Redis Version**: 7.2-alpine
- **Container User**: redis (UID: 999)
- **Default Port**: 6379
- **Data Directory**: /data
- **Log Directory**: /var/log/redis