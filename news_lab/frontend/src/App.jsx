import React, { useCallback, useEffect, useRef, useState } from 'react';
import { newsApi } from './api';
import NewsDetailScreen from './components/NewsDetailScreen';
import NewsFeedScreen from './components/NewsFeedScreen';
import TermDrawer from './components/TermDrawer';

const DIFFICULTY_VALUES = new Set(['beginner', 'elementary', 'intermediate']);

function stripMarkup(text) {
  return String(text || '')
    .replace(/<mark\b[^>]*>(.*?)<\/mark>/gis, '$1')
    .replace(/\[\[([^\]]+)\]\]/g, '$1');
}

function buildChartContext(result) {
  if (!result) return '';
  const newsletter = result.newsletter_mode || {};
  const sixW = newsletter.six_w || result.explain_mode?.six_w || {};
  const explainText = stripMarkup(result.explain_mode?.content_marked || '');

  return [
    `제목: ${result.article?.title || ''}`,
    `출처: ${result.article?.source || ''}`,
    `리드: ${newsletter.lede || result.explain_mode?.lede || ''}`,
    `누가: ${sixW.who || ''}`,
    `무엇을: ${sixW.what || ''}`,
    `언제: ${sixW.when || ''}`,
    `어디서: ${sixW.where || ''}`,
    `왜: ${sixW.why || ''}`,
    `어떻게: ${sixW.how || ''}`,
    `배경: ${newsletter.background || ''}`,
    `중요성: ${newsletter.importance || ''}`,
    `핵심개념: ${(newsletter.concepts || []).join(', ')}`,
    `관련이슈: ${(newsletter.related || []).join(', ')}`,
    `핵심정리: ${(newsletter.takeaways || []).join(' | ')}`,
    `설명본문: ${explainText.slice(0, 1800)}`,
  ].join('\n');
}

export default function App() {
  const [screen, setScreen] = useState('feed');

  const [market, setMarket] = useState('KR');
  const [difficulty, setDifficulty] = useState('beginner');

  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState('');
  const [headlines, setHeadlines] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [headlinesLoading, setHeadlinesLoading] = useState(false);

  const [urlInput, setUrlInput] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState('');

  const [result, setResult] = useState(null);
  const [mode, setMode] = useState('explain');

  const [chartState, setChartState] = useState({ status: 'idle', html: '', error: '' });
  const chartRequestSeq = useRef(0);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTerm, setDrawerTerm] = useState('');
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerExplanation, setDrawerExplanation] = useState('');

  useEffect(() => {
    const loadSources = async () => {
      try {
        const data = await newsApi.sources(market);
        const incoming = data.sources || [];
        setSources(incoming);
        setSelectedSource((prev) => {
          if (incoming.some((item) => item.id === prev)) return prev;
          return incoming[0]?.id || '';
        });
      } catch (_e) {
        setSources([]);
        setSelectedSource('');
      }
    };

    loadSources();
  }, [market]);

  useEffect(() => {
    const loadHeadlines = async () => {
      setHeadlinesLoading(true);
      try {
        const data = await newsApi.headlines({ market, sourceId: selectedSource || undefined, limit: 20 });
        setHeadlines(data.headlines || []);
        setWarnings(data.warnings || []);
      } catch (e) {
        setHeadlines([]);
        setWarnings([{ source_id: selectedSource || market, message: e.message }]);
      } finally {
        setHeadlinesLoading(false);
      }
    };

    loadHeadlines();
  }, [market, selectedSource]);

  const generateChart = useCallback(async (analysis) => {
    if (!analysis) {
      setChartState({ status: 'error', html: '', error: '먼저 기사를 분석해주세요.' });
      return;
    }

    if (!analysis.chart_ready) {
      setChartState({
        status: 'unavailable',
        html: '',
        error: analysis.chart_unavailable_reason || '기사에서 수치 근거를 찾지 못해 차트를 생성하지 않습니다.',
      });
      return;
    }

    const seq = ++chartRequestSeq.current;
    const dataContext = buildChartContext(analysis);

    setChartState({ status: 'loading', html: '', error: '' });

    try {
      const response = await newsApi.visualize({
        description: `${analysis.article?.title || '뉴스'} 관련 핵심 지표를 요약 차트로 보여주세요.`,
        dataContext,
      });

      if (seq !== chartRequestSeq.current) return;

      if (!response?.html) {
        setChartState({ status: 'error', html: '', error: response?.error || '차트를 생성하지 못했습니다.' });
        return;
      }

      setChartState({ status: 'ready', html: response.html, error: '' });
    } catch (e) {
      if (seq !== chartRequestSeq.current) return;
      setChartState({ status: 'error', html: '', error: e.message || '차트를 생성하지 못했습니다.' });
    }
  }, []);

  const handleAnalyze = async (targetUrl) => {
    const url = String(targetUrl || urlInput || '').trim();
    if (!url) {
      setAnalyzeError('분석할 URL을 입력해주세요.');
      return;
    }

    setAnalyzing(true);
    setAnalyzeError('');

    try {
      const data = await newsApi.analyze({ url, difficulty, market });
      setResult(data);
      setMode('explain');
      setUrlInput(url);
      setScreen('detail');
      void generateChart(data);
    } catch (e) {
      setAnalyzeError(String(e.message || '분석에 실패했습니다.'));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClickTerm = async (term) => {
    const safeDifficulty = DIFFICULTY_VALUES.has(difficulty) ? difficulty : 'beginner';
    setDrawerTerm(term);
    setDrawerOpen(true);
    setDrawerLoading(true);
    setDrawerExplanation('');

    try {
      const data = await newsApi.explainTerm({ term, difficulty: safeDifficulty });
      setDrawerExplanation(data.explanation || '설명을 찾을 수 없습니다.');
    } catch (_e) {
      setDrawerExplanation('설명을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setDrawerLoading(false);
    }
  };

  return (
    <div className="news-lab-root">
      <div className="mobile-shell">
        <div className="brand-strip">
          <div className="brand-logo" aria-hidden="true">&#128039;</div>
          <strong>Adelie</strong>
        </div>

        <div className="shell-content">
          {screen === 'feed' ? (
            <NewsFeedScreen
              market={market}
              setMarket={setMarket}
              difficulty={difficulty}
              setDifficulty={setDifficulty}
              sources={sources}
              selectedSource={selectedSource}
              onSelectSource={setSelectedSource}
              headlines={headlines}
              warnings={warnings}
              loading={headlinesLoading}
              urlInput={urlInput}
              setUrlInput={setUrlInput}
              onAnalyze={handleAnalyze}
              analyzing={analyzing}
              analyzeError={analyzeError}
            />
          ) : (
            <NewsDetailScreen
              result={result}
              mode={mode}
              onChangeMode={setMode}
              onBack={() => setScreen('feed')}
              onClickTerm={handleClickTerm}
              chartState={chartState}
              onRetryChart={() => generateChart(result)}
            />
          )}
        </div>
      </div>

      <TermDrawer
        open={drawerOpen}
        term={drawerTerm}
        loading={drawerLoading}
        explanation={drawerExplanation}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
