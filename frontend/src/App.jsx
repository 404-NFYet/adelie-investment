/**
 * App.jsx - Main application component
 * 코드 스플리팅 적용 (React.lazy + Suspense)
 */
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UserProvider, useUser } from './contexts/UserContext';
import { PortfolioProvider } from './contexts/PortfolioContext';
import { TutorProvider } from './contexts/TutorContext';
import { TermProvider } from './contexts/TermContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { TutorModal, ErrorBoundary, ToastProvider } from './components';
import TermBottomSheet from './components/domain/TermBottomSheet';
import ChatFAB from './components/layout/ChatFAB';
import BottomNav from './components/layout/BottomNav';
import PenguinLoading from './components/common/PenguinLoading';
import UpdatePrompt from './components/common/UpdatePrompt';

// 코드 스플리팅: 각 페이지를 동적 import
const Auth = lazy(() => import('./pages/Auth'));
const Landing = lazy(() => import('./pages/Landing'));
const Home = lazy(() => import('./pages/Home'));
const Content = lazy(() => import('./pages/Content'));
const Search = lazy(() => import('./pages/Search'));
const Comparison = lazy(() => import('./pages/Comparison'));
const Story = lazy(() => import('./pages/Story'));
const Companies = lazy(() => import('./pages/Companies'));
const History = lazy(() => import('./pages/History'));
const Matching = lazy(() => import('./pages/Matching'));
const Narrative = lazy(() => import('./pages/Narrative'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Profile = lazy(() => import('./pages/Profile'));
const TutorChat = lazy(() => import('./pages/TutorChat'));

function ProtectedRoute({ children }) {
  const { user, isLoading } = useUser();
  if (isLoading) return <PageLoader />;
  if (!user?.isAuthenticated) return <Navigate to="/auth" replace />;
  return children;
}

function PageLoader() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <PenguinLoading size="sm" />
    </div>
  );
}

function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/landing" element={<Landing />} />
        <Route path="/onboarding" element={<Navigate to="/landing" replace />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/" element={<Home />} />
        <Route path="/content/:caseId" element={<Content />} />
        <Route path="/search" element={<Search />} />
        <Route path="/comparison" element={<Comparison />} />
        <Route path="/story" element={<Story />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/history" element={<History />} />
        <Route path="/case/:caseId" element={<Matching />} />
        <Route path="/narrative/:caseId" element={<Narrative />} />
        <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/tutor" element={<ProtectedRoute><TutorChat /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/landing" replace />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <UserProvider>
          <PortfolioProvider>
          <TutorProvider>
            <TermProvider>
              <ErrorBoundary>
                <ToastProvider>
                  <div className="app-container">
                    <UpdatePrompt />
                    <AppRoutes />
                    <TermBottomSheet />
                    <TutorModal />
                    <ChatFAB />
                    <BottomNav />
                  </div>
                </ToastProvider>
              </ErrorBoundary>
            </TermProvider>
          </TutorProvider>
          </PortfolioProvider>
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
