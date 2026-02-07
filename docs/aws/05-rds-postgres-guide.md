# RDS PostgreSQL 가이드

## RDS 인스턴스 확인

```bash
# RDS 인스턴스 목록
aws rds describe-db-instances --region ap-northeast-2

# 특정 인스턴스 상세 정보
aws rds describe-db-instances --db-instance-identifier adelie-postgres --region ap-northeast-2

# 엔드포인트 확인
aws rds describe-db-instances --db-instance-identifier adelie-postgres --query 'DBInstances[0].Endpoint.Address' --output text --region ap-northeast-2
```

## pgvector 확장 활성화

```bash
# psql로 데이터베이스 접속 (Bastion을 통한 접속 필요)
psql -h <RDS_ENDPOINT> -U postgres -d adelie_db

# pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

# 확장 확인
\dx vector

# 버전 확인
SELECT * FROM pg_available_extensions WHERE name = 'vector';
```

## 데이터베이스 백업 및 복원

```bash
# 수동 스냅샷 생성
aws rds create-db-snapshot \
  --db-instance-identifier adelie-postgres \
  --db-snapshot-identifier adelie-postgres-manual-$(date +%Y%m%d) \
  --region ap-northeast-2

# 스냅샷 목록
aws rds describe-db-snapshots --db-instance-identifier adelie-postgres --region ap-northeast-2

# 스냅샷에서 복원
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier adelie-postgres-restored \
  --db-snapshot-identifier adelie-postgres-manual-20260208 \
  --region ap-northeast-2
```

## 데이터 마이그레이션

```bash
# 로컬에서 덤프 생성
pg_dump -h localhost -U postgres -d adelie_db -F c -f backup.dump

# RDS로 복원
pg_restore -h <RDS_ENDPOINT> -U postgres -d adelie_db -v backup.dump

# SQL 파일로 마이그레이션
psql -h <RDS_ENDPOINT> -U postgres -d adelie_db -f migration.sql
```

## 연결 테스트

```bash
# psql로 직접 연결 테스트
psql -h <RDS_ENDPOINT> -U postgres -d adelie_db -c "SELECT version();"

# ECS Task에서 연결 테스트 (ECS Exec 사용)
aws ecs execute-command \
  --cluster adelie-cluster \
  --task <TASK_ID> \
  --container backend-api \
  --command "psql -h <RDS_ENDPOINT> -U postgres -d adelie_db -c 'SELECT 1;'" \
  --interactive \
  --region ap-northeast-2
```

## 성능 모니터링

```bash
# CloudWatch 메트릭 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=adelie-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region ap-northeast-2
```
