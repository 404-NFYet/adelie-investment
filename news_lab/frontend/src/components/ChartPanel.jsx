import React, { useMemo } from 'react';

const EMPTY_HTML = '<html><body style="font-family:Pretendard,Noto Sans KR,sans-serif;padding:16px;color:#6b7280;">차트를 아직 생성하지 않았습니다.</body></html>';

export default function ChartPanel({ chartState, onRetry }) {
  const iframeSrc = useMemo(() => chartState?.html || EMPTY_HTML, [chartState?.html]);

  if (chartState?.status === 'unavailable') {
    return (
      <section className="chart-panel">
        <div className="chart-panel-head">
          <h4>시각화</h4>
        </div>
        <div className="chart-unavailable">{chartState?.error || '기사에 수치 근거가 부족해 차트를 생성하지 않습니다.'}</div>
      </section>
    );
  }

  return (
    <section className="chart-panel">
      <div className="chart-panel-head">
        <h4>시각화</h4>
        <button type="button" className="secondary-btn" onClick={onRetry} disabled={chartState?.status === 'loading'}>
          {chartState?.status === 'loading' ? '생성 중...' : '다시 생성'}
        </button>
      </div>

      {chartState?.status === 'error' ? <p className="inline-error">{chartState.error || '차트를 생성하지 못했습니다.'}</p> : null}

      {chartState?.status === 'loading' ? (
        <div className="chart-loading">차트를 생성하고 있습니다...</div>
      ) : (
        <iframe title="news-chart" sandbox="allow-scripts" srcDoc={iframeSrc} className="chart-frame" />
      )}
    </section>
  );
}
