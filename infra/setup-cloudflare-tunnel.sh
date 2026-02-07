#!/bin/bash
# ============================================================
# Cloudflare Tunnel 설치 및 설정 스크립트
# deploy-test 컨테이너(10.10.10.20) 내부에서 실행
#
# 사전 준비:
#   1. Cloudflare 계정 + adelie-invest.com 도메인
#   2. deploy-test에서 Docker 서비스가 실행 중이어야 함
#
# 사용법: bash setup-cloudflare-tunnel.sh
# ============================================================

set -e

echo "=== Cloudflare Tunnel 설치 ==="

# 1. cloudflared 설치
if ! command -v cloudflared &>/dev/null; then
    echo "cloudflared 설치 중..."
    curl -fsSL https://pkg.cloudflare.com/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb
    rm /tmp/cloudflared.deb
else
    echo "cloudflared 이미 설치됨: $(cloudflared --version)"
fi

# 2. Cloudflare 인증
echo ""
echo "=== Cloudflare 인증 ==="
echo "아래 URL을 브라우저에서 열어 adelie-invest.com 도메인을 선택하세요."
echo ""
cloudflared tunnel login

# 3. 터널 생성
echo ""
echo "=== 터널 생성 ==="
cloudflared tunnel create adelie-demo

# 4. DNS 라우팅
echo ""
echo "=== DNS 라우팅 설정 ==="
cloudflared tunnel route dns adelie-demo demo.adelie-invest.com

# 5. 설정 파일 생성
TUNNEL_ID=$(cloudflared tunnel list --output json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || echo "TUNNEL_ID_HERE")

mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: demo.adelie-invest.com
    service: http://localhost:80
  - service: http_status:404
EOF

echo ""
echo "=== 설정 파일 생성 완료 ==="
cat ~/.cloudflared/config.yml

# 6. 서비스 등록
echo ""
echo "=== systemd 서비스 등록 ==="
cloudflared service install 2>/dev/null || true
systemctl enable cloudflared 2>/dev/null || true
systemctl start cloudflared 2>/dev/null || true

echo ""
echo "=== 완료! ==="
echo "접속 URL: https://demo.adelie-invest.com"
echo ""
echo "상태 확인: systemctl status cloudflared"
echo "로그 확인: journalctl -u cloudflared -f"
