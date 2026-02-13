# Terraform Quickstart 가이드

## Terraform 설치

```bash
# Linux (Ubuntu/Debian)
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# 버전 확인
terraform version
```

## AWS CLI 설정

```bash
# AWS CLI 설치 (이미 설치되어 있다면 생략)
sudo apt install awscli

# 자격 증명 설정
aws configure
# AWS Access Key ID 입력
# AWS Secret Access Key 입력
# Default region name: ap-northeast-2 (서울)
# Default output format: json

# 설정 확인
aws sts get-caller-identity
```

## Terraform 초기화 및 실행

```bash
# 프로젝트 디렉토리로 이동
cd infra/terraform/environments/dev

# 초기화 (프로바이더 다운로드)
terraform init

# 실행 계획 확인 (변경사항 미리보기)
terraform plan

# 인프라 생성/업데이트
terraform apply

# 특정 리소스만 적용
terraform apply -target=module.ecr

# 인프라 삭제
terraform destroy
```

## 모듈별 설명

- **VPC 모듈**: 네트워크 구성 (VPC, 서브넷, IGW, NAT, 라우팅 테이블)
- **Bastion 모듈**: SSH 접속용 점프 서버
- **ECR 모듈**: 컨테이너 이미지 저장소 (frontend, backend-api, ai-pipeline)
- **RDS 모듈**: PostgreSQL + pgvector 데이터베이스
- **ElastiCache 모듈**: Redis 캐시 서버
- **S3 모듈**: 객체 스토리지 (MinIO 대체)
- **Secrets 모듈**: API 키 및 비밀 정보 관리 (Secrets Manager)
- **ECS 모듈**: Fargate 컨테이너 오케스트레이션 (클러스터, 서비스, 태스크 정의, ALB 포함)

## 유용한 명령어

```bash
# 상태 파일 확인
terraform show

# 출력값 확인
terraform output

# 포맷팅
terraform fmt

# 검증
terraform validate
```
