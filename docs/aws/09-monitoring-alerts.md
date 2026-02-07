# CloudWatch 모니터링 및 알람 가이드

## CloudWatch 메트릭 확인

```bash
# ECS CPU 사용률 확인
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=adelie-backend-api Name=ClusterName,Value=adelie-cluster \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region ap-northeast-2

# RDS CPU 사용률 확인
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

## CloudWatch Logs 확인

```bash
# 로그 그룹 목록
aws logs describe-log-groups --region ap-northeast-2

# 로그 스트림 목록
aws logs describe-log-streams \
  --log-group-name /ecs/adelie-backend-api \
  --region ap-northeast-2

# 로그 조회
aws logs tail /ecs/adelie-backend-api --follow --region ap-northeast-2

# 특정 시간대 로그 조회
aws logs filter-log-events \
  --log-group-name /ecs/adelie-backend-api \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --region ap-northeast-2
```

## 알람 생성

```bash
# ECS CPU 사용률 알람 생성
aws cloudwatch put-metric-alarm \
  --alarm-name adelie-ecs-high-cpu \
  --alarm-description "ECS CPU 사용률이 80% 초과 시 알람" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ServiceName,Value=adelie-backend-api Name=ClusterName,Value=adelie-cluster \
  --alarm-actions arn:aws:sns:ap-northeast-2:ACCOUNT_ID:adelie-alerts \
  --region ap-northeast-2

# RDS 연결 수 알람
aws cloudwatch put-metric-alarm \
  --alarm-name adelie-rds-high-connections \
  --alarm-description "RDS 연결 수가 80% 초과 시 알람" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=adelie-postgres \
  --alarm-actions arn:aws:sns:ap-northeast-2:ACCOUNT_ID:adelie-alerts \
  --region ap-northeast-2
```

## SNS 토픽 생성 및 구독

```bash
# SNS 토픽 생성
aws sns create-topic --name adelie-alerts --region ap-northeast-2

# 이메일 구독 추가
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:ACCOUNT_ID:adelie-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region ap-northeast-2

# 알람 목록 확인
aws cloudwatch describe-alarms --region ap-northeast-2

# 알람 상태 확인
aws cloudwatch describe-alarms --alarm-names adelie-ecs-high-cpu --region ap-northeast-2
```

## 대시보드 생성

```bash
# CloudWatch 대시보드 JSON 파일 생성 후 적용
aws cloudwatch put-dashboard \
  --dashboard-name adelie-monitoring \
  --dashboard-body file://dashboard.json \
  --region ap-northeast-2
```

## 주요 모니터링 메트릭

- **ECS**: CPUUtilization, MemoryUtilization, RunningTaskCount
- **RDS**: CPUUtilization, DatabaseConnections, FreeableMemory, ReadLatency, WriteLatency
- **ALB**: TargetResponseTime, HTTPCode_Target_5XX_Count, HealthyHostCount
- **Application**: Custom 메트릭 (애플리케이션에서 PutMetricData 사용)
