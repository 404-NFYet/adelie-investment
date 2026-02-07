/**
 * QueryProvider.jsx - React Query 설정
 * 서버 상태 관리: 브리핑, 포트폴리오, 주가 등의 데이터 캐싱
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5분 동안 fresh 유지
      gcTime: 10 * 60 * 1000,         // 10분 후 가비지 컬렉션
      retry: 2,                        // 2회 재시도
      refetchOnWindowFocus: false,     // 탭 전환 시 자동 refetch 비활성화
    },
  },
});

export default function QueryProvider({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

export { queryClient };
