# AWS 인프라 트러블슈팅 가이드

## 자주 발생하는 문제

### 1. ECS Task가 시작되지 않음

```bash
# Task 상태 확인
aws ecs describe-tasks --cluster adelie-cluster --tasks <TASK_ARN> --region ap-northeast-2

# Task 중지 이유 확인
aws ecs describe-tasks --cluster adelie-cluster --tasks <TASK_ARN> \
  --query 'tasks[0].stoppedReason' --region ap-northeast-2

# CloudWatch Logs 확인
aws logs tail /ecs/adelie-backend-api --follow --region ap-northeast-2

# 일반적인 원인:
# - 이미지 pull 실패 (ECR 권한 문제)
# - 메모리 부족 (OOM)
# - 헬스 체크 실패
# - 보안 그룹 설정 문제
```

### 2. RDS 연결 불가

```bash
# RDS 상태 확인
aws rds describe-db-instances --db-instance-identifier adelie-postgres --region ap-northeast-2

# 보안 그룹 확인
aws rds describe-db-instances \
  --db-instance-identifier adelie-postgres \
  --query 'DBInstances[0].VpcSecurityGroups' \
  --region ap-northeast-2

# 보안 그룹에 ECS 보안 그룹 추가 필요
aws ec2 authorize-security-group-ingress \
  --group-id <RDS_SG_ID> \
  --protocol tcp \
  --port 5432 \
  --source-group <ECS_SG_ID> \
  --region ap-northeast-2
```

### 3. ALB 타겟이 unhealthy

```bash
# 타겟 그룹 상태 확인
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region ap-northeast-2

# 헬스 체크 설정 확인
aws elbv2 describe-target-groups \
  --target-group-arns <TARGET_GROUP_ARN> \
  --region ap-northeast-2

# 일반적인 원인:
# - 애플리케이션이 헬스 체크 경로를 제공하지 않음
# - 포트 불일치
# - 보안 그룹에서 트래픽 차단
```

### 4. ECR 이미지 push 실패

```bash
# ECR 로그인 확인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <ECR_REGISTRY>

# IAM 권한 확인
aws iam get-user-policy --user-name <USER_NAME> --policy-name <POLICY_NAME>

# 필요한 권한:
# - ecr:GetAuthorizationToken
# - ecr:BatchCheckLayerAvailability
# - ecr:GetDownloadUrlForLayer
# - ecr:BatchGetImage
# - ecr:PutImage
```

### 5. Terraform apply 실패

```bash
# 상태 파일 확인
terraform show

# 상태 파일 새로고침
terraform refresh

# 특정 리소스만 재생성
terraform taint aws_ecs_service.backend_api
terraform apply

# 상태 파일 백업
cp terraform.tfstate terraform.tfstate.backup

# 일반적인 원인:
# - 리소스 이름 중복
# - IAM 권한 부족
# - 리전 불일치
# - 의존성 문제
```

### 6. Secrets Manager 접근 불가

```bash
# Secret 존재 확인
aws secretsmanager describe-secret --secret-id adelie/database/credentials --region ap-northeast-2

# Task Role 권한 확인
aws iam get-role-policy --role-name adelie-ecs-task-role --policy-name SecretsManagerAccess

# 필요한 권한:
# - secretsmanager:GetSecretValue
# - secretsmanager:DescribeSecret
```

### 7. CloudWatch Logs가 보이지 않음

```bash
# 로그 그룹 존재 확인
aws logs describe-log-groups --log-group-name-prefix /ecs/ --region ap-northeast-2

# Task Definition에서 로그 설정 확인
aws ecs describe-task-definition --task-definition adelie-backend-api --region ap-northeast-2

# 로그 드라이버 설정 필요:
# "logConfiguration": {
#   "logDriver": "awslogs",
#   "options": {
#     "awslogs-group": "/ecs/adelie-backend-api",
#     "awslogs-region": "ap-northeast-2",
#     "awslogs-stream-prefix": "ecs"
#   }
# }
```

## 유용한 디버깅 명령어

```bash
# ECS Exec로 컨테이너 내부 접속
aws ecs execute-command \
  --cluster adelie-cluster \
  --task <TASK_ID> \
  --container backend-api \
  --command "/bin/sh" \
  --interactive \
  --region ap-northeast-2

# 네트워크 연결 테스트
aws ecs execute-command \
  --cluster adelie-cluster \
  --task <TASK_ID> \
  --container backend-api \
  --command "nc -zv <RDS_ENDPOINT> 5432" \
  --interactive \
  --region ap-northeast-2

# 환경 변수 확인
aws ecs describe-tasks --cluster adelie-cluster --tasks <TASK_ID> \
  --query 'tasks[0].containers[0].environment' --region ap-northeast-2
```

## 로그 수집

```bash
# 모든 로그 그룹에서 에러 검색
for log_group in $(aws logs describe-log-groups --query 'logGroups[].logGroupName' --output text --region ap-northeast-2); do
  echo "Checking $log_group"
  aws logs filter-log-events \
    --log-group-name $log_group \
    --filter-pattern "ERROR" \
    --start-time $(date -d '1 hour ago' +%s)000 \
    --region ap-northeast-2
done
```
