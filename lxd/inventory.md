# LXD 서버 인벤토리

## 인스턴스 현황 (2026-02-14 업데이트)

| 인스턴스 | IP | 역할 | 담당자 | CPU/RAM | 프로파일 |
|----------|-----|------|--------|---------|---------|
| infra-server | 10.10.10.10 | PostgreSQL, Redis, MinIO | 공유 | 8/24GB | `infra.yml` |
| deploy-test | 10.10.10.20 | prod 배포 서버 | 도형준 | 16/32GB | `deploy.yml` |
| dev-yj99son | 10.10.10.14 | PM / Frontend | 손영진 | 4/8GB | `dev-standard.yml` |
| dev-j2hoon10 | 10.10.10.11 | Chatbot (LangGraph 에이전트) | 정지훈 | 4/12GB | `dev-ai.yml` |
| dev-ryejinn | 10.10.10.13 | Data Pipeline (LangGraph 파이프라인) | 안례진 | 4/12GB | `dev-ai.yml` |
| dev-jjjh02 | 10.10.10.12 | Backend (FastAPI, DB) | 허진서 | 4/8GB | `dev-standard.yml` |
| dev-hj | 10.10.10.15 | Infra (Docker, CI/CD) | 도형준 | 4/8GB | `dev-standard.yml` |
| **합계** | - | - | - | **34/84GB** | - |

> 디스크: 전체 인스턴스가 **1개의 1.8TB NVMe**를 공유하는 구조.

## 스토리지 Quota

| 인스턴스 | Quota | 비고 |
|----------|-------|------|
| infra-server | 300GB | PostgreSQL, Redis, MinIO 데이터 |
| deploy-test | 200GB | Docker 이미지 + 컨테이너 |
| dev-* (각각) | 150GB | 소스코드, Docker, node_modules |
| 예비 | 550GB | 향후 확장용 |

## 역할 변경 이력 (2026-02-14)

- dev-ryejinn: `dev-qa.yml` (2/4GB) → `dev-ai.yml` (4/12GB) 승격 (Pipeline 담당 전환)
- deploy-test: RAM 64GB → 32GB 축소 (실사용 ~1.3GB 대비 과잉)

## 프로파일 적용 명령어

```bash
# dev-hj (인프라)
lxc config set dev-hj limits.cpu 4
lxc config set dev-hj limits.memory 8GB

# dev-j2hoon10 (Chatbot)
lxc config set dev-j2hoon10 limits.cpu 4
lxc config set dev-j2hoon10 limits.memory 12GB

# dev-jjjh02 (Backend)
lxc config set dev-jjjh02 limits.cpu 4
lxc config set dev-jjjh02 limits.memory 8GB

# dev-ryejinn (Pipeline) — 승격
lxc config set dev-ryejinn limits.cpu 4
lxc config set dev-ryejinn limits.memory 12GB

# dev-yj99son (Frontend)
lxc config set dev-yj99son limits.cpu 4
lxc config set dev-yj99son limits.memory 8GB

# deploy-test (prod 배포)
lxc config set deploy-test limits.memory 32GB

# 스토리지 quota (pool: default)
for inst in infra-server deploy-test dev-hj dev-j2hoon10 dev-jjjh02 dev-ryejinn dev-yj99son; do
  echo "$inst: $(lxc config device get $inst root size 2>/dev/null || echo 'unset')"
done
```

> 프로파일 적용 전 팀원 공지 필수. 실행 중인 작업 확인 후 적용.
