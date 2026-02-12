# LXD 서버 인벤토리

## 인스턴스 현황 (실측 2026-02-11)

| 인스턴스 | IP | 용도 | 현재 CPU/RAM | 실사용 메모리 | 권장 CPU/RAM | 프로파일 |
|----------|-----|------|-------------|-------------|-------------|---------|
| infra-server | 10.10.10.10 | PostgreSQL, Redis, Neo4j, MinIO | 8/24GB | ~1.2GB | **8/24GB** (유지) | `infra.yml` |
| deploy-test | 10.10.10.20 | 테스트 배포 서버 | 16/64GB | ~1.3GB | **16/32GB** | `deploy.yml` |
| dev-hj | - | 인프라 (Docker, CI/CD) | 8/28GB | ~228MB | **4/8GB** | `dev-standard.yml` |
| dev-j2hoon10 | - | AI 개발 (FastAPI, LangGraph) | 8/28GB | ~104MB | **4/12GB** | `dev-ai.yml` |
| dev-jjjh02 | - | 백엔드 (Spring Boot, 인증) | 8/28GB | ~104MB | **4/8GB** | `dev-standard.yml` |
| dev-ryejinn | - | AI QA (테스트, 프롬프트) | 8/28GB | ~104MB | **2/4GB** | `dev-qa.yml` |
| dev-yj99son | - | 프론트엔드 (React UI) | 8/28GB | ~104MB | **4/8GB** | `dev-standard.yml` |
| **합계** | - | - | **64/228GB** | **~3.2GB** | **42/96GB** | - |

> 디스크: 전체 인스턴스가 **1개의 1.8TB NVMe**를 공유하는 구조.

## 리소스 절감 효과

- CPU: 64 → 42 코어 (**34% 절감**)
- RAM: 228GB → 96GB (**58% 절감**)
- 실사용 대비 10배+ 여유 유지 (안전 마진 확보)

## 프로파일 적용 명령어

```bash
# dev-hj (인프라)
lxc config set dev-hj limits.cpu 4
lxc config set dev-hj limits.memory 8GB

# dev-j2hoon10 (AI)
lxc config set dev-j2hoon10 limits.cpu 4
lxc config set dev-j2hoon10 limits.memory 12GB

# dev-jjjh02 (백엔드)
lxc config set dev-jjjh02 limits.cpu 4
lxc config set dev-jjjh02 limits.memory 8GB

# dev-ryejinn (QA)
lxc config set dev-ryejinn limits.cpu 2
lxc config set dev-ryejinn limits.memory 4GB

# dev-yj99son (프론트)
lxc config set dev-yj99son limits.cpu 4
lxc config set dev-yj99son limits.memory 8GB

# deploy-test (배포)
lxc config set deploy-test limits.memory 32GB
```

> ⚠️ 프로파일 적용 전 팀원 공지 필수. 실행 중인 작업 확인 후 적용.
