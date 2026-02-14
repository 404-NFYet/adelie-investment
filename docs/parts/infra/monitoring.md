# 모니터링 구성

> Grafana + Prometheus 구성, node_exporter, cAdvisor, 알림 규칙, 접속 정보를 다룬다.

---

## 접속 정보

| 서비스 | URL | 인증 |
|--------|-----|------|
| Grafana | https://monitoring.adelie-invest.com | mutsa1234 / mutsa1234 |
| Prometheus | http://10.10.10.10:9090 (내부 전용) | 없음 |

---

## 아키텍처

```
infra-server (10.10.10.10)
├── Prometheus (:9090)
│   ├── scrape: node_exporter (7개 인스턴스)
│   └── scrape: cAdvisor (2개 인스턴스)
└── Grafana (:3000)
    ├── 데이터 소스: Prometheus
    ├── 프로비저닝: dashboards, alerting
    └── Cloudflare Tunnel → monitoring.adelie-invest.com
```

### Docker Compose (infra/monitoring/docker-compose.yml)

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: adelie-prometheus
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=30d

  grafana:
    image: grafana/grafana:latest
    container_name: adelie-grafana
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_USER: mutsa1234
      GF_SECURITY_ADMIN_PASSWORD: mutsa1234
      GF_SERVER_ROOT_URL: https://monitoring.adelie-invest.com
      GF_AUTH_ANONYMOUS_ENABLED: "false"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
```

---

## 수집 대상

### node_exporter (7개)

각 LXD 인스턴스에서 `node_exporter`가 `:9100`에서 실행되며, 시스템 메트릭(CPU, RAM, Disk, Network)을 제공한다.

| 인스턴스 | 타겟 | 역할 |
|----------|------|------|
| infra-server | `10.10.10.10:9100` | 공유 인프라 |
| deploy-test | `10.10.10.20:9100` | prod 배포 |
| dev-yj99son | `10.10.10.14:9100` | Frontend 개발 |
| dev-j2hoon10 | `10.10.10.11:9100` | Chatbot 개발 |
| dev-ryejinn | `10.10.10.13:9100` | Pipeline 개발 |
| dev-jjjh02 | `10.10.10.12:9100` | Backend 개발 |
| dev-hj | `10.10.10.15:9100` | Infra 개발 |

### cAdvisor (2개)

Docker 컨테이너 메트릭(CPU, RAM, 네트워크, 재시작 횟수)을 수집한다.

| 인스턴스 | 타겟 | 모니터링 대상 |
|----------|------|-------------|
| infra-server | `10.10.10.10:8080` | narrative-postgres, narrative-redis, narrative-neo4j, narrative-minio |
| deploy-test | `10.10.10.20:8080` | adelie-frontend, adelie-backend-api, adelie-postgres, adelie-redis |

---

## Prometheus 설정 (prometheus.yml)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets:
          - '10.10.10.10:9100'   # infra-server
          - '10.10.10.20:9100'   # deploy-test
          - '10.10.10.14:9100'   # dev-yj99son
          - '10.10.10.11:9100'   # dev-j2hoon10
          - '10.10.10.13:9100'   # dev-ryejinn
          - '10.10.10.12:9100'   # dev-jjjh02
          - '10.10.10.15:9100'   # dev-hj
        labels:
          env: 'lxd'

  - job_name: 'cadvisor'
    static_configs:
      - targets:
          - '10.10.10.10:8080'   # infra-server
          - '10.10.10.20:8080'   # deploy-test
```

---

## 알림 규칙 (Grafana Alerting)

`infra/monitoring/grafana/provisioning/alerting/rules.yml`에 정의된다.

| 알림 | 조건 | 지속 시간 | 심각도 |
|------|------|----------|--------|
| **HighCPU** | CPU 사용률 > 90% | 5분 | warning |
| **HighMemory** | RAM 사용률 > 85% | 5분| warning |
| **DiskAlmostFull** | Disk 사용률 > 80% | 10분 | critical |
| **ContainerDown** | `adelie-*` 컨테이너 미감지 | 1분 | critical |
| **ContainerRestart** | `adelie-*` 컨테이너 재시작 감지 | 즉시 | warning |

### 알림 표현식

```yaml
# CPU > 90% (5분 지속)
100 - (avg by(instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90

# RAM > 85% (5분 지속)
(1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes) * 100 > 85

# Disk > 80% (10분 지속)
100 - (node_filesystem_avail_bytes{mountpoint="/"}/node_filesystem_size_bytes{mountpoint="/"} * 100) > 80

# 컨테이너 다운 (1분)
absent(container_last_seen{name=~"adelie-.*"})

# 컨테이너 재시작 (5분 내)
increase(container_restart_count{name=~"adelie-.*"}[5m]) > 0
```

---

## Grafana 프로비저닝

### 디렉토리 구조

```
infra/monitoring/grafana/provisioning/
├── datasources/
│   └── prometheus.yml    # Prometheus 데이터 소스 자동 등록
├── dashboards/
│   └── dashboard.yml     # 대시보드 프로비저닝 설정
└── alerting/
    └── rules.yml         # 알림 규칙 (위 5개)
```

### 데이터 소스

```yaml
# datasources/prometheus.yml
- name: Prometheus
  type: prometheus
  access: proxy
  url: http://prometheus:9090
  isDefault: true
```

---

## 모니터링 운영

### 재시작

```bash
# 모니터링 스택 재시작
ssh infra-server 'cd /opt/narrative-investment/infra/monitoring && docker compose restart'

# Prometheus만 재시작 (설정 변경 후)
ssh infra-server 'docker restart adelie-prometheus'

# Grafana만 재시작
ssh infra-server 'docker restart adelie-grafana'
```

### 상태 확인

```bash
# Prometheus 타겟 상태
ssh infra-server 'curl -s http://localhost:9090/api/v1/targets | jq ".data.activeTargets[] | {instance: .labels.instance, health: .health}"'

# Grafana 헬스
curl https://monitoring.adelie-invest.com/api/health

# 로그 확인
ssh infra-server 'docker logs adelie-prometheus --tail 50'
ssh infra-server 'docker logs adelie-grafana --tail 50'
```

### 데이터 보존

- Prometheus: `--storage.tsdb.retention.time=30d` (30일 보존)
- Grafana: Docker volume `grafana_data` (대시보드, 설정 등)

---

## 향후 추가 예정

- [ ] PostgreSQL exporter (DB 쿼리 성능 메트릭)
- [ ] Redis exporter (캐시 히트율, 메모리 사용)
- [ ] FastAPI 애플리케이션 메트릭 (Prometheus client)
- [ ] 알림 채널 연동 (Discord Webhook)
