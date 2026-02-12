#!/usr/bin/env bash
# setup-hdd-pool.sh — HDD 1개 공유 스토리지 풀 생성 + 5명 컨테이너 마이그레이션
# 사전 조건: root 권한, LXD 초기화 완료, dev-* 컨테이너 5개 존재
#
# Usage:
#   sudo bash setup-hdd-pool.sh              # 실제 실행
#   sudo bash setup-hdd-pool.sh --dry-run    # 명령어 출력만

set -euo pipefail

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}${BOLD}>>> $*${NC}"; }

# --dry-run 플래그
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    warn "드라이런 모드 — 명령어를 출력만 하고 실행하지 않습니다."
fi

run() {
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "  ${YELLOW}[DRY-RUN]${NC} $*"
    else
        info "실행: $*"
        eval "$@"
    fi
}

# 설정
DEVICE="/dev/sda2"
OLD_MOUNT="/storage/j2hoon10"
NEW_MOUNT="/storage/lxd-dev"
POOL_NAME="hdd-dev"
FSTAB="/etc/fstab"

CONTAINERS=("dev-hj" "dev-j2hoon10" "dev-jjjh02" "dev-ryejinn" "dev-yj99son")

declare -A PORT_MAP
PORT_MAP["dev-yj99son"]=13001
PORT_MAP["dev-j2hoon10"]=13002
PORT_MAP["dev-ryejinn"]=13003
PORT_MAP["dev-jjjh02"]=13004
PORT_MAP["dev-hj"]=13005
CONTAINER_PORT=3001

# ── Step 1: root 권한 확인 ──
step "Step 1/7: root 권한 확인"

if [[ "$EUID" -ne 0 ]]; then
    error "root 권한으로 실행해야 합니다: sudo bash $0 [--dry-run]"
    exit 1
fi
info "root 권한 확인 완료"

# ── Step 2: 기존 마운트 해제 ──
step "Step 2/7: 기존 마운트 해제 ($OLD_MOUNT)"

if mountpoint -q "$OLD_MOUNT" 2>/dev/null; then
    warn "기존 마운트 감지: $OLD_MOUNT"
    run "umount $OLD_MOUNT"
    info "기존 마운트 해제 완료"
else
    info "기존 마운트 없음 — 건너뜁니다."
fi

# ── Step 3: 새 마운트 포인트 생성 및 마운트 ──
step "Step 3/7: 새 마운트 포인트 생성 ($NEW_MOUNT)"

run "mkdir -p $NEW_MOUNT"
run "mount $DEVICE $NEW_MOUNT"
info "마운트 완료: $DEVICE -> $NEW_MOUNT"

# ── Step 4: /etc/fstab 업데이트 ──
step "Step 4/7: /etc/fstab 업데이트"

if [[ "$DRY_RUN" == true ]]; then
    echo -e "  ${YELLOW}[DRY-RUN]${NC} 기존 $OLD_MOUNT 항목 주석 처리"
    echo -e "  ${YELLOW}[DRY-RUN]${NC} 새 항목 추가: $DEVICE $NEW_MOUNT ext4 defaults 0 2"
else
    # 기존 마운트 항목 주석 처리
    if grep -q "$OLD_MOUNT" "$FSTAB" 2>/dev/null; then
        sed -i "s|^\([^#].*${OLD_MOUNT}\)|# \1  # 주석 처리 $(date +%Y-%m-%d)|" "$FSTAB"
        info "기존 fstab 항목 주석 처리 완료"
    fi

    # 새 항목 추가
    if grep -q "$NEW_MOUNT" "$FSTAB" 2>/dev/null; then
        warn "fstab에 $NEW_MOUNT 항목이 이미 존재합니다."
    else
        echo "" >> "$FSTAB"
        echo "# LXD 공유 스토리지 풀 ($(date +%Y-%m-%d))" >> "$FSTAB"
        echo "$DEVICE  $NEW_MOUNT  ext4  defaults  0  2" >> "$FSTAB"
        info "fstab 새 항목 추가 완료"
    fi
fi

# ── Step 5: LXD 스토리지 풀 생성 ──
step "Step 5/7: LXD 스토리지 풀 생성 ($POOL_NAME)"

if lxc storage show "$POOL_NAME" &>/dev/null; then
    warn "스토리지 풀 '$POOL_NAME'이 이미 존재합니다."
else
    run "lxc storage create $POOL_NAME dir source=$NEW_MOUNT"
    info "스토리지 풀 '$POOL_NAME' 생성 완료"
fi

# ── Step 6: 컨테이너 마이그레이션 ──
step "Step 6/7: 컨테이너 마이그레이션 (${#CONTAINERS[@]}개)"

for ct in "${CONTAINERS[@]}"; do
    info "마이그레이션: ${BOLD}$ct${NC}"

    if ! lxc info "$ct" &>/dev/null; then
        error "'$ct' 컨테이너가 존재하지 않습니다. 건너뜁니다."
        continue
    fi

    TEMP_NAME="${ct}-migrating"

    # 이미 hdd-dev 풀에 있는지 확인
    if [[ "$DRY_RUN" == false ]]; then
        CURRENT_POOL=$(lxc config device get "$ct" root pool 2>/dev/null || echo "default")
        if [[ "$CURRENT_POOL" == "$POOL_NAME" ]]; then
            info "  '$ct'는 이미 '$POOL_NAME' 풀에 있습니다."
            continue
        fi
    fi

    run "lxc stop $ct --force 2>/dev/null || true"
    run "lxc copy $ct $TEMP_NAME --storage $POOL_NAME"
    run "lxc delete $ct"
    run "lxc rename $TEMP_NAME $ct"
    run "lxc start $ct"
    info "  ${GREEN}$ct 마이그레이션 완료${NC}"
done

# ── Step 7: 프록시 디바이스 추가 ──
step "Step 7/7: 프록시 디바이스 추가 (프론트엔드 포트 포워딩)"

for ct in "${CONTAINERS[@]}"; do
    HOST_PORT="${PORT_MAP[$ct]}"
    PROXY_NAME="frontend-proxy"

    if lxc config device show "$ct" 2>/dev/null | grep -q "$PROXY_NAME"; then
        warn "  $ct: 프록시 '$PROXY_NAME'이 이미 존재합니다."
    else
        info "  $ct: 호스트 :${HOST_PORT} -> 컨테이너 :${CONTAINER_PORT}"
        run "lxc config device add $ct $PROXY_NAME proxy listen=tcp:0.0.0.0:$HOST_PORT connect=tcp:127.0.0.1:$CONTAINER_PORT"
    fi
done

# ── 완료 요약 ──
echo ""
step "설정 완료 요약"
info "스토리지 풀: $POOL_NAME (source: $NEW_MOUNT)"
info "디바이스:    $DEVICE"
info "포트 포워딩:"
for ct in "${CONTAINERS[@]}"; do
    echo -e "  ${GREEN}-${NC} $ct: :${PORT_MAP[$ct]} -> :${CONTAINER_PORT}"
done

if [[ "$DRY_RUN" == true ]]; then
    warn "드라이런 모드였습니다. 실제 실행: sudo bash $0"
else
    info "${GREEN}${BOLD}모든 작업이 완료되었습니다!${NC}"
fi
