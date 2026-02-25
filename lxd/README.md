# LXD 인프라 구성

## 개요

LXD 기반 개발 환경: dev 서버 5대 + 인프라 서버 2대 운영.

- **dev-*** (5대): 팀원별 개인 개발 환경 (각각 로컬 postgres 운영)
- **infra-server**: 모니터링 에이전트 (cadvisor, node_exporter)
- **deploy-test**: 프로덕션 배포 서버

서버 목록 및 스펙: [inventory.md](./inventory.md)

## 주요 Makefile 타겟

`make -f lxd/Makefile <타겟>` 으로 실행.

| 타겟 | 설명 |
|------|------|
| `sync-lxd` | LXD 전체 서버: git pull + Docker 이미지 pull + build + up -d |
| `sync-dev-data` | deploy-test → LXD dev 서버 DB 콘텐츠 동기화 (13개 테이블) |
| `sync-dev-branches` | prod-final → dev-final/* 브랜치 동기화 |
| `dev-local-db-setup` | 개인 로컬 DB 초기 세팅 (기동 + 마이그레이션 + prod 데이터 복제) |
| `health-lxd` | 전체 LXD 서버 헬스체크 |
| `fix-lxd-jwt` | JWT_SECRET 기본값 → openssl rand -hex 32 갱신 |
| `check-lxd-git` | 전체 LXD 서버 git 상태 점검 |

## 디렉토리 구조

```
lxd/
├── Makefile          # 자동화 타겟
├── inventory.md      # 서버 인벤토리 (IP, 스펙, 역할)
├── profiles/         # LXD 프로파일 정의 (infra.yml, deploy.yml, dev-*.yml)
├── scripts/          # 서버 프로비저닝 및 관리 스크립트
└── archive/          # 아카이브
```

## 개발 환경 세팅

```bash
# 1. 로컬 DB 초기화 (최초 1회)
make -f lxd/Makefile dev-local-db-setup

# 2. 코드 + 이미지 동기화
make -f lxd/Makefile sync-lxd

# 3. prod 데이터 최신화 (필요 시)
make -f lxd/Makefile sync-dev-data
```

## git 설정

각 LXD 서버에 담당자의 git 계정이 설정되어 있음. `check-lxd-git`으로 확인 가능.
