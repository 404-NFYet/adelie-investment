# ECS Fargate 가이드

## 클러스터 확인

```bash
# 클러스터 목록
aws ecs list-clusters --region ap-northeast-2

# 클러스터 상세 정보
aws ecs describe-clusters --clusters adelie-cluster --region ap-northeast-2
```

## Task Definition 관리

```bash
# Task Definition 목록
aws ecs list-task-definitions --region ap-northeast-2

# Task Definition 상세 정보
aws ecs describe-task-definition --task-definition adelie-backend-api --region ap-northeast-2

# 새 버전 등록 (Terraform으로 관리하는 경우 생략)
aws ecs register-task-definition --cli-input-json file://task-definition.json --region ap-northeast-2
```

## Service 관리

```bash
# 서비스 목록
aws ecs list-services --cluster adelie-cluster --region ap-northeast-2

# 서비스 상세 정보
aws ecs describe-services --cluster adelie-cluster --services adelie-backend-api --region ap-northeast-2

# 서비스 업데이트 (새 Task Definition으로 배포)
aws ecs update-service \
  --cluster adelie-cluster \
  --service adelie-backend-api \
  --task-definition adelie-backend-api:NEW_VERSION \
  --region ap-northeast-2

# 서비스 강제 새 배포 (롤링 업데이트)
aws ecs update-service \
  --cluster adelie-cluster \
  --service adelie-backend-api \
  --force-new-deployment \
  --region ap-northeast-2
```

## Task 관리

```bash
# 실행 중인 Task 목록
aws ecs list-tasks --cluster adelie-cluster --service-name adelie-backend-api --region ap-northeast-2

# Task 상세 정보
aws ecs describe-tasks --cluster adelie-cluster --tasks <TASK_ARN> --region ap-northeast-2

# Task 로그 확인 (CloudWatch Logs)
aws logs tail /ecs/adelie-backend-api --follow --region ap-northeast-2
```

## ALB 연동 확인

```bash
# 타겟 그룹 상태 확인
aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN> --region ap-northeast-2

# ALB 리스너 확인
aws elbv2 describe-listeners --load-balancer-arn <ALB_ARN> --region ap-northeast-2
```

## 배포 프로세스

1. **이미지 빌드 및 푸시**: ECR에 새 이미지 업로드
2. **Task Definition 업데이트**: 새 이미지 태그로 업데이트
3. **Service 업데이트**: 새 Task Definition으로 서비스 업데이트
4. **헬스 체크 확인**: ALB 타겟 그룹에서 헬스 체크 상태 모니터링
