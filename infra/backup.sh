#!/bin/bash
# Narrative Investment - Database Backup Script
# cron 등록 예시: 0 3 * * * /path/to/infra/backup.sh
# 매일 새벽 3시 자동 백업

set -e

BACKUP_DIR="/backup/narrative-investment"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Backup started"

# PostgreSQL 백업
echo "  [1/2] Backing up PostgreSQL..."
docker exec narrative-postgres pg_dump \
    -U narative \
    -d narrative_invest \
    --format=custom \
    --compress=9 \
    > "${BACKUP_DIR}/postgres_${DATE}.dump" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "  [OK] PostgreSQL backup: postgres_${DATE}.dump"
else
    echo "  [ERROR] PostgreSQL backup failed"
fi

# Neo4j 백업 (Community Edition - 데이터 디렉토리 복사)
echo "  [2/2] Backing up Neo4j data..."
NEO4J_VOLUME=$(docker volume inspect narrative-investment_neo4j_data --format '{{.Mountpoint}}' 2>/dev/null || echo "")
if [ -n "$NEO4J_VOLUME" ] && [ -d "$NEO4J_VOLUME" ]; then
    tar -czf "${BACKUP_DIR}/neo4j_${DATE}.tar.gz" -C "$NEO4J_VOLUME" . 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  [OK] Neo4j backup: neo4j_${DATE}.tar.gz"
    else
        echo "  [ERROR] Neo4j backup failed"
    fi
else
    echo "  [SKIP] Neo4j volume not found"
fi

# 오래된 백업 정리
echo "  Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null

echo "[$(date)] Backup completed"
echo "  Location: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -5
