import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import useUserStore from './store/userStore';
import SplashScreen from './pages/SplashScreen';
import OnboardingPage from './pages/OnboardingPage';
import ChatPage from './pages/ChatPage';
import MyPage from './pages/MyPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 1000 * 60 * 5 } },
});

function AppContent() {
  const { isOnboarded } = useUserStore();
  const [showSplash, setShowSplash] = useState(true);
  const [page, setPage] = useState('chat');

  if (showSplash) return <SplashScreen onFinish={() => setShowSplash(false)} />;
  if (!isOnboarded) return <OnboardingPage />;
  if (page === 'mypage') return <MyPage onGoChat={() => setPage('chat')} />;
  return <ChatPage onGoMyPage={() => setPage('mypage')} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
