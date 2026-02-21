/**
 * App.jsx - Main application component
 * 코드 스플리팅 적용 (React.lazy + Suspense)
 */
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { UserProvider, useUser } from './contexts/UserContext';
import { PortfolioProvider } from './contexts/PortfolioContext';
import { TutorProvider } from './contexts/TutorContext';
import { TermProvider } from './contexts/TermContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { TutorModal, ErrorBoundary, ToastProvider } from './components';
import TermBottomSheet from './components/domain/TermBottomSheet';
import BottomNav from './components/layout/BottomNav';
import AgentDock from './components/agent/AgentDock';
import PenguinLoading from './components/common/PenguinLoading';
import UpdatePrompt from './components/common/UpdatePrompt';

// 코드 스플리팅: 각 페이지를 동적 import
const Auth = lazy(() => import('./pages/Auth'));
const Landing = lazy(() => import('./pages/Landing'));
const Home = lazy(() => import('./pages/Home'));
const Education = lazy(() => import('./pages/Education'));
const ActivityArchive = lazy(() => import('./pages/ActivityArchive'));
const Search = lazy(() => import('./pages/Search'));
const Comparison = lazy(() => import('./pages/Comparison'));
const Story = lazy(() => import('./pages/Story'));
const Companies = lazy(() => import('./pages/Companies'));
const History = lazy(() => import('./pages/History'));
const Narrative = lazy(() => import('./pages/Narrative'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Profile = lazy(() => import('./pages/Profile'));
const TutorChat = lazy(() => import('./pages/TutorChat'));
const AgentCanvasPage = lazy(() => import('./pages/AgentCanvasPage'));
const AgentHistoryPage = lazy(() => import('./pages/AgentHistoryPage'));

function CaseRedirect() {
  const { caseId } = useParams();
  if (!caseId) return <Navigate to="/search" replace />;
  return <Navigate to={`/narrative/${caseId}`} replace />;
}

function ProtectedRoute({ children }) {
  const { user, isLoading } = useUser();
  if (isLoading) return <PageLoader />;
  if (!user?.isAuthenticated) return <Navigate to="/" replace />;
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
        <Route path="/" element={<Landing />} />
        <Route path="/landing" element={<Navigate to="/" replace />} />
        <Route path="/onboarding" element={<Navigate to="/" replace />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/education" element={<ProtectedRoute><Education /></ProtectedRoute>} />
        <Route path="/education/archive" element={<ProtectedRoute><ActivityArchive /></ProtectedRoute>} />
        <Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} />
        <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
        <Route path="/comparison" element={<ProtectedRoute><Comparison /></ProtectedRoute>} />
        <Route path="/story" element={<ProtectedRoute><Story /></ProtectedRoute>} />
        <Route path="/companies" element={<ProtectedRoute><Companies /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/case/:caseId" element={<ProtectedRoute><CaseRedirect /></ProtectedRoute>} />
        <Route path="/narrative/:caseId" element={<ProtectedRoute><Narrative /></ProtectedRoute>} />
        <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute><Portfolio /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/tutor" element={<ProtectedRoute><TutorChat /></ProtectedRoute>} />
        <Route path="/agent" element={<ProtectedRoute><AgentCanvasPage /></ProtectedRoute>} />
        <Route path="/agent/history" element={<ProtectedRoute><AgentHistoryPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
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
                    <AgentDock />
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
