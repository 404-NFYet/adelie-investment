# 배포 가이드

## deploy-test (LXD 로컬 데모)

### 서비스 시작

```bash
# deploy-test 접속
ssh deploy-test

# 프로젝트 클론 (최초 1회)
cd ~ && git clone ... && cd adelie-investment

# Docker 이미지 pull + 실행
REGISTRY=dorae222 TAG=latest docker compose -f docker-compose.prod.yml up -d

# 상태 확인
docker compose -f docker-compose.prod.yml ps
```

### 데이터 초기화 (최초 배포 또는 데이터 리셋 시)

```bash
# 1. 시장 데이터 수집 (키워드 + 종목)
docker exec adelie-backend-api python /app/scripts/seed_fresh_data.py

# 2. 역사적 사례 생성 (LLM 기반, OPENAI_API_KEY 필요)
docker exec -e OPENAI_API_KEY="$OPENAI_API_KEY" adelie-backend-api python /app/generate_cases.py

# 데이터 확인
docker exec adelie-postgres psql -U adelie -d adelie -c "SELECT COUNT(*) FROM historical_cases;"
```

### Cloudflare Tunnel 설정

```bash
bash infra/setup-cloudflare-tunnel.sh
# -> https://demo.adelie-invest.com 접속 가능
```

### 장애 대응

```bash
# 로그 확인
docker compose -f docker-compose.prod.yml logs backend-api -f

# 서비스 재시작
docker compose -f docker-compose.prod.yml restart backend-api

# 전체 재시작
docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d
```

## AWS 배포 (Terraform)

```bash
cd infra/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars  # 실제 값 입력
terraform init
terraform plan
terraform apply
```

상세 가이드: docs/aws/ 디렉토리 참조
