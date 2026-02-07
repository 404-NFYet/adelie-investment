# AWS 아키텍처

## 전체 구조

- VPC: 10.0.0.0/16
  - Public Subnet x2 (10.0.1.0/24, 10.0.2.0/24) - ALB, Bastion, NAT
  - Private Subnet x2 (10.0.10.0/24, 10.0.20.0/24) - ECS, RDS, ElastiCache, Neo4j
- ECS Fargate: Frontend, FastAPI, Spring Boot (ALB 뒤)
- RDS PostgreSQL 16 + pgvector
- ElastiCache Redis 7
- EC2 Neo4j (Docker)
- S3 (MinIO 대체)
- Secrets Manager (API 키 관리)
- EventBridge (일일 파이프라인 스케줄)

## 접속 경로

사용자 -> ALB -> ECS Fargate -> RDS/Redis/Neo4j
관리자 -> Bastion(SSH) -> Private 리소스

## 예상 월 비용 (dev): $115-140
