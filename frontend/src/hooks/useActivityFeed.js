import { useCallback, useEffect, useMemo, useState } from 'react';
import { learningApi, portfolioApi } from '../api';
import { formatKRW } from '../utils/formatNumber';
import { formatDateKeyKST, formatTimeKST } from '../utils/kstDate';

const LEARNING_STATUS_LABEL = {
  completed: '완료',
  in_progress: '진행중',
  viewed: '열람',
};

const LEARNING_TYPE_LABEL = {
  case: '내러티브',
  glossary: '용어',
  briefing: '브리핑',
};

function normalizeTradeItem(trade) {
  const tradeTypeLabel = trade.trade_type === 'buy' ? '매수' : '매도';
  const occurredAt = trade.traded_at;
  const stockName = trade.stock_name || trade.stock_code || '종목';

  return {
    id: `trade-${trade.id}`,
    type: 'trade',
    occurredAt,
    dateKey: formatDateKeyKST(occurredAt),
    timeLabel: formatTimeKST(occurredAt),
    title: `${tradeTypeLabel} ${stockName}`,
    subtitle: `${trade.quantity}주 · ${formatKRW(trade.total_amount || 0)}`,
    meta: {
      stockCode: trade.stock_code,
      tradeType: trade.trade_type,
      price: trade.price,
    },
  };
}

function normalizeLearningItem(item) {
  const occurredAt = item.completed_at || item.started_at;
  const typeLabel = LEARNING_TYPE_LABEL[item.content_type] || '학습';
  const statusLabel = LEARNING_STATUS_LABEL[item.status] || '기록';
  const progressPercent = Number(item.progress_percent || 0);

  return {
    id: `learning-${item.id}`,
    type: 'learning',
    occurredAt,
    dateKey: formatDateKeyKST(occurredAt),
    timeLabel: formatTimeKST(occurredAt),
    title: `${typeLabel} 학습 #${item.content_id} ${statusLabel}`,
    subtitle: `진행률 ${progressPercent}%`,
    meta: {
      contentType: item.content_type,
      contentId: item.content_id,
      status: item.status,
      progressPercent: progressPercent,
    },
  };
}

export default function useActivityFeed() {
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 각 API 호출을 개별적으로 에러 처리하여 한쪽 실패 시에도 다른 데이터 표시
      const [tradeResult, learningResult] = await Promise.allSettled([
        portfolioApi.getTradeHistory(100),
        learningApi.getProgress(),
      ]);

      const tradeRes = tradeResult.status === 'fulfilled' ? tradeResult.value : null;
      const learningRes = learningResult.status === 'fulfilled' ? learningResult.value : null;

      const tradeItems = Array.isArray(tradeRes?.trades)
        ? tradeRes.trades.map(normalizeTradeItem)
        : [];

      const learningItems = Array.isArray(learningRes?.data)
        ? learningRes.data
          .filter((item) => item?.content_type === 'case')
          .map(normalizeLearningItem)
        : [];

      const merged = [...tradeItems, ...learningItems]
        .filter((item) => item.occurredAt)
        .sort((a, b) => new Date(b.occurredAt).getTime() - new Date(a.occurredAt).getTime());

      setActivities(merged);

      // 양쪽 모두 실패한 경우에만 에러 표시
      if (tradeResult.status === 'rejected' && learningResult.status === 'rejected') {
        setError('활동 내역을 불러오지 못했습니다.');
      }
    } catch (fetchError) {
      setActivities([]);
      setError(fetchError?.message || '활동 내역을 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const activitiesByDate = useMemo(() => {
    return activities.reduce((acc, item) => {
      if (!acc[item.dateKey]) acc[item.dateKey] = [];
      acc[item.dateKey].push(item);
      return acc;
    }, {});
  }, [activities]);

  return {
    activities,
    activitiesByDate,
    isLoading,
    error,
    refetch,
  };
}
