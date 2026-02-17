export const DEFAULT_HOME_ICON_KEY = 'chart-dynamic-color';

export const HOME_ICON_CATALOG = [
  { key: 'chart-dynamic-color', src: '/images/figma/home-icons/chart-dynamic-color.png', label: '시장 흐름' },
  { key: 'money-dynamic-color', src: '/images/figma/home-icons/money-dynamic-color.png', label: '현금 흐름' },
  { key: 'money-bag-dynamic-color', src: '/images/figma/home-icons/money-bag-dynamic-color.png', label: '수익성' },
  { key: 'wallet-dynamic-color', src: '/images/figma/home-icons/wallet-dynamic-color.png', label: '자산' },
  { key: 'card-dynamic-color', src: '/images/figma/home-icons/card-dynamic-color.png', label: '결제' },
  { key: 'dollar-dollar-color', src: '/images/figma/home-icons/dollar-dollar-color.png', label: '달러' },
  { key: 'euro-dynamic-color', src: '/images/figma/home-icons/euro-dynamic-color.png', label: '유로' },
  { key: 'pound-dynamic-color', src: '/images/figma/home-icons/pound-dynamic-color.png', label: '파운드' },
  { key: 'yuan-dynamic-color', src: '/images/figma/home-icons/yuan-dynamic-color.png', label: '위안' },
  { key: 'rupee-dynamic-color', src: '/images/figma/home-icons/rupee-dynamic-color.png', label: '루피' },
  { key: '3d-coin-dynamic-color', src: '/images/figma/home-icons/3d-coin-dynamic-color.png', label: '코인' },
  { key: 'calculator-dynamic-color', src: '/images/figma/home-icons/calculator-dynamic-color.png', label: '지표 계산' },
  { key: 'bulb-dynamic-color', src: '/images/figma/home-icons/bulb-dynamic-color.png', label: '인사이트' },
  { key: 'rocket-dynamic-color', src: '/images/figma/home-icons/rocket-dynamic-color.png', label: '급성장' },
  { key: 'target-dynamic-color', src: '/images/figma/home-icons/target-dynamic-color.png', label: '목표' },
  { key: 'bookmark-dynamic-color', src: '/images/figma/home-icons/bookmark-dynamic-color.png', label: '핵심 포인트' },
  { key: 'file-text-dynamic-color', src: '/images/figma/home-icons/file-text-dynamic-color.png', label: '리포트' },
  { key: 'medal-dynamic-color', src: '/images/figma/home-icons/medal-dynamic-color.png', label: '우수 종목' },
  { key: 'sheild-dynamic-color', src: '/images/figma/home-icons/sheild-dynamic-color.png', label: '방어' },
  { key: 'lock-dynamic-color', src: '/images/figma/home-icons/lock-dynamic-color.png', label: '리스크 관리' },
];

export const HOME_ICON_MAP = HOME_ICON_CATALOG.reduce((acc, icon) => {
  acc[icon.key] = icon;
  return acc;
}, {});

export function getHomeIconSrc(iconKey) {
  const key = iconKey && HOME_ICON_MAP[iconKey] ? iconKey : DEFAULT_HOME_ICON_KEY;
  return HOME_ICON_MAP[key].src;
}

