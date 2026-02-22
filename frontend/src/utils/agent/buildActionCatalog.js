function baseActions() {
  return [
    {
      id: 'nav_home',
      label: '홈으로 이동',
      description: '현재 화면을 홈 탭으로 전환합니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: {},
    },
    {
      id: 'nav_portfolio',
      label: '투자 탭으로 이동',
      description: '현재 화면을 투자 탭으로 전환합니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: {},
    },
    {
      id: 'nav_education',
      label: '교육 탭으로 이동',
      description: '현재 화면을 교육 탭으로 전환합니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: {},
    },
    {
      id: 'open_agent_history',
      label: '대화 기록 열기',
      description: '에이전트 대화 기록 목록 화면으로 이동합니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: {},
    },
    {
      id: 'check_portfolio',
      label: '내 포트폴리오 확인',
      description: '현재 보유 종목, 현금, 수익률 요약을 조회합니다.',
      type: 'tool',
      risk: 'low',
      params_schema: {},
    },
  ];
}

export default function buildActionCatalog({
  pathname = '/home',
  mode = 'home',
  stockContext = null,
} = {}) {
  const actions = [...baseActions()];
  const hasStockCode = Boolean(stockContext?.stock_code);

  if (pathname.startsWith('/home') || mode === 'home') {
    actions.push({
      id: 'open_home_issue_agent',
      label: '오늘 이슈 분석 시작',
      description: '홈 컨텍스트로 캔버스 분석 화면을 엽니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: { prompt: 'string?' },
    });
  }

  if (pathname.startsWith('/portfolio') || mode === 'stock') {
    actions.push(
      {
        id: 'open_stock_agent',
        label: '종목 분석 캔버스 열기',
        description: '선택 종목 컨텍스트로 캔버스 분석 화면을 엽니다.',
        type: 'navigate',
        risk: 'low',
        params_schema: { stock_code: 'string?', stock_name: 'string?' },
      },
    );
  }

  if (hasStockCode || mode === 'stock') {
    actions.push(
      {
        id: 'buy_stock',
        label: '이 종목 매수하기',
        description: '현재 시세를 조회한 뒤 매수 주문을 실행합니다. 사용자 확인이 필요합니다.',
        type: 'tool',
        risk: 'high',
        params_schema: { stock_code: 'string', stock_name: 'string?' },
      },
      {
        id: 'sell_stock',
        label: '이 종목 매도하기',
        description: '현재 시세를 조회한 뒤 매도 주문을 실행합니다. 사용자 확인이 필요합니다.',
        type: 'tool',
        risk: 'high',
        params_schema: { stock_code: 'string', stock_name: 'string?' },
      },
      {
        id: 'check_stock_price',
        label: '현재 시세 확인',
        description: '해당 종목의 현재 시세를 조회합니다.',
        type: 'tool',
        risk: 'low',
        params_schema: { stock_code: 'string' },
      },
    );
  }

  if (pathname.startsWith('/agent') || pathname.startsWith('/home') || pathname.startsWith('/education')) {
    actions.push({
      id: 'open_learning_history',
      label: '학습 히스토리 보기',
      description: '교육 아카이브 화면으로 이동합니다.',
      type: 'navigate',
      risk: 'low',
      params_schema: {},
    });
  }

  if (hasStockCode) {
    actions.push({
      id: 'open_external_stock_info',
      label: '외부 종목 정보 열기',
      description: '외부 종목 정보 페이지를 새 창으로 엽니다. 사용자 확인이 필요합니다.',
      type: 'navigate',
      risk: 'high',
      params_schema: { stock_code: 'string' },
    });
  }

  return actions;
}
