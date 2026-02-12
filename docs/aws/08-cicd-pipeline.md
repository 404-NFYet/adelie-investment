# CI/CD Pipeline 가이드 (GitHub Actions)

## GitHub Actions 워크플로우 구조

```yaml
# .github/workflows/deploy.yml 예시
name: Deploy to ECS

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-northeast-2
      
      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: adelie-backend-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -f fastapi/Dockerfile -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: adelie-backend-api
          cluster: adelie-cluster
          wait-for-service-stability: true
```

## GitHub Secrets 설정

```bash
# GitHub 저장소에서 Settings > Secrets and variables > Actions로 이동
# 다음 Secrets 추가:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - ECR_REGISTRY (선택사항)
```

## ECR 빌드 및 푸시

```bash
# 로컬에서 수동 빌드 및 푸시
ECR_REGISTRY=$(terraform -chdir=infra/terraform/environments/dev output -raw ecr_registry)
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ECR_REGISTRY

docker build -f fastapi/Dockerfile -t $ECR_REGISTRY/adelie-backend-api:latest .
docker push $ECR_REGISTRY/adelie-backend-api:latest
```

## ECS 배포

```bash
# Task Definition 업데이트 후 서비스 업데이트
aws ecs update-service \
  --cluster adelie-cluster \
  --service adelie-backend-api \
  --task-definition adelie-backend-api:NEW_VERSION \
  --force-new-deployment \
  --region ap-northeast-2

# 배포 상태 확인
aws ecs describe-services \
  --cluster adelie-cluster \
  --services adelie-backend-api \
  --query 'services[0].deployments' \
  --region ap-northeast-2
```

## 롤백

```bash
# 이전 Task Definition으로 롤백
PREVIOUS_TASK_DEF=$(aws ecs describe-services \
  --cluster adelie-cluster \
  --services adelie-backend-api \
  --query 'services[0].deployments[?status==`PRIMARY`].taskDefinition' \
  --output text \
  --region ap-northeast-2)

aws ecs update-service \
  --cluster adelie-cluster \
  --service adelie-backend-api \
  --task-definition $PREVIOUS_TASK_DEF \
  --region ap-northeast-2
```

## 배포 전략

- **롤링 업데이트**: 기본값, 무중단 배포
- **Blue/Green 배포**: ALB 타겟 그룹 전환 사용
- **Canary 배포**: 트래픽 일부만 새 버전으로 라우팅
