import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import useUserStore from './store/userStore';
import OnboardingPage from './pages/OnboardingPage';
import ChatPage from './pages/ChatPage';
import MyPage from './pages/MyPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 1000 * 60 * 5 } },
});

function AppContent() {
  const { isOnboarded } = useUserStore();
  const [page, setPage] = useState('chat');

  // 온보딩 미완료 → 온보딩 화면
  if (!isOnboarded) return <OnboardingPage />;

  // 마이페이지
  if (page === 'mypage') {
    return <MyPage onGoChat={() => setPage('chat')} />;
  }

  // 채팅 화면 (기본)
  return <ChatPage onGoMyPage={() => setPage('mypage')} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
