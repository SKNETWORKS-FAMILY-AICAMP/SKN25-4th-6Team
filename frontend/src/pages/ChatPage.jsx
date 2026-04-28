import { useState, useRef, useEffect } from 'react';
import useUserStore from '../store/userStore';
import { addMessage, createSession, deleteSession, getSessionDetail, getSessions, sendMessage } from '../api/client';
import raichuImg from '../assets/raichu.png';

const QUICK_SEARCHES = [
  '해외여행자용 카드',
  '쇼핑 할인 많은 카드',
  '주유비 할인 카드',
  '연회비 싼 카드',
];

const INITIAL_MSG = {
  id: 1,
  role: 'assistant',
  text: `안녕하세요! 저는 RAIchU예요 ⚡\n맞춤 카드 추천과 혜택 질문을 도와드릴게요.\n무엇이 궁금하신가요?`,
};

export default function ChatPage({ onGoMyPage }) {
  const profile = useUserStore((s) => s.profile);
  const [messages, setMessages] = useState([INITIAL_MSG]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    getSessions()
      .then((res) => setSessions(res.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendChat = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = { id: Date.now(), role: 'user', text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    let sessionId = currentSessionId;

    try {
      if (!sessionId) {
        const title = text.length > 22 ? text.slice(0, 22) + '…' : text;
        const res = await createSession(title);
        sessionId = res.data.id;
        setCurrentSessionId(sessionId);
        setSessions((prev) => [{ id: sessionId, title: res.data.title }, ...prev]);
      }

      await addMessage(sessionId, 'user', text);

      const history = newMessages.map((m) => ({ role: m.role, content: m.text }));
      const response = await sendMessage({
        message: text,
        history,
        profile: {
          age_group: profile.age_group || '',
          has_car: profile.has_car ?? null,
          lifestyles: profile.lifestyles || [],
          preferred_benefits: profile.preferred_benefits || [],
          monthly_spend: profile.monthly_spend || '',
          annual_fee_range: profile.annual_fee_range || '',
          owned_cards: profile.owned_cards || [],
        },
      });

      const answerText = response.data.answer;
      await addMessage(sessionId, 'assistant', answerText);
      setMessages([...newMessages, { id: Date.now() + 1, role: 'assistant', text: answerText }]);
    } catch {
      setMessages([
        ...newMessages,
        {
          id: Date.now() + 1,
          role: 'assistant',
          text: '오류가 발생했어요. 백엔드 서버가 실행 중인지 확인해주세요.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const removeSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([INITIAL_MSG]);
      }
    } catch {}
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat(input);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F5F4F0]">

      {/* ── 사이드바 ── */}
      <aside className="w-[240px] min-w-[240px] bg-[#1A1A1A] text-white flex flex-col px-5 py-8 relative overflow-hidden">
        <div className="absolute -top-1/2 -left-1/3 w-[200%] h-[200%] pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(245,200,66,0.06) 0%, transparent 60%)' }} />

        <div className="relative z-10 flex flex-col h-full">
          {/* 로고 */}
          <div className="mb-6">
            <div className="text-3xl font-black tracking-tight leading-none" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <span className="text-[#F5C842]">RAI</span>ch<span className="text-[#F5C842]">U</span>
            </div>
            <div className="text-[9px] text-white/25 tracking-widest">v.1.0.0</div>
          </div>

          {/* 새 대화 버튼 */}
          <button
            onClick={() => {
              setCurrentSessionId(null);
              setMessages([INITIAL_MSG]);
            }}
            className="w-full py-2.5 border-2 border-white/20 rounded-xl text-sm font-medium text-white hover:border-[#F5C842] hover:text-[#F5C842] transition-all duration-200 mb-5 cursor-pointer bg-transparent"
          >
            ✏️ 새 대화
          </button>

          {/* 빠른 검색 */}
          <div className="mb-5">
            <div className="text-[10px] text-white/30 tracking-widest mb-2 px-1">빠른 검색</div>
            <div className="flex flex-col gap-1.5">
              {QUICK_SEARCHES.map((q) => (
                <button
                  key={q}
                  onClick={() => sendChat(q)}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs text-white/60 hover:text-white hover:bg-white/[0.07] transition-all duration-200 cursor-pointer bg-transparent border-none"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-white/[0.07] mb-4" />

          {/* 대화내역 */}
          <div className="flex-1 overflow-y-auto">
            <div className="text-[10px] text-white/30 tracking-widest mb-2 px-1">대화내역</div>
            <div className="flex flex-col gap-1">
              {sessions.length === 0 && (
                <div className="px-3 py-2 text-xs text-white/25">대화 내역이 없어요</div>
              )}
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className={`group relative flex items-center rounded-lg transition-all duration-200
                    ${s.id === currentSessionId ? 'bg-white/[0.12]' : 'hover:bg-white/[0.07]'}`}
                >
                  <button
                    onClick={async () => {
                      setCurrentSessionId(s.id);
                      try {
                        const res = await getSessionDetail(s.id);
                        setMessages([INITIAL_MSG, ...res.data.messages]);
                      } catch {
                        setMessages([INITIAL_MSG]);
                      }
                    }}
                    className={`flex-1 text-left px-3 py-2 text-xs cursor-pointer bg-transparent border-none truncate pr-7
                      ${s.id === currentSessionId ? 'text-white' : 'text-white/50 group-hover:text-white'}`}
                  >
                    {s.title}
                  </button>
                  <button
                    onClick={(e) => removeSession(e, s.id)}
                    className="absolute right-1.5 opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center text-white/40 hover:text-red-400 cursor-pointer bg-transparent border-none transition-all duration-150 text-xs rounded"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* My Page 버튼 */}
          <button
            onClick={onGoMyPage}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 text-sm text-white/60 hover:text-white hover:border-[#F5C842]/50 hover:bg-[#F5C842]/5 transition-all duration-200 cursor-pointer bg-transparent mt-4"
          >
            <span>💳</span>
            <span>My Page</span>
          </button>
        </div>
      </aside>

      {/* ── 채팅 메인 ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto px-12 py-8">
          <div className="max-w-[700px] mx-auto flex flex-col gap-5">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden
                  ${msg.role === 'user' ? 'bg-[#E5E5E0] text-xl' : 'bg-[#F5C842]'}`}
                >
                  {msg.role === 'user'
                    ? (profile.avatar || '👤')
                    : <img src={raichuImg} alt="RAIchU" className="w-full h-full object-cover" />
                  }
                </div>
                <div className={`max-w-[75%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
                  ${msg.role === 'user'
                    ? 'bg-white text-[#1A1A1A] rounded-tr-sm shadow-sm'
                    : 'bg-white text-[#1A1A1A] rounded-tl-sm shadow-sm'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-[#F5C842] flex items-center justify-center overflow-hidden">
                  <img src={raichuImg} alt="RAIchU" className="w-full h-full object-cover" />
                </div>
                <div className="bg-white rounded-2xl rounded-tl-sm px-5 py-3.5 shadow-sm">
                  <div className="flex gap-1.5 items-center h-5">
                    <span className="w-2 h-2 bg-[#F5C842] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-[#F5C842] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-[#F5C842] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 입력창 */}
        <div className="px-12 py-5 border-t border-[#E5E5E0] bg-[#F5F4F0]">
          <div className="max-w-[700px] mx-auto flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="궁금한 점이 있다면 입력하세요."
              className="flex-1 px-5 py-3.5 rounded-xl border-2 border-[#E5E5E0] bg-white text-sm text-[#1A1A1A] placeholder:text-[#999] outline-none focus:border-[#F5C842] transition-all duration-200"
            />
            <button
              onClick={() => sendChat(input)}
              disabled={!input.trim() || isLoading}
              className="px-6 py-3.5 bg-[#F5C842] hover:bg-[#E0AD20] disabled:opacity-40 disabled:cursor-not-allowed text-[#1A1A1A] font-bold text-sm rounded-xl border-none cursor-pointer transition-all duration-200"
            >
              입력
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
