import os

html_head = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>ADELIE V2 — 에이전틱 서비스의 본질에 대하여</title>
    <link rel="stylesheet" href="style-os.css">
</head>
<body>
    <div class="presentation-container">
"""

slide_0_cover = """
        <!-- SLIDE 0: COVER -->
        <div class="slide active" id="slide-0">
            <div class="center-content">
                <h1 class="cover-title">에이전틱 서비스의<br>본질에 대하여</h1>
                <p class="cover-subtitle">사용자의 직관(Vibe)을 자산(Knowledge)으로 바꾸는 과정</p>
            </div>
            <div class="slide-footer">
                <span class="slide-footer__logo">adelie team</span>
            </div>
        </div>
"""

slide_1_toc = """
        <!-- SLIDE 1: CONTENTS -->
        <div class="slide" id="slide-1">
            <div class="slide-header">
                <h2 class="slide-header__title">OVERVIEW</h2>
                <p class="slide-header__subtitle">[Base: ADELIE 프로젝트 내러티브 구조]</p>
            </div>
            <div class="split-layout">
                <div class="flat-list">
                    <div class="flat-item">
                        <div class="flat-item__icon">01</div>
                        <div class="flat-item__content">
                            <h3>시장의 딜레마</h3>
                            <p>깊지만 높은 장벽(HTS)과 얕고 불안한 접근(MTS) 사이의 2030 투자자.</p>
                        </div>
                    </div>
                    <div class="flat-item">
                        <div class="flat-item__icon">02</div>
                        <div class="flat-item__content">
                            <h3>아델리의 해답</h3>
                            <p>Vibe Investing: 투자자의 직관을 에이전트가 완결된 맥락으로 보완.</p>
                        </div>
                    </div>
                    <div class="flat-item">
                        <div class="flat-item__icon">03</div>
                        <div class="flat-item__content">
                            <h3>사용자 경험 시나리오</h3>
                            <p>가벼운 탐색에서 시작해 지식의 자산화에 이르는 에이전틱 플로우.</p>
                        </div>
                    </div>
                    <div class="flat-item">
                        <div class="flat-item__icon">04</div>
                        <div class="flat-item__content">
                            <h3>미래 비전과 본질</h3>
                            <p>기능의 대체가 아닌 주도권의 공존, Explainable UX의 중요성.</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">1</span></div>
        </div>
"""

slide_2_part1 = """
        <div class="slide" id="slide-2">
            <div class="center-content">
                <p style="font-weight:800; color:var(--primary-blue); margin-bottom:12px; font-size:18px;">Part 1</p>
                <h2 class="cover-title">시장의 딜레마</h2>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">2</span></div>
        </div>
"""

slide_3_target_dilemma = """
        <!-- SLIDE 3: TARGET & DILEMMA -->
        <div class="slide" id="slide-3">
            <div class="slide-header">
                <h2 class="slide-header__title">현상: 투자는 일상이 되었지만 <em>깊이는 상실되었다</em></h2>
                <p class="slide-header__subtitle">[Base: 국내 주식 투자 앱 UI/UX 및 2030 성향 분석]</p>
            </div>
            <div class="split-layout">
                <div style="flex:1; padding-right:20px; border-right:1px dashed var(--border-color); display:flex; flex-direction:column; justify-content:center;">
                    <h3 style="font-size:22px; font-weight:800; margin-bottom:20px; color:#111;">일상적인 2030 초보 투자자</h3>
                    <p style="font-size:15px; color:var(--text-gray); line-height:1.6; margin-bottom:20px;">
                        HTS(영웅문 등)를 쓸 시간도 전문 지식도 없으며,<br>흩어진 유튜브 정보로 공부하기엔 여력이 부족합니다.
                    </p>
                    <div style="background:#f4f5f7; padding:16px; border-radius:8px; display:inline-block;">
                        <span style="font-weight:800; color:var(--primary-blue); font-size:24px;">72.1%</span>
                        <span style="font-size:13px; color:#555; display:block; margin-top:4px;">Z세대의 앱 선택 1위 이유 ("편리함")</span>
                    </div>
                </div>
                <div style="flex:1; padding-left:20px; display:flex; flex-direction:column; justify-content:center;">
                    <h3 style="font-size:22px; font-weight:800; margin-bottom:20px; color:var(--accent-red);">양극화된 모바일 환경</h3>
                    <div class="compare-h-row left" style="width:100%; margin-bottom:12px;">
                        <div class="compare-h-diff" style="color:#555; width:40px; text-align:left;">HTS</div>
                        <div class="compare-h-val" style="width:80px">정보 뎁스</div>
                        <div class="compare-h-bar" style="width: 50%; background:#d0d0d0;"></div>
                    </div>
                    <div class="compare-h-row" style="width:100%;">
                        <div class="compare-h-diff" style="color:var(--primary-blue); width:40px; text-align:right; font-weight:800;">MTS</div>
                        <div class="compare-h-val" style="width:80px; text-align:right;">접근성</div>
                        <div class="compare-h-bar" style="width: 70%; background:var(--primary-blue); align-self:flex-end; border-radius:4px 0 0 4px;"></div>
                    </div>
                    <p style="margin-top:24px; font-size:14px; color:var(--text-gray); line-height: 1.5;">
                        결과적으로 직관(Vibe)에 의존하여 3탭 만에 빠르게 매수하지만,<br>
                        <strong style="color:#111;">스스로 '왜 샀는지' 명확히 설명하지 못하는 불안정성</strong>이 존재합니다.
                    </p>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">3</span></div>
        </div>
"""

slide_4_failure = """
        <!-- SLIDE 4: FAILURE -->
        <div class="slide" id="slide-4">
            <div class="slide-header">
                <h2 class="slide-header__title">초기 가설의 실패: <em>교육은 선행되지 않는다</em></h2>
                <p class="slide-header__subtitle">[Base: 정통적 순차 학습 시나리오와 실제 행동의 괴리]</p>
            </div>
            <div class="line-chart-container" style="border:none;">
                <div class="line-chart-col" style="padding-left:0;">
                    <div class="line-title-top"><span class="icon">A</span> 기존의 패러다임 (선 교육)</div>
                    <div style="display:flex; flex-direction:column; align-items:center; gap:16px; margin-top:10px;">
                        <div style="padding:16px; width:100%; text-align:center; border:1px solid var(--border-color); border-radius:4px; font-weight:700; color:#555;">1. 이론 및 용어 학습</div>
                        <div style="color:#ccc;">↓</div>
                        <div style="padding:16px; width:100%; text-align:center; border:1px solid #111; color:#111; font-weight:800; border-radius:4px;">2. 실전 투자 진행</div>
                    </div>
                </div>
                <div class="line-chart-col" style="padding-right:0;">
                    <div class="line-title-top"><span class="icon highlight" style="background:#111;">B</span> 실제 투자자의 패턴 (후 학습)</div>
                    <div style="display:flex; flex-direction:column; align-items:center; gap:16px; margin-top:10px;">
                        <div style="padding:16px; width:100%; text-align:center; border:1px solid #111; color:#111; font-weight:800; border-radius:4px;">1. 직관적 매수 (선 투자)</div>
                        <div style="color:#111; font-weight:800; font-size:20px;">↓</div>
                        <div style="padding:16px; width:100%; text-align:center; border:1px solid #111; background:#f4f5f7; color:#111; font-weight:800; border-radius:4px;">2. 손실 또는 변동성 경험</div>
                        <div style="color:#111; font-weight:800; font-size:20px;">↓</div>
                        <div style="padding:16px; width:100%; text-align:center; border:1px dashed #111; color:#111; font-weight:800; border-radius:4px;">3. 원인 파악을 위한 사후 탐색</div>
                    </div>
                </div>
            </div>
            <div style="margin-top:30px; background:#f8f9fc; padding:20px 24px; border-radius:8px; display:flex; gap:20px; align-items:center;">
                <div class="chip" style="font-size:14px; padding:6px 16px;">Insight</div>
                <div style="font-size:15px; font-weight:500; color:#333; line-height: 1.5;">사용자는 투자 결정의 <strong>그 순간</strong>에 가장 높은 학습 필요성을 느낍니다.<br>교육 콘텐츠의 나열이 아닌, <strong style="color:var(--primary-blue)">유저의 액션 사이를 채워주는 에이전트</strong>가 필요합니다.</div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">4</span></div>
        </div>
"""

slide_5_part2 = """
        <div class="slide" id="slide-5">
            <div class="center-content">
                <p style="font-weight:800; color:var(--primary-blue); margin-bottom:12px; font-size:18px;">Part 2</p>
                <h2 class="cover-title">아델리의 해답</h2>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">5</span></div>
        </div>
"""

slide_6_vibe = """
        <!-- SLIDE 6: VIBE INVESTING -->
        <div class="slide" id="slide-6">
            <div class="slide-header">
                <h2 class="slide-header__title">핵심 철학: <em>Vibe Investing</em></h2>
                <p class="slide-header__subtitle">[Base: 개발 프레임워크의 변화를 투자 씬으로 치환]</p>
            </div>
            <div class="split-layout">
                <div style="display:flex; flex-direction:column; justify-content:center; gap:30px;">
                    <div>
                        <h3 style="font-size:22px; font-weight:800; color:#111; margin-bottom:12px;">Vibe Coding <span style="font-size:12px; font-weight:600; color:var(--text-light); margin-left:6px;">(Cursor 등 개발자 도구)</span></h3>
                        <p style="font-size:15px; line-height:1.6; color:var(--text-gray);">
                            "정확한 문법(Syntax)을 몰라도 '이런 느낌으로 만들어줘'라고 에이전트에게 지시하면 코드가 출력되고 개발자는 승인합니다."
                        </p>
                    </div>
                </div>
                <div style="display:flex; align-items:center; justify-content:center; flex:0 0 30px;">
                    <span style="font-size:24px; font-weight:800; color:var(--border-color);">→</span>
                </div>
                <div style="display:flex; flex-direction:column; justify-content:center; gap:30px;">
                    <div>
                        <h3 style="font-size:22px; font-weight:800; color:var(--primary-blue); margin-bottom:12px;">Vibe Investing</h3>
                        <p style="font-size:15px; line-height:1.6; color:var(--text-gray);">
                            "완벽한 재무제표 분석 지식이 없어도 '반도체 요즘 핫하다던데?'라는 직관적 트리거로 시작하면, <strong>에이전트가 평가 맥락을 구조화하여 보완</strong>합니다."
                        </p>
                    </div>
                    <div style="padding-top:20px; border-top:1px solid #111;">
                        <span style="font-size:14px; color:var(--text-gray); line-height:1.5;">투자의 최종 승인권은 사용자에게 남기고, 인지적 부하(조사/분석)만 에이전트가 대신 수행하는 공생 구조입니다.</span>
                    </div>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">6</span></div>
        </div>
"""

slide_7_structure = """
        <!-- SLIDE 7: STRUCTURE -->
        <div class="slide" id="slide-7">
            <div class="slide-header">
                <h2 class="slide-header__title">이를 실현하는 <em>세 가지 인프라</em></h2>
                <p class="slide-header__subtitle">[Base: ADELIE 서비스 아키텍처 및 핵심 기능]</p>
            </div>
            <div class="flat-list">
                <div class="flat-item">
                    <div class="flat-item__icon" style="background:#f4f5f7; color:#111;">01</div>
                    <div class="flat-item__content">
                        <h3>현실적 시뮬레이션 <span class="chip chip--gray">모의투자</span></h3>
                        <p>실시세 연동, 슬리피지 및 부분체결 반영. 실패해도 자본 손실이 없는 '안전한 실험실'을 제공하여 의사결정의 두려움을 제거합니다.</p>
                    </div>
                </div>
                <div class="flat-item">
                    <div class="flat-item__icon" style="background:#f4f5f7; color:#111;">02</div>
                    <div class="flat-item__content">
                        <h3>투자의 Co-pilot <span class="chip chip--gray">상시 대기 에이전트</span></h3>
                        <p>독립된 페이지가 아닌, 투자와 탐색 과정 전반에 걸쳐 하단에 상주하며 사용자의 액션에 논리적 근거와 데이터를 덧붙여 줍니다.</p>
                    </div>
                </div>
                <div class="flat-item">
                    <div class="flat-item__icon" style="background:#f4f5f7; color:#111;">03</div>
                    <div class="flat-item__content">
                        <h3>개인화된 지식 축적 <span class="chip chip--gray">자산화 엔진</span></h3>
                        <p>대화를 통해 이해한 리포트, 재무 용어가 마크다운 뷰 형태의 '나만의 카드'로 저장되어 향후 투자 컨텍스트에 지속적으로 반영됩니다.</p>
                    </div>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">7</span></div>
        </div>
"""

slide_8_part3 = """
        <div class="slide" id="slide-8">
            <div class="center-content">
                <p style="font-weight:800; color:var(--primary-blue); margin-bottom:12px; font-size:18px;">Part 3</p>
                <h2 class="cover-title">사용자 경험 시나리오</h2>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">8</span></div>
        </div>
"""

slide_9_flow = """
        <!-- SLIDE 9: FLOW -->
        <div class="slide" id="slide-9">
            <div class="slide-header">
                <h2 class="slide-header__title">작동 방식: <em>감이 어떻게 지식으로 치환되는가</em></h2>
                <p class="slide-header__subtitle">[Base: 실제 앱 내 에이전트 개입 시나리오 플로우]</p>
            </div>
            <div style="display:flex; flex-direction:column; gap:24px; align-items: center; justify-content: center; flex: 1; padding: 0 40px;">
                <div style="display:flex; align-items:flex-start; gap:24px; border-bottom:1px solid var(--border-light); padding-bottom:24px; width:100%;">
                    <div style="font-size:14px; color:#111; font-weight:700; width:120px; flex-shrink:0;">Step 01<br><span style="font-size:12px; color:var(--text-light); font-weight:500;">비목적성 탐색</span></div>
                    <div>
                        <div style="font-size:16px; font-weight:700; color:#111; margin-bottom:8px;">타임라인 기반의 직관적 뉴스 탐색</div>
                        <p style="font-size:14px; color:var(--text-gray);">사용자가 뚜렷한 분석 목적 없이 화제성 종목이나 트렌드를 가볍게 스크롤합니다.</p>
                    </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:24px; border-bottom:1px solid var(--border-light); padding-bottom:24px; width:100%;">
                    <div style="font-size:14px; color:#111; font-weight:700; width:120px; flex-shrink:0;">Step 02<br><span style="font-size:12px; color:var(--primary-blue); font-weight:800;">에이전트 개입</span></div>
                    <div>
                        <div style="font-size:16px; font-weight:700; color:#111; margin-bottom:8px;">컨텍스트 매칭 및 객관적 리포트 제시</div>
                        <p style="font-size:14px; color:var(--text-gray);">관심을 보인 종목에 대해 에이전트가 기관 리포트의 요약본과 재무 상태를 적절한 타이밍에 팝업 제안합니다.</p>
                    </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:24px; border-bottom:1px solid var(--border-light); padding-bottom:24px; width:100%;">
                    <div style="font-size:14px; color:#111; font-weight:700; width:120px; flex-shrink:0;">Step 03<br><span style="font-size:12px; color:var(--text-light); font-weight:500;">안전한 실행</span></div>
                    <div>
                        <div style="font-size:16px; font-weight:700; color:#111; margin-bottom:8px;">모의투자 환경으로의 매끄러운 연결</div>
                        <p style="font-size:14px; color:var(--text-gray);">학습된 내용을 바탕으로 실제 매수 대신 모의투자 계좌를 통해 리스크 없이 가설을 테스트합니다.</p>
                    </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:24px; width:100%;">
                    <div style="font-size:14px; color:#111; font-weight:700; width:120px; flex-shrink:0;">Step 04<br><span style="font-size:12px; color:var(--text-light); font-weight:500;">지식의 구조화</span></div>
                    <div>
                        <div style="font-size:16px; font-weight:800; color:#111; margin-bottom:8px;">학습 데이터의 온톨로지(Ontology) 매핑</div>
                        <p style="font-size:14px; color:var(--text-gray); margin-bottom:8px;">이해를 마친 정보는 독립된 지식 노드로 저장되며, 다음 탐색 시 에이전트의 응답 컨텍스트를 고도화하는 재료로 쓰입니다.</p>
                        <span class="chip chip--gray">일회성 상호작용의 종식</span>
                    </div>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">9</span></div>
        </div>
"""

slide_10_part4 = """
        <div class="slide" id="slide-10">
            <div class="center-content">
                <p style="font-weight:800; color:var(--primary-blue); margin-bottom:12px; font-size:18px;">Part 4</p>
                <h2 class="cover-title">미래 비전과 본질</h2>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">10</span></div>
        </div>
"""

slide_11_risk = """
        <!-- SLIDE 11: RISK -->
        <div class="slide" id="slide-11">
            <div class="slide-header">
                <h2 class="slide-header__title">극복 과제: <em>편의성이 부른 통제권 상실의 공포</em></h2>
                <p class="slide-header__subtitle">[Base: Gartner 2028 예측 및 SailPoint 조사 기반 에이전트 도입의 한계]</p>
            </div>
            <div class="rank-grid">
                <div class="rank-grid__header">
                    <div class="rank-grid__header-item">산업 트렌드<span>성장과 융합</span></div>
                    <div class="rank-grid__header-item" style="color:var(--accent-red)">치명적 리스크<span>통제권 상실</span></div>
                    <div class="rank-grid__header-item" style="color:var(--primary-blue)">아델리의 돌파구<span>신뢰 설계</span></div>
                </div>
                <div class="rank-row rank-row--top">
                    <div class="rank-badge">현상</div>
                    <div class="rank-cols">
                        <div class="rank-col">
                            <div class="rank-item">
                                <span class="rank-item-title">앱 내장형 에이전트 확산</span>
                                <span class="rank-item-value diff--up">최단기 확산세</span>
                            </div>
                        </div>
                        <div class="rank-col" style="background:#fffafa;">
                            <div class="rank-item">
                                <span class="rank-item-title">"에이전트가 내 계좌를 비우면?"</span>
                                <span class="rank-item-value diff--down">응답자의 66% 우려</span>
                            </div>
                        </div>
                        <div class="rank-col" style="background:#f5f8ff;">
                            <div class="rank-item">
                                <span class="rank-item-title">Explainable UX</span>
                                <span class="rank-item-value diff--up">결정의 출처와 과정 투명화</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="rank-row">
                    <div class="rank-badge rank-badge--light">결과</div>
                    <div class="rank-cols">
                        <div class="rank-col">
                            <div class="rank-item">
                                <span class="rank-item-title">기존 메뉴 및 기능 대체</span>
                                <span class="rank-item-value">메뉴 없는 자동화 앱의 등장</span>
                            </div>
                        </div>
                        <div class="rank-col" style="background:#fffafa;">
                            <div class="rank-item">
                                <span class="rank-item-title">실제 자산 운용에서의 도입 보류</span>
                                <span class="rank-item-value" style="color:var(--accent-red);">블랙박스형 설계의 한계</span>
                            </div>
                        </div>
                        <div class="rank-col" style="background:#f5f8ff;">
                            <div class="rank-item">
                                <span class="rank-item-title">모의투자 환경 결합</span>
                                <span class="rank-item-value" style="color:var(--primary-blue);">신뢰 확인 전까지의 샌드박스</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div style="margin-top:24px; font-size:15px; font-weight:700; text-align:center; line-height:1.6;">
                강력한 자동화는 금융 도메인에서 필연적으로 '보안과 통제 상실'의 공포를 수반합니다.<br>
                에이전틱 서비스의 안착은 <strong style="color:var(--primary-blue)">유저가 과정을 이해하고 통제할 수 있다고 느끼게 만드는 설계</strong>에 달려 있습니다.
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">11</span></div>
        </div>
"""

slide_12_lessons = """
        <!-- SLIDE 12: LESSONS -->
        <div class="slide" id="slide-12">
            <div class="slide-header">
                <h2 class="slide-header__title">핵심 요약: <em>기능의 대체를 넘어선 가치 질서의 재편</em></h2>
                <p class="slide-header__subtitle">[Base: 프로젝트 최종 관점]</p>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center; flex:1; padding-bottom:40px;">
                <div style="display:flex; gap:40px; margin-top:0; width:100%;">
                    <div style="flex:1; padding-top:20px; border-top:1px solid #111;">
                        <div style="font-size:24px; font-weight:900; color:#111; margin-bottom:16px; line-height: 1;">01.</div>
                        <h3 style="font-size:18px; font-weight:800; margin-bottom:12px; color:#111;">블랙박스가 아닌 투명한 파트너</h3>
                        <p style="font-size:14px; color:var(--text-gray); line-height:1.6;">
                            사용자를 화면 뒤로 밀어내는 완전 자동화 대신, 분석의 과정을 공유하고 <strong>최종 결정의 주도권은 사용자에게 남기는 투명한(Explainable) 설계</strong>가 신뢰의 본질입니다.
                        </p>
                    </div>
                    <div style="flex:1; padding-top:20px; border-top:1px solid #111;">
                        <div style="font-size:24px; font-weight:900; color:#111; margin-bottom:16px; line-height: 1;">02.</div>
                        <h3 style="font-size:18px; font-weight:800; margin-bottom:12px; color:#111;">시간 순이 아닌 맥락 연결</h3>
                        <p style="font-size:14px; color:var(--text-gray); line-height:1.6;">
                            투자 교육은 별도로 존재하는 것이 아니라 행위의 접점에 있어야 합니다. 파편화된 정보를 <strong>나의 포트폴리오(맥락)라는 기준점</strong>에 맞춰 재배열하는 것이 에이전트의 역할입니다.
                        </p>
                    </div>
                    <div style="flex:1; padding-top:20px; border-top:1px solid #111;">
                        <div style="font-size:24px; font-weight:900; color:#111; margin-bottom:16px; line-height: 1;">03.</div>
                        <h3 style="font-size:18px; font-weight:800; margin-bottom:12px; color:#111;">지식이 자산이 되는 플랫폼</h3>
                        <p style="font-size:14px; color:var(--text-gray); line-height:1.6;">
                            일회성 질문응답(Q&A)을 비우고 삭제하는 구조를 탈피해야 합니다. 누적된 상호작용은 사용자의 투자 프로필을 고도화하고, <strong>플랫폼에 Lock-in 시키는 핵심 자산</strong>이 됩니다.
                        </p>
                    </div>
                </div>
                <div style="margin-top:60px; text-align:center;">
                    <p style="font-size:18px; font-weight:500; color:var(--text-gray);">"얼마나 똑똑하게 '알아서' 해주느냐가 경쟁력이 아닙니다.</p>
                    <p style="font-size:26px; font-weight:800; color:#111; margin-top:8px;">자신의 주도권 안에서 <strong style="color:var(--primary-blue)">투자자를 더 영리하고 통제 가능한 주체로 만들어 주는 것.</strong>"</p>
                </div>
            </div>
            <div class="slide-footer"><span class="slide-footer__logo">adelie</span> <span class="slide-footer__page">12</span></div>
        </div>
"""

html_tail = """
    </div> <!-- End Container -->

    <!-- Navigation Hint -->
    <div class="nav-hint">좌우 방향키(← →)로 이동하세요</div>

    <script>
        const slides = document.querySelectorAll('.slide');
        let currentSlide = 0;

        function showSlide(index) {
            slides.forEach(s => {
                s.classList.remove('active');
                s.style.opacity = '0';
            });
            if (slides[index]) {
                slides[index].classList.add('active');
                setTimeout(() => slides[index].style.opacity = '1', 50);
            }
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' || e.key === ' ') {
                if (currentSlide < slides.length - 1) {
                    currentSlide++;
                    showSlide(currentSlide);
                }
            } else if (e.key === 'ArrowLeft') {
                if (currentSlide > 0) {
                    currentSlide--;
                    showSlide(currentSlide);
                }
            }
        });

        // Click to advance
        document.querySelector('.presentation-container').addEventListener('click', (e) => {
            const x = e.clientX;
            const width = window.innerWidth;
            if (x > width / 2 && currentSlide < slides.length - 1) {
                currentSlide++;
                showSlide(currentSlide);
            } else if (x <= width / 2 && currentSlide > 0) {
                currentSlide--;
                showSlide(currentSlide);
            }
        });

        showSlide(0);
    </script>
</body>
</html>
"""

full_html = (
    html_head + slide_0_cover + slide_1_toc + slide_2_part1 + slide_3_target_dilemma +
    slide_4_failure + slide_5_part2 + slide_6_vibe + slide_7_structure + slide_8_part3 +
    slide_9_flow + slide_10_part4 + slide_11_risk + slide_12_lessons + html_tail
)

with open('index_v2.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print("index_v2.html created successfully.")
