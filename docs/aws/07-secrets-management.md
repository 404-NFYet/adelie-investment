# Secrets Manager 가이드

## Secret 생성

```bash
# JSON 형식으로 Secret 생성
aws secretsmanager create-secret \
  --name adelie/database/credentials \
  --description "RDS PostgreSQL credentials" \
  --secret-string '{"username":"postgres","password":"your-password"}' \
  --region ap-northeast-2

# 파일에서 Secret 생성
aws secretsmanager create-secret \
  --name adelie/api-keys \
  --secret-string file://secrets.json \
  --region ap-northeast-2
```

## Secret 조회

```bash
# Secret 목록
aws secretsmanager list-secrets --region ap-northeast-2

# Secret 값 조회 (JSON)
aws secretsmanager get-secret-value \
  --secret-id adelie/database/credentials \
  --region ap-northeast-2 \
  --query SecretString --output text | jq .

# 특정 키 값만 조회
aws secretsmanager get-secret-value \
  --secret-id adelie/database/credentials \
  --region ap-northeast-2 \
  --query SecretString --output text | jq -r .password
```

## Secret 업데이트

```bash
# Secret 값 업데이트
aws secretsmanager update-secret \
  --secret-id adelie/database/credentials \
  --secret-string '{"username":"postgres","password":"new-password"}' \
  --region ap-northeast-2

# 버전별 관리 (자동 버전 생성)
aws secretsmanager put-secret-value \
  --secret-id adelie/database/credentials \
  --secret-string '{"username":"postgres","password":"updated-password"}' \
  --region ap-northeast-2
```

## ECS Task Definition 연동

**Task Definition에서 secrets 사용:**
```json
{
  "containerDefinitions": [{
    "name": "backend-api",
    "secrets": [
      {
        "name": "DB_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:ACCOUNT_ID:secret:adelie/database/credentials:password::"
      },
      {
        "name": "API_KEY",
        "valueFrom": "arn:aws:secretsmanager:ap-northeast-2:ACCOUNT_ID:secret:adelie/api-keys:API_KEY::"
      }
    ]
  }]
}
```

## IAM 권한 설정

ECS Task Role에 다음 권한 추가:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ],
    "Resource": [
      "arn:aws:secretsmanager:ap-northeast-2:ACCOUNT_ID:secret:adelie/*"
    ]
  }]
}
```

## 애플리케이션에서 사용

```python
# Python 예시 (boto3)
import boto3
import json

secrets_client = boto3.client('secretsmanager', region_name='ap-northeast-2')
secret = secrets_client.get_secret_value(SecretId='adelie/database/credentials')
credentials = json.loads(secret['SecretString'])

db_password = credentials['password']
```

## Secret 삭제

```bash
# Secret 삭제 (복구 가능 기간: 7-30일)
aws secretsmanager delete-secret \
  --secret-id adelie/database/credentials \
  --region ap-northeast-2

# 즉시 삭제 (복구 불가)
aws secretsmanager delete-secret \
  --secret-id adelie/database/credentials \
  --force-delete-without-recovery \
  --region ap-northeast-2
```
