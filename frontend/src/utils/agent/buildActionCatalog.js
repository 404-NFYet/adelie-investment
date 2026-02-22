function baseActions() {
  return [
    {
      id: 'nav_home',
      label: '홈으로 이동',
      risk: 'low',
      params_schema: {},
      intent_keywords: ['홈', 'home', '메인'],
    },
    {
      id: 'nav_portfolio',
      label: '투자 탭으로 이동',
      risk: 'low',
      params_schema: {},
      intent_keywords: ['투자', '포트', 'portfolio', '종목'],
    },
    {
      id: 'nav_education',
      label: '교육 탭으로 이동',
      risk: 'low',
      params_schema: {},
      intent_keywords: ['교육', '학습', 'education', '브리핑'],
    },
    {
      id: 'open_agent_history',
      label: '대화 기록 열기',
      risk: 'low',
      params_schema: {},
      intent_keywords: ['기록', '히스토리', 'history'],
    },
  ];
}

export default function buildActionCatalog({
  pathname = '/home',
  mode = 'home',
  stockContext = null,
} = {}) {
  const actions = [...baseActions()];

  if (pathname.startsWith('/home') || mode === 'home') {
    actions.push(
      {
        id: 'open_home_issue_agent',
        label: '오늘 이슈 분석 시작',
        risk: 'low',
        params_schema: {
          prompt: 'string?',
        },
        intent_keywords: ['이슈', '분석', '아델리와 알아보기'],
      },
    );
  }

  if (pathname.startsWith('/portfolio') || mode === 'stock') {
    actions.push(
      {
        id: 'open_stock_agent',
        label: '종목 분석 캔버스 열기',
        risk: 'low',
        params_schema: {
          stock_code: 'string?',
          stock_name: 'string?',
        },
        intent_keywords: ['종목 분석', '이 종목 물어보기', '체크포인트'],
      },
      {
        id: 'buy_stock',
        label: '매수 화면으로 이동',
        risk: 'high',
        params_schema: {
          stock_code: 'string?',
          stock_name: 'string?',
        },
        intent_keywords: ['매수', 'buy'],
      },
      {
        id: 'sell_stock',
        label: '매도 화면으로 이동',
        risk: 'high',
        params_schema: {
          stock_code: 'string?',
          stock_name: 'string?',
        },
        intent_keywords: ['매도', 'sell'],
      },
    );
  }

  if (pathname.startsWith('/agent') || pathname.startsWith('/home') || pathname.startsWith('/education')) {
    actions.push(
      {
        id: 'open_learning_history',
        label: '학습 히스토리 보기',
        risk: 'low',
        params_schema: {},
        intent_keywords: ['복습', '학습 이력', '아카이브'],
      },
    );
  }

  if (stockContext?.stock_code) {
    actions.push({
      id: 'open_external_stock_info',
      label: '외부 종목 정보 열기',
      risk: 'high',
      params_schema: {
        stock_code: 'string',
      },
      intent_keywords: ['외부', '네이버', '공시'],
    });
  }

  return actions;
}
