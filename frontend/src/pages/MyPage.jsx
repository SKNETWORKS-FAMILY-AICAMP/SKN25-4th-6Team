import { useEffect, useState } from 'react';
import { getCards } from '../api/client';
import useUserStore from '../store/userStore';

const MBTI_PROFILES = [
  { type: 'ISTJ', emoji: '📋', label: '신뢰할 수 있는 관리자' },
  { type: 'ISFJ', emoji: '🏠', label: '용감한 수호자' },
  { type: 'INFJ', emoji: '🌿', label: '선의의 옹호자' },
  { type: 'INTJ', emoji: '🎯', label: '용의주도한 전략가' },
  { type: 'ISTP', emoji: '🔧', label: '만능 재주꾼' },
  { type: 'ISFP', emoji: '🎨', label: '호기심 많은 예술가' },
  { type: 'INFP', emoji: '📚', label: '열정적인 중재자' },
  { type: 'INTP', emoji: '💡', label: '논리적인 사색가' },
  { type: 'ESTJ', emoji: '⚡', label: '엄격한 관리자' },
  { type: 'ESFJ', emoji: '🤝', label: '사교적인 외교관' },
  { type: 'ENFJ', emoji: '🌟', label: '정의로운 사회운동가' },
  { type: 'ENTJ', emoji: '👑', label: '대담한 통솔자' },
  { type: 'ESTP', emoji: '🚀', label: '모험을 즐기는 사업가' },
  { type: 'ESFP', emoji: '🎉', label: '자유로운 연예인' },
  { type: 'ENFP', emoji: '✨', label: '재기발랄한 활동가' },
  { type: 'ENTP', emoji: '💫', label: '뜨거운 논쟁가' },
];

// 각 필드의 선택지 정의
const FIELD_OPTIONS = {
  age_group: ['20대', '30대', '40대', '50대 이상'],
  has_car: [true, false],
  monthly_spend: ['30만원 미만', '30~70만원', '70~150만원', '150만원 이상'],
  annual_fee_range: ['없음 선호', '3만원 이하', '5만원 이상도 OK'],
  preferred_benefits: ['즉시할인', '포인트적립', '마일리지', '캐시백'],
  lifestyles: ['카라이프', '여행러', '카페인중독', '디지털노마드', '헬스·건강', '가족중심', '배달·외식', '문화생활', '쇼핑'],
  mbti: MBTI_PROFILES.map(p => p.type),
};

const PROFILE_ITEMS = [
  { key: 'age_group',          label: '나이대',      icon: '🎂' },
  { key: 'has_car',            label: '자동차',      icon: '🚗' },
  { key: 'monthly_spend',      label: '월 사용액',   icon: '💳' },
  { key: 'annual_fee_range',   label: '연회비 허용', icon: '💰' },
  { key: 'preferred_benefits', label: '선호 혜택',   icon: '🎯' },
  { key: 'lifestyles',         label: '라이프스타일', icon: '✨' },
  { key: 'mbti',               label: 'MBTI',        icon: '🧠' },
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
  const { profile, updateProfile, resetOnboarding } = useUserStore();
  const [cardSearch, setCardSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [cardOptions, setCardOptions] = useState([]);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [selectedMbti, setSelectedMbti] = useState(null);

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
    <div className="fixed inset-0 flex overflow-hidden bg-[#F5F4F0]">
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
              <div className="flex items-center gap-3">
                <span className="text-xs text-[#999]">항목을 클릭해서 수정하세요</span>
                <button
                  onClick={() => {
                    if (window.confirm('프로필을 초기화하면 모든 설정이 삭제되고 온보딩으로 돌아갑니다. 계속할까요?')) {
                      resetOnboarding();
                    }
                  }}
                  className="px-3 py-1 text-xs text-red-400 border border-red-200 rounded-lg hover:bg-red-50 cursor-pointer bg-transparent transition-all duration-150"
                >
                  초기화
                </button>
              </div>
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

          {/* MBTI 카드 탐색 */}
          <div className="mt-10">
            <h2 className="text-xl font-bold text-[#1A1A1A] mb-1">MBTI 카드 탐색</h2>
            <p className="text-sm text-[#999] mb-4">MBTI 유형을 선택하면 어울리는 카드를 확인할 수 있어요</p>

            <div className="grid grid-cols-4 gap-2 mb-5">
              {MBTI_PROFILES.map(({ type, emoji, label }) => (
                <button
                  key={type}
                  onClick={() => setSelectedMbti(selectedMbti === type ? null : type)}
                  className={`px-3 py-2 rounded-xl text-left border-2 cursor-pointer transition-all duration-150
                    ${selectedMbti === type
                      ? 'bg-[#E8F4FF] border-[#2563EB] text-[#2563EB]'
                      : 'bg-white border-[#E5E5E0] text-[#555] hover:border-[#2563EB]/40 hover:bg-[#E8F4FF]/30'
                    }`}
                >
                  <div className="text-xs font-bold">{emoji} {type}</div>
                  <div className="text-[9px] mt-0.5 truncate opacity-60">{label}</div>
                </button>
              ))}
            </div>

            {selectedMbti && (() => {
              const mbtiProfile = MBTI_PROFILES.find(p => p.type === selectedMbti);
              const mbtiCards = cardOptions.filter(c => (c.mbti_types || []).includes(selectedMbti));
              return (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">{mbtiProfile?.emoji}</span>
                    <span className="text-sm font-bold text-[#1A1A1A]">{selectedMbti} · {mbtiProfile?.label}</span>
                    <span className="text-xs text-[#999] bg-[#E8F4FF] text-[#2563EB] px-2 py-0.5 rounded-full font-medium">{mbtiCards.length}개</span>
                  </div>
                  {mbtiCards.length === 0 ? (
                    <div className="text-sm text-[#999] py-6 text-center bg-white rounded-xl border border-dashed border-[#E5E5E0]">
                      해당 유형에 매칭된 카드가 없어요
                    </div>
                  ) : (
                    <div className="grid grid-cols-4 gap-3">
                      {mbtiCards.map((card) => (
                        <div key={card.card_id} className="bg-white rounded-xl p-4 shadow-sm border border-[#E5E5E0] hover:border-[#2563EB]/30 transition-colors duration-150">
                          <div className="text-[10px] text-[#999] mb-1">{card.company}</div>
                          <div className="text-sm font-semibold text-[#1A1A1A] leading-tight">{card.name}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}
          </div>

        </div>
      </main>
    </div>
  );
}
