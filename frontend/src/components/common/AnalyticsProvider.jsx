/**
 * AnalyticsProvider - 분석 SDK 초기화 + 자동 페이지뷰 추적
 *
 * UserProvider 안, PortfolioProvider 위에 배치.
 * - 1회 초기화: Clarity + PostHog SDK
 * - 유저 변경: identify / reset
 * - 라우트 변경: 자동 페이지뷰
 */
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useUser } from '../../contexts/UserContext';
import {
  initClarity,
  initPostHog,
  identifyUser,
  resetUser,
} from '../../utils/analyticsProviders';
import { trackPageView } from '../../utils/analytics';

export default function AnalyticsProvider({ children }) {
  const { user } = useUser();
  const location = useLocation();

  // SDK 초기화 (1회)
  useEffect(() => {
    initClarity();
    initPostHog();
  }, []);

  // 유저 식별 (로그인/로그아웃)
  useEffect(() => {
    if (user?.isAuthenticated) {
      identifyUser(user);
    } else {
      resetUser();
    }
  }, [user]);

  // SPA 라우트 변경 → 자동 페이지뷰
  useEffect(() => {
    trackPageView(location.pathname);
  }, [location.pathname]);

  return children;
}
