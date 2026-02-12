# Bastion 서버 접속 가이드

## SSH 접속

```bash
# 기본 SSH 접속
ssh -i ~/.ssh/adelie-bastion.pem ec2-user@<BASTION_PUBLIC_IP>

# 또는 Terraform output 사용
BASTION_IP=$(terraform -chdir=infra/terraform/environments/dev output -raw bastion_ip)
ssh -i ~/.ssh/adelie-bastion.pem ec2-user@$BASTION_IP

# SSH 설정 파일 사용 (~/.ssh/config)
Host bastion-adelie
    HostName <BASTION_PUBLIC_IP>
    User ec2-user
    IdentityFile ~/.ssh/adelie-bastion.pem
    StrictHostKeyChecking no

# 설정 파일 사용하여 접속
ssh bastion-adelie
```

## SSH 키 설정

```bash
# 키 파일 권한 설정 (필수)
chmod 400 ~/.ssh/adelie-bastion.pem

# SSH 에이전트에 키 추가
ssh-add ~/.ssh/adelie-bastion.pem
```

## 포트 포워딩 (터널링)

```bash
# RDS PostgreSQL 접속을 위한 터널링
ssh -i ~/.ssh/adelie-bastion.pem \
    -L 5432:<RDS_ENDPOINT>:5432 \
    ec2-user@<BASTION_PUBLIC_IP> -N

# 백그라운드 실행
ssh -i ~/.ssh/adelie-bastion.pem \
    -L 5432:<RDS_ENDPOINT>:5432 \
    -f -N ec2-user@<BASTION_PUBLIC_IP>

# 터널링 후 로컬에서 RDS 접속
psql -h localhost -U postgres -d adelie_db
```

## ECS Task 접속 (ECS Exec)

```bash
# ECS Exec 활성화 확인 (Task Definition에 enableExecuteCommand: true 필요)

# 실행 중인 Task ID 확인
TASK_ID=$(aws ecs list-tasks --cluster adelie-cluster --service-name adelie-backend-api --query 'taskArns[0]' --output text --region ap-northeast-2)

# Task에 접속
aws ecs execute-command \
  --cluster adelie-cluster \
  --task $TASK_ID \
  --container backend-api \
  --command "/bin/bash" \
  --interactive \
  --region ap-northeast-2
```

## Private 리소스 접근

```bash
# Bastion을 통한 RDS 접속
# 1. Bastion에 SSH 접속
ssh bastion-adelie

# 2. Bastion에서 RDS 접속
psql -h <RDS_PRIVATE_ENDPOINT> -U postgres -d adelie_db

# 3. 또는 터널링 사용 (위의 포트 포워딩 참조)
```

## 보안 그룹 확인

```bash
# Bastion 보안 그룹 확인
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=adelie-bastion-sg" \
  --region ap-northeast-2

# RDS 보안 그룹 확인
aws rds describe-db-instances \
  --db-instance-identifier adelie-postgres \
  --query 'DBInstances[0].VpcSecurityGroups' \
  --region ap-northeast-2
```
