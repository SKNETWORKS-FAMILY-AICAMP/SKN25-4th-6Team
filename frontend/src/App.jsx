import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import useUserStore from './store/userStore';
import OnboardingPage from './pages/OnboardingPage';

// TanStack Query 클라이언트
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5분
    },
  },
});

function AppContent() {
  const isOnboarded = useUserStore((s) => s.isOnboarded);

  // 온보딩 완료 전 → OnboardingPage
  if (!isOnboarded) return <OnboardingPage />;

  // 온보딩 완료 후 → 추후 ChatPage / MyPage 추가 예정
  return (
    <div className="flex items-center justify-center h-screen bg-[#F5F4F0]">
      <div className="text-center">
        <div className="text-5xl mb-4">⚡</div>
        <h2 className="text-2xl font-bold text-[#1A1A1A] mb-2">ChatPage 준비 중</h2>
        <p className="text-sm text-[#999]">곧 챗봇 화면이 연결될 예정이에요</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
