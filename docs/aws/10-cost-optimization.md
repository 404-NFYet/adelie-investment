# AWS 비용 최적화 가이드

## 비용 확인

```bash
# 현재 비용 조회 (Cost Explorer API)
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-08 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --region ap-northeast-2

# 서비스별 비용
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-08 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --region ap-northeast-2
```

## Free Tier 활용

**AWS Free Tier (신규 계정 12개월):**
- **EC2**: t2.micro/t3.micro 750시간/월
- **RDS**: db.t2.micro/db.t3.micro 750시간/월
- **ECR**: 500MB 스토리지
- **ECS Fargate**: 20GB 스토리지
- **CloudWatch**: 10개 커스텀 메트릭, 5GB 로그 수집

```bash
# Free Tier 사용량 확인
aws ce get-cost-and-usage \
  --time-period Start=2026-02-01,End=2026-02-08 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://free-tier-filter.json \
  --region ap-northeast-2
```

## ECS Fargate 비용 최적화

```bash
# Task CPU/메모리 최적화 (필요한 만큼만 할당)
# Task Definition에서:
# - CPU: 256 (0.25 vCPU) - 최소 단위
# - Memory: 512MB - CPU의 2배 권장

# 사용하지 않는 Task 중지
aws ecs update-service \
  --cluster adelie-cluster \
  --service adelie-backend-api \
  --desired-count 0 \
  --region ap-northeast-2
```

## RDS 비용 최적화

```bash
# 개발 환경: db.t3.micro 사용
# 프로덕션: 필요에 따라 db.t3.small 이상

# 자동 백업 보관 기간 단축 (기본 7일)
aws rds modify-db-instance \
  --db-instance-identifier adelie-postgres \
  --backup-retention-period 3 \
  --region ap-northeast-2

# 스토리지 자동 스케일링 비활성화 (필요시)
aws rds modify-db-instance \
  --db-instance-identifier adelie-postgres \
  --max-allocated-storage 20 \
  --region ap-northeast-2
```

## ECR Lifecycle Policy로 스토리지 비용 절감

```bash
# 오래된 이미지 자동 삭제
aws ecr put-lifecycle-policy \
  --repository-name adelie-backend-api \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "30일 이상된 이미지 삭제",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {"type": "expire"}
    }]
  }' \
  --region ap-northeast-2
```

## CloudWatch Logs 보관 정책

```bash
# 로그 보관 기간 설정 (기본 무제한)
aws logs put-retention-policy \
  --log-group-name /ecs/adelie-backend-api \
  --retention-in-days 7 \
  --region ap-northeast-2

# 오래된 로그 삭제
aws logs delete-log-group --log-group-name /ecs/old-logs --region ap-northeast-2
```

## 비용 알람 설정

```bash
# 예산 알람 생성
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json \
  --region ap-northeast-2

# budget.json 예시:
# {
#   "BudgetName": "adelie-monthly-budget",
#   "BudgetLimit": {"Amount": "50", "Unit": "USD"},
#   "TimeUnit": "MONTHLY",
#   "BudgetType": "COST"
# }
```

## 리소스 태깅으로 비용 추적

```bash
# 리소스에 태그 추가 (환경별 비용 추적)
aws ecs tag-resource \
  --resource-arn <SERVICE_ARN> \
  --tags key=Environment,Value=production key=Project,Value=adelie \
  --region ap-northeast-2
```
