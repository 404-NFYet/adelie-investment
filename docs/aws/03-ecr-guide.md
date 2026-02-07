# ECR 리포지토리 관리 가이드

## ECR 리포지토리 확인

```bash
# 리포지토리 목록 조회
aws ecr describe-repositories --region ap-northeast-2

# 특정 리포지토리 정보
aws ecr describe-repositories --repository-names adelie-backend-api --region ap-northeast-2
```

## Docker 로그인

```bash
# ECR 로그인 토큰 획득 및 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com

# 또는 Terraform output 사용
ECR_REGISTRY=$(terraform -chdir=infra/terraform output -raw ecr_registry)
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ECR_REGISTRY
```

## 이미지 빌드 및 푸시

```bash
# 이미지 빌드
cd backend_api
docker build -t backend-api:latest .

# ECR 태깅
docker tag backend-api:latest <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/adelie-backend-api:latest
docker tag backend-api:latest <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/adelie-backend-api:v1.0.0

# 이미지 푸시
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/adelie-backend-api:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/adelie-backend-api:v1.0.0

# 모든 태그 푸시
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/adelie-backend-api --all-tags
```

## 이미지 관리

```bash
# 이미지 목록 조회
aws ecr list-images --repository-name adelie-backend-api --region ap-northeast-2

# 이미지 태그 조회
aws ecr describe-images --repository-name adelie-backend-api --region ap-northeast-2

# 이미지 삭제
aws ecr batch-delete-image --repository-name adelie-backend-api --image-ids imageTag=old-tag --region ap-northeast-2
```

## Lifecycle Policy 설정

```bash
# lifecycle-policy.json 생성 후 적용
aws ecr put-lifecycle-policy \
  --repository-name adelie-backend-api \
  --lifecycle-policy-text file://lifecycle-policy.json \
  --region ap-northeast-2

# 정책 확인
aws ecr get-lifecycle-policy --repository-name adelie-backend-api --region ap-northeast-2
```

**lifecycle-policy.json 예시:**
```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "최근 10개 이미지만 유지",
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 10
    },
    "action": {
      "type": "expire"
    }
  }]
}
```
