import { useEffect, useState } from 'react';
import { getCards } from '../api/client';
import useUserStore from '../store/userStore';

// 각 필드의 선택지 정의
const FIELD_OPTIONS = {
  age_group: ['20대', '30대', '40대', '50대 이상'],
  has_car: [true, false],
  monthly_spend: ['30만원 미만', '30~70만원', '70~150만원', '150만원 이상'],
  annual_fee_range: ['없음 선호', '3만원 이하', '5만원 이상도 OK'],
  preferred_benefits: ['즉시할인', '포인트적립', '마일리지', '캐시백'],
  lifestyles: ['카라이프', '여행러', '카페인중독', '디지털노마드', '헬스·건강', '가족중심', '배달·외식', '문화생활', '쇼핑'],
};

const PROFILE_ITEMS = [
  { key: 'age_group',          label: '나이대',      icon: '🎂' },
  { key: 'has_car',            label: '자동차',      icon: '🚗' },
  { key: 'monthly_spend',      label: '월 사용액',   icon: '💳' },
  { key: 'annual_fee_range',   label: '연회비 허용', icon: '💰' },
  { key: 'preferred_benefits', label: '선호 혜택',   icon: '🎯' },
  { key: 'lifestyles',         label: '라이프스타일', icon: '✨' },
];

const formatValue = (key, value) => {
  if (value === null || value === undefined || value === '') return '미입력';
  if (key === 'has_car') return value ? '있음' : '없음';
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '미입력';
  return value;
};

// 개별 프로필 항목 카드
function ProfileCard({ item, value, onSave }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value);
  const options = FIELD_OPTIONS[item.key];
  const isMulti = Array.isArray(value) || item.key === 'preferred_benefits' || item.key === 'lifestyles';
  const isBool = item.key === 'has_car';

  const handleToggleMulti = (opt) => {
    const arr = Array.isArray(draft) ? draft : [];
    if (arr.includes(opt)) {
      setDraft(arr.filter(v => v !== opt));
    } else {
      if (item.key === 'lifestyles' && arr.length >= 3) {
        setDraft([...arr.slice(1), opt]);
      } else {
        setDraft([...arr, opt]);
      }
    }
  };

  const handleSave = () => {
    onSave(item.key, draft);
    setOpen(false);
  };

  const handleOpen = () => {
    setDraft(value);
    setOpen(!open);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden border-2 transition-all duration-200"
      style={{ borderColor: open ? '#F5C842' : 'transparent' }}>
      {/* 항목 헤더 - 클릭하면 열림 */}
      <div
        className="px-4 py-3 cursor-pointer hover:bg-[#FFFBEB] transition-colors duration-150"
        onClick={handleOpen}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{item.icon}</span>
            <span className="text-xs font-semibold text-[#999]">{item.label}</span>
          </div>
          <span className="text-xs text-[#999]">{open ? '▲' : '▼'}</span>
        </div>
        <div className="text-sm font-medium text-[#1A1A1A] truncate">
          {formatValue(item.key, value)}
        </div>
      </div>

      {/* 수정 패널 */}
      {open && (
        <div className="px-4 pb-4 border-t border-[#F5F4F0]">
          <div className="pt-3 flex flex-wrap gap-2 mb-3">
            {isBool ? (
              <>
                {[true, false].map(opt => (
                  <button
                    key={String(opt)}
                    onClick={() => setDraft(opt)}
                    className={`px-4 py-2 rounded-full text-xs font-medium border-2 cursor-pointer transition-all duration-150
                      ${draft === opt
                        ? 'bg-[#F5C842] border-[#F5C842] text-[#1A1A1A] font-semibold'
                        : 'border-[#E5E5E0] text-[#555] hover:border-[#F5C842] hover:bg-[#FFFBEB]'
                      }`}
                  >
                    {opt ? '🚗 있음' : '🚶 없음'}
                  </button>
                ))}
              </>
            ) : isMulti ? (
              options.map(opt => {
                const arr = Array.isArray(draft) ? draft : [];
                const selected = arr.includes(opt);
                return (
                  <button
                    key={opt}
                    onClick={() => handleToggleMulti(opt)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border-2 cursor-pointer transition-all duration-150
                      ${selected
                        ? 'bg-[#F5C842] border-[#F5C842] text-[#1A1A1A] font-semibold'
                        : 'border-[#E5E5E0] text-[#555] hover:border-[#F5C842] hover:bg-[#FFFBEB]'
                      }`}
                  >
                    {opt}
                  </button>
                );
              })
            ) : (
              options.map(opt => (
                <button
                  key={opt}
                  onClick={() => setDraft(opt)}
                  className={`px-4 py-2 rounded-full text-xs font-medium border-2 cursor-pointer transition-all duration-150
                    ${draft === opt
                      ? 'bg-[#F5C842] border-[#F5C842] text-[#1A1A1A] font-semibold'
                      : 'border-[#E5E5E0] text-[#555] hover:border-[#F5C842] hover:bg-[#FFFBEB]'
                    }`}
                >
                  {opt}
                </button>
              ))
            )}
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setOpen(false)}
              className="px-4 py-1.5 text-xs text-[#999] border border-[#E5E5E0] rounded-lg cursor-pointer bg-transparent hover:bg-[#F5F4F0]"
            >
              취소
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 text-xs font-bold text-[#1A1A1A] bg-[#F5C842] hover:bg-[#E0AD20] rounded-lg border-none cursor-pointer transition-all duration-150"
            >
              저장
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const AVATAR_OPTIONS = ['🧑‍💻', '👤', '😊', '😎', '🦸', '🎩', '🐱', '🦊', '🌟', '🧑‍🎤'];

export default function MyPage({ onGoChat }) {
  const { profile, updateProfile } = useUserStore();
  const [cardSearch, setCardSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [cardOptions, setCardOptions] = useState([]);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);

  useEffect(() => {
    getCards()
      .then(res => setCardOptions(res.data.cards ?? []))
      .catch(() => setCardOptions([]));
  }, []);

  const ownedCards = profile.owned_cards || [];

  const filteredOptions = cardOptions.filter((c) => {
    const q = cardSearch.toLowerCase();
    return (
      (c.name.toLowerCase().includes(q) || c.company.toLowerCase().includes(q)) &&
      !ownedCards.some((o) => o.card_id === c.card_id)
    );
  });

  const addCard = (card) => {
    updateProfile({ owned_cards: [...ownedCards, { name: card.name, company: card.company, card_id: card.card_id }] });
    setCardSearch('');
    setShowDropdown(false);
  };

  const removeCard = (card_id) => {
    updateProfile({ owned_cards: ownedCards.filter((c) => c.card_id !== card_id) });
  };

  const handleSaveField = (key, value) => {
    updateProfile({ [key]: value });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F5F4F0]">
      {/* 사이드바 */}
      <aside className="w-[240px] min-w-[240px] bg-[#1A1A1A] text-white flex flex-col px-5 py-8 relative overflow-hidden">
        <div className="absolute -top-1/2 -left-1/3 w-[200%] h-[200%] pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(245,200,66,0.06) 0%, transparent 60%)' }} />
        <div className="relative z-10 flex flex-col h-full">
          <div className="mb-8">
            <div className="text-3xl font-black tracking-tight leading-none" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <span className="text-[#F5C842]">RAI</span>ch<span className="text-[#F5C842]">U</span>
            </div>
            <div className="text-[9px] text-white/25 tracking-widest">v.1.0.0</div>
          </div>
          <button
            onClick={onGoChat}
            className="w-full py-2.5 border-2 border-white/20 rounded-xl text-sm font-medium text-white hover:border-[#F5C842] hover:text-[#F5C842] transition-all duration-200 mb-5 cursor-pointer bg-transparent"
          >
            ✏️ 새 대화
          </button>
          <div className="flex-1" />
          <button className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-[#F5C842]/50 bg-[#F5C842]/10 text-sm text-[#F5C842] font-semibold cursor-default mt-4">
            <span>💳</span><span>My Page</span>
          </button>
        </div>
      </aside>

      {/* 메인 */}
      <main className="flex-1 overflow-y-auto px-12 py-10">
        <div className="max-w-[760px] mx-auto">

          {/* MY PROFILE */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-[#1A1A1A]">MY PROFILE</h2>
              <span className="text-xs text-[#999]">항목을 클릭해서 수정하세요</span>
            </div>

            <div className="flex items-start gap-5">
              <div className="relative flex-shrink-0">
                <div
                  onClick={() => setShowAvatarPicker(v => !v)}
                  className="w-16 h-16 rounded-full bg-[#E5E5E0] flex items-center justify-center text-3xl cursor-pointer hover:ring-2 hover:ring-[#F5C842] transition-all"
                >
                  {profile.avatar || '🧑‍💻'}
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#F5C842] rounded-full flex items-center justify-center text-[10px] font-bold text-[#1A1A1A] pointer-events-none">✏️</div>
                {showAvatarPicker && (
                  <div className="absolute top-full left-0 mt-2 bg-white rounded-xl shadow-lg border border-[#E5E5E0] p-2 z-20 grid grid-cols-4 gap-1 w-40">
                    {AVATAR_OPTIONS.map(emoji => (
                      <button
                        key={emoji}
                        onClick={() => { updateProfile({ avatar: emoji }); setShowAvatarPicker(false); }}
                        className={`w-9 h-9 rounded-lg text-xl flex items-center justify-center cursor-pointer border-2 transition-all bg-transparent
                          ${profile.avatar === emoji ? 'border-[#F5C842] bg-[#FFFBEB]' : 'border-transparent hover:bg-[#F5F4F0]'}`}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex-1 grid grid-cols-2 gap-3">
                {PROFILE_ITEMS.map((item) => (
                  <ProfileCard
                    key={item.key}
                    item={item}
                    value={profile[item.key]}
                    onSave={handleSaveField}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* MY CARD */}
          <div>
            <h2 className="text-xl font-bold text-[#1A1A1A] mb-2">MY CARD</h2>
            <p className="text-sm text-[#999] mb-4">보유 중인 카드</p>

            <div className="relative mb-5">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={cardSearch}
                  onChange={(e) => { setCardSearch(e.target.value); setShowDropdown(true); }}
                  onFocus={() => setShowDropdown(true)}
                  placeholder="카드명 또는 카드사 검색"
                  className="flex-1 px-4 py-3 rounded-xl border-2 border-[#F5C842] bg-white text-sm outline-none placeholder:text-[#999]"
                />
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="px-5 py-3 bg-[#F5C842] hover:bg-[#E0AD20] text-[#1A1A1A] font-bold text-sm rounded-xl border-none cursor-pointer transition-all duration-200"
                >
                  추가
                </button>
              </div>
              {showDropdown && cardSearch && filteredOptions.length > 0 && (
                <div className="absolute top-full left-0 right-12 mt-1 bg-white rounded-xl shadow-lg border border-[#E5E5E0] z-10 max-h-48 overflow-y-auto">
                  {filteredOptions.map((c) => (
                    <div key={c.id} onClick={() => addCard(c)}
                      className="px-4 py-3 hover:bg-[#FFFBEB] cursor-pointer transition-colors duration-150 border-b border-[#F5F4F0] last:border-0">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-semibold text-[#1A1A1A]">{c.name}</div>
                          <div className="text-xs text-[#999]">{c.company}</div>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                          {(c.mbti_types || []).map((mbti) => (
                            <span key={mbti} className="px-1.5 py-0.5 bg-[#E8F4FF] text-[#2563EB] text-[9px] rounded-full font-bold">
                              {mbti}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-4 gap-3">
              {ownedCards.map((card) => {
                const meta = cardOptions.find((c) => c.card_id === card.card_id);
                const mbtiTypes = meta?.mbti_types || [];
                return (
                  <div key={card.card_id} className="relative bg-white rounded-xl p-4 shadow-sm border-2 border-[#E5E5E0] aspect-[3/4] flex flex-col justify-between">
                    <button
                      onClick={() => removeCard(card.card_id)}
                      className="absolute -top-2 -left-2 w-6 h-6 bg-red-400 hover:bg-red-500 text-white rounded-full flex items-center justify-center text-xs font-bold cursor-pointer border-none z-10"
                    >−</button>
                    <div>
                      <div className="text-xs font-semibold text-[#1A1A1A] leading-tight mb-1">{card.name}</div>
                      <div className="text-[10px] text-[#999] mb-2">{card.company}</div>
                      <div className="flex gap-1 flex-wrap">
                        {mbtiTypes.map((mbti) => (
                          <span key={mbti} className="px-1.5 py-0.5 bg-[#E8F4FF] text-[#2563EB] text-[9px] rounded-full font-bold">
                            {mbti}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="text-2xl">💳</div>
                  </div>
                );
              })}
              {Array.from({ length: Math.max(0, 4 - ownedCards.length) }).map((_, i) => (
                <div key={`empty-${i}`} className="bg-white rounded-xl border-2 border-dashed border-[#E5E5E0] aspect-[3/4]" />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
