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

function isProfileReady(profile) {
  return Boolean(
    profile?.age_group &&
    profile?.annual_fee_range &&
    profile?.monthly_spend &&
    Array.isArray(profile?.lifestyles) &&
    profile.lifestyles.length > 0 &&
    profile?.has_car !== null
  );
}

function AppContent() {
  const { isOnboarded, hasHydrated, profile } = useUserStore();
  const [showSplash, setShowSplash] = useState(true);
  const [page, setPage] = useState('chat');
  const readyForChat = isOnboarded || isProfileReady(profile);

  if (showSplash) return <SplashScreen onFinish={() => setShowSplash(false)} />;
  if (!hasHydrated) return null;
  if (!readyForChat) return <OnboardingPage />;
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
