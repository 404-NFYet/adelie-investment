# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# LXD 서버 점검 및 싱크 정상화 계획

## Context

2026-02-24 현재 LXD 5대 + deploy-test + infra-server 전체 상태를 점검한 결과,
4가지 이슈가 발견됐다. 배포 서버(deploy-test)는 정상이나 dev 환경이 최신 origin과 불일치한다.

---

## 발견된 이슈 요약

| 서버 | 이슈 | 심각도 |
|------|------|--------|
| dev-j2hoon10 | 컨테이너 전혀 없음 (이미지만 존재) | 🔴 긴급 |
| dev-j2hoon10, dev-j...

### Prompt 2

배포 서버의 DB 마이그레이션시 컨텐츠 뿐만 아니라 DB 자체에 있는 모든 정보를 업데이트해야 한다.

### Prompt 3

모든 LXD 서버에 데이터 동기화를 진행해라

### Prompt 4

현재 배포된 화면과 로컬 3001번으로 화면을 봤을 때, AgentDock이 있을 때의 화면이 있는데 이를 올바르게 수정하고 모든 LXD에 싱크를 맞춰야 한다.

### Prompt 5

[Request interrupted by user for tool use]

### Prompt 6

도커 이미지의 문제인지 재확인하는게 좋을 것 같다.

### Prompt 7

[Request interrupted by user for tool use]

