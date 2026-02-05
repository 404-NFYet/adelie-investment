/**
 * App.jsx - Main application component
 * Routes and global providers
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UserProvider, useUser } from './contexts/UserContext';
import { TutorProvider } from './contexts/TutorContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { TutorModal, ErrorBoundary, ToastProvider } from './components';
import BottomNav from './components/BottomNav';
import { Onboarding, Home, Comparison, Story, Companies, History, Matching, Auth, Search, Profile } from './pages';

function ProtectedRoute({ children }) {
  const { user, settings } = useUser();
  // 온보딩 완료 또는 토큰 인증된 사용자 허용
  if (!user && !settings.hasCompletedOnboarding) return <Navigate to="/onboarding" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
      <Route path="/search" element={<ProtectedRoute><Search /></ProtectedRoute>} />
      <Route path="/comparison" element={<ProtectedRoute><Comparison /></ProtectedRoute>} />
      <Route path="/story" element={<ProtectedRoute><Story /></ProtectedRoute>} />
      <Route path="/companies" element={<ProtectedRoute><Companies /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="/matching" element={<ProtectedRoute><Matching /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <UserProvider>
          <TutorProvider>
            <ErrorBoundary>
              <ToastProvider>
                <div className="app-container">
                  <AppRoutes />
                  <TutorModal />
                  <BottomNav />
                </div>
              </ToastProvider>
            </ErrorBoundary>
          </TutorProvider>
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
