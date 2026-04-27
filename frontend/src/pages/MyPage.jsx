import { useState } from 'react';
import useUserStore from '../store/userStore';

// 온보딩 데이터 → 표시용 라벨 매핑
const PROFILE_ITEMS = [
  { key: 'age_group',         label: '나이대',      icon: '🎂' },
  { key: 'has_car',           label: '자동차',      icon: '🚗' },
  { key: 'monthly_spend',     label: '월 사용액',   icon: '💳' },
  { key: 'annual_fee_range',  label: '연회비 허용', icon: '💰' },
  { key: 'preferred_benefits',label: '선호 혜택',   icon: '🎯' },
  { key: 'lifestyles',        label: '라이프스타일', icon: '✨' },
];

const formatValue = (key, value) => {
  if (value === null || value === undefined || value === '') return '미입력';
  if (key === 'has_car') return value ? '있음' : '없음';
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '미입력';
  return value;
};

// 목 카드 데이터 (나중에 API 연결)
const CARD_OPTIONS = [
  { id: 1,  name: '토스 올인원 체크카드',      company: '토스뱅크',    card_id: 'TOSS_ALLINONE_001' },
  { id: 2,  name: '신한카드 Deep Dream',        company: '신한카드',    card_id: 'SHINHAN_DEEP_DREAM_001' },
  { id: 3,  name: '삼성 iD SIMPLE 카드',        company: '삼성카드',    card_id: 'SAMSUNG_ID_SIMPLE_001' },
  { id: 4,  name: 'KB국민 My WE:SH 카드',       company: 'KB국민카드',  card_id: 'KB_MYWESH_001' },
  { id: 5,  name: '현대카드 ZERO Edition2',     company: '현대카드',    card_id: 'HYUNDAI_ZERO_ED2_001' },
  { id: 6,  name: '우리카드 카드의정석 COOKIE', company: '우리카드',    card_id: 'WOORI_COOKIE_001' },
  { id: 7,  name: 'NH올원 Pay 카드',            company: 'NH농협카드',  card_id: 'NH_ALLONE_PAY_001' },
  { id: 8,  name: '롯데카드 LOCA 365',          company: '롯데카드',    card_id: 'LOTTE_LOCA365_001' },
  { id: 9,  name: 'IBK 참! 좋은 카드',          company: 'IBK기업은행', card_id: 'IBK_GOOD_001' },
  { id: 10, name: '하나카드 원큐 페이',         company: '하나카드',    card_id: 'HANA_1Q_PAY_001' },
];

export default function MyPage({ onGoChat, onEditProfile }) {
  const { profile, updateProfile, resetOnboarding } = useUserStore();
  const [cardSearch, setCardSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  // 보유 카드 목록 (profile.owned_cards 기반)
  const ownedCards = profile.owned_cards || [];

  const filteredOptions = CARD_OPTIONS.filter(
    (c) =>
      (c.name.includes(cardSearch) || c.company.includes(cardSearch)) &&
      !ownedCards.some((o) => o.card_id === c.card_id)
  );

  const addCard = (card) => {
    updateProfile({
      owned_cards: [...ownedCards, { name: card.name, company: card.company, card_id: card.card_id }],
    });
    setCardSearch('');
    setShowDropdown(false);
  };

  const removeCard = (card_id) => {
    updateProfile({ owned_cards: ownedCards.filter((c) => c.card_id !== card_id) });
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F5F4F0]">

      {/* ── 사이드바 ── */}
      <aside className="w-[240px] min-w-[240px] bg-[#1A1A1A] text-white flex flex-col px-5 py-8 relative overflow-hidden">
        <div className="absolute -top-1/2 -left-1/3 w-[200%] h-[200%] pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(245,200,66,0.06) 0%, transparent 60%)' }} />

        <div className="relative z-10 flex flex-col h-full">
          {/* 로고 */}
          <div className="mb-8">
            <div className="text-3xl font-black tracking-tight leading-none" style={{ fontFamily: 'Outfit, sans-serif' }}>
              <span className="text-[#F5C842]">RAI</span>ch<span className="text-[#F5C842]">U</span>
            </div>
            <div className="text-[9px] text-white/25 tracking-widest">v.1.0.0</div>
          </div>

          {/* 새 대화 버튼 */}
          <button
            onClick={onGoChat}
            className="w-full py-2.5 border-2 border-white/20 rounded-xl text-sm font-medium text-white hover:border-[#F5C842] hover:text-[#F5C842] transition-all duration-200 mb-5 cursor-pointer bg-transparent"
          >
            ✏️ 새 대화
          </button>

          <div className="flex-1" />

          {/* My Page 버튼 (활성) */}
          <button className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-[#F5C842]/50 bg-[#F5C842]/10 text-sm text-[#F5C842] font-semibold cursor-default mt-4">
            <span>💳</span>
            <span>My Page</span>
          </button>
        </div>
      </aside>

      {/* ── 마이페이지 메인 ── */}
      <main className="flex-1 overflow-y-auto px-12 py-10">
        <div className="max-w-[760px] mx-auto">

          {/* MY PROFILE */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-[#1A1A1A]">MY PROFILE</h2>
              <button
                onClick={resetOnboarding}
                className="text-sm text-[#999] hover:text-[#F5C842] transition-colors duration-200 cursor-pointer bg-transparent border-none"
              >
                수정하기
              </button>
            </div>

            <div className="flex items-start gap-5">
              {/* 아바타 */}
              <div className="w-16 h-16 rounded-full bg-[#E5E5E0] flex items-center justify-center text-3xl flex-shrink-0">
                👤
              </div>

              {/* 프로필 카드 그리드 */}
              <div className="flex-1 grid grid-cols-2 gap-3">
                {PROFILE_ITEMS.map((item) => (
                  <div key={item.key} className="bg-white rounded-xl px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">{item.icon}</span>
                      <span className="text-xs font-semibold text-[#999]">{item.label}</span>
                    </div>
                    <div className="text-sm font-medium text-[#1A1A1A] truncate">
                      {formatValue(item.key, profile[item.key])}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* MY CARD */}
          <div>
            <h2 className="text-xl font-bold text-[#1A1A1A] mb-2">MY CARD</h2>
            <p className="text-sm text-[#999] mb-4">보유 중인 카드</p>

            {/* 카드 검색/추가 */}
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

              {/* 드롭다운 */}
              {showDropdown && cardSearch && filteredOptions.length > 0 && (
                <div className="absolute top-full left-0 right-12 mt-1 bg-white rounded-xl shadow-lg border border-[#E5E5E0] z-10 max-h-48 overflow-y-auto">
                  {filteredOptions.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => addCard(c)}
                      className="px-4 py-3 hover:bg-[#FFFBEB] cursor-pointer transition-colors duration-150 border-b border-[#F5F4F0] last:border-0"
                    >
                      <div className="text-sm font-semibold text-[#1A1A1A]">{c.name}</div>
                      <div className="text-xs text-[#999]">{c.company}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 카드 그리드 */}
            <div className="grid grid-cols-4 gap-3">
              {ownedCards.map((card) => (
                <div key={card.card_id} className="relative bg-white rounded-xl p-4 shadow-sm border-2 border-[#E5E5E0] aspect-[3/4] flex flex-col justify-between">
                  {/* 삭제 버튼 */}
                  <button
                    onClick={() => removeCard(card.card_id)}
                    className="absolute -top-2 -left-2 w-6 h-6 bg-red-400 hover:bg-red-500 text-white rounded-full flex items-center justify-center text-xs font-bold cursor-pointer border-none transition-colors duration-150 z-10"
                  >
                    −
                  </button>
                  <div>
                    <div className="text-xs font-semibold text-[#1A1A1A] leading-tight mb-1">{card.name}</div>
                    <div className="text-[10px] text-[#999]">{card.company}</div>
                  </div>
                  <div className="text-2xl">💳</div>
                </div>
              ))}

              {/* 빈 슬롯 (최소 4개 표시) */}
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
