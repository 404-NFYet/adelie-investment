/**
 * Companies.jsx - 관련 기업 화면 (핵심 플레이어들)
 * 역할별 기업 카드 목록 + 매수 기능
 */
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AppHeader from '../components/layout/AppHeader';
import { useUser } from '../contexts';
import { casesApi } from '../api';
import { PenguinMascot, TradeModal } from '../components';

// 역할별 스타일 매핑
const ROLE_STYLES = {
  leader: { label: '대장주', badgeClass: 'badge-primary' },
  equipment: { label: '장비주', badgeClass: 'badge-info' },
  potential: { label: '잠룡', badgeClass: 'badge-success' },
};

export default function Companies() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get('caseId') || '';
  const { addToHistory } = useUser();

  const [companies, setCompanies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tradeModal, setTradeModal] = useState({ isOpen: false, stock: null, type: 'buy' });
  const [traded, setTraded] = useState(false);

  useEffect(() => {
    const fetchCompanies = async () => {
      if (!caseId) {
        setError('케이스 ID가 없습니다.');
        setIsLoading(false);
        return;
      }
      try {
        setIsLoading(true);
        setError(null);
        const data = await casesApi.getCompanies(caseId);
        const mapped = (data.related_companies || data.companies || []).map((c, idx) => {
          const name = c.stock_name || c.name || '';
          const role = c.relation_type || c.role || 'potential';
          const fullDesc = c.relation_detail || c.description || '';
          return {
            id: c.id || idx + 1,
            name: name,
            code: c.stock_code || c.code || '',
            role: role,
            roleLabel: c.role_label || ROLE_STYLES[role]?.label || role,
            description: role === 'leader' ? '' : fullDesc,
            detail: role === 'leader' ? fullDesc : '',
            initial: c.initial || name.substring(0, 2) || '',
          };
        });
        setCompanies(mapped);
      } catch (err) {
        console.error('기업 데이터 로딩 실패:', err);
        setError('기업 데이터를 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchCompanies();
  }, [caseId]);

  const openTrade = (company) => {
    setTradeModal({
      isOpen: true,
      stock: { stock_code: company.code, stock_name: company.name },
      type: 'buy',
    });
  };

  const handleTradeClose = () => {
    setTradeModal(prev => ({ ...prev, isOpen: false }));
    setTraded(true);
  };

  return (
    <div className="min-h-screen bg-background pb-10">
      <AppHeader showBack title="관련 기업" />

      <main className="container py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold mb-1">핵심 플레이어들</h2>
          <p className="text-sm text-text-secondary">
            분석을 바탕으로 투자할 종목을 선택하세요
          </p>
        </div>

        {isLoading && (
          <div className="flex justify-center py-8">
            <div className="animate-pulse text-secondary">로딩 중...</div>
          </div>
        )}

        {error && (
          <div className="flex justify-center py-8">
            <div className="text-red-500 text-sm">{error}</div>
          </div>
        )}

        {!isLoading && !error && (
          <div className="space-y-4">
            {companies.map((company) => {
              const roleStyle = ROLE_STYLES[company.role] || ROLE_STYLES.leader;
              const isLeader = company.role === 'leader';

              return (
                <div
                  key={company.id}
                  className={`card ${isLeader ? 'border-primary/60 border-2' : ''}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center flex-shrink-0">
                        <span className="text-base font-bold text-primary">
                          {company.initial}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-bold">{company.name}</h3>
                        <span className="text-sm text-text-secondary">{company.code}</span>
                      </div>
                    </div>
                    <span className={`badge ${roleStyle.badgeClass}`}>
                      {company.roleLabel}
                    </span>
                  </div>

                  <p className="text-sm text-text-secondary">{company.description}</p>

                  {isLeader && company.detail && (
                    <p className="text-sm text-text-primary mt-3 leading-relaxed bg-surface rounded-lg p-3">
                      {company.detail}
                    </p>
                  )}

                  {/* 매수 버튼 */}
                  {company.code && (
                    <button
                      onClick={() => openTrade(company)}
                      className="mt-3 w-full py-2.5 rounded-xl text-sm font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors"
                    >
                      매수
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!isLoading && !error && companies.length === 0 && (
          <PenguinMascot variant="empty" message="관련 기업 정보가 없습니다." />
        )}

        {/* 하단 버튼 */}
        <div className="mt-10 mb-8 flex flex-col gap-3 items-center">
          {traded && (
            <button
              onClick={() => navigate('/portfolio')}
              className="btn-primary w-full max-w-xs py-4 rounded-full text-sm font-bold"
            >
              포트폴리오 확인
            </button>
          )}
          <button
            onClick={() => {
              addToHistory({
                id: Date.now(),
                date: new Date().toISOString().slice(0, 10),
                keyword: new URLSearchParams(window.location.search).get('keyword') || '',
                syncRate: 0,
                pastCase: '',
              });
              navigate('/');
            }}
            className={`w-full max-w-xs py-4 rounded-full text-sm font-bold ${traded ? 'bg-surface border border-border text-text-secondary' : 'btn-primary'}`}
          >
            처음으로 돌아가기
          </button>
        </div>
      </main>

      <TradeModal
        isOpen={tradeModal.isOpen}
        onClose={handleTradeClose}
        stock={tradeModal.stock}
        tradeType={tradeModal.type}
        caseId={caseId}
      />
    </div>
  );
}
