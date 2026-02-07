# 개발 환경 설정 가이드

## 1. LXD 컨테이너 접속
```bash
# 본인 컨테이너에 SSH 접속
# dev-j2hoon10: 10.10.10.11, dev-jjjh02: .12, dev-ryejinn: .13, dev-yj99son: .14, dev-hj: .15
ssh ubuntu@10.10.10.{번호}
```

## 2. Docker 확인
```bash
docker --version   # Docker 29.2.1 이상
docker compose version
```

## 3. Docker Hub 로그인
```bash
echo "$DOCKER_PAT" | docker login -u dorae222 --password-stdin
```

## 4. 프로젝트 클론 및 설정
```bash
cd ~ && git clone https://github.com/404-NFYet/adelie-investment.git
cd adelie-investment
cp .env.example .env  # API 키 입력 (팀장에게 요청)
```

## 5. 개발 서버 실행
```bash
make dev              # 전체 (infra-server DB 연결)
make dev-frontend     # 프론트만
make dev-api          # FastAPI만
```

## 6. 접속 URL
- 프론트엔드: http://localhost:3001
- FastAPI Docs: http://localhost:8082/docs
- **데모 사이트**: https://demo.adelie-invest.com

## 7. 이미지 빌드/배포
```bash
make build TAG=v1.0   # Docker 이미지 빌드
make push TAG=v1.0    # Docker Hub 푸시
```

## 인프라 구조
- infra-server (10.10.10.10): PostgreSQL, Redis, Neo4j, MinIO
- deploy-test (10.10.10.20): 40인 데모 풀스택 + Cloudflare Tunnel
- 개발 컨테이너: Docker로 앱 서비스 실행, infra-server DB 공유
