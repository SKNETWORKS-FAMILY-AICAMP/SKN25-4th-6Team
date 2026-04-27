import { useState } from 'react';

// ─── 상수 데이터 ───────────────────────────────────────────────
const CARDS = [
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

const LIFESTYLES = [
  { icon: '🚗', label: '카라이프',    value: '카라이프' },
  { icon: '✈️', label: '여행러',      value: '여행러' },
  { icon: '☕', label: '카페인 중독', value: '카페인중독' },
  { icon: '💻', label: '디지털 노마드', value: '디지털노마드' },
  { icon: '🏋️', label: '헬스·건강',  value: '헬스·건강' },
  { icon: '👨‍👩‍👧', label: '가족 중심', value: '가족중심' },
  { icon: '🍜', label: '배달·외식',  value: '배달·외식' },
  { icon: '🎬', label: '문화생활',   value: '문화생활' },
  { icon: '🛍️', label: '쇼핑',       value: '쇼핑' },
];

// 사이드바 스텝 정의
const STEPS = [
  { num: 1, title: '기본 프로필',  sub: '나이대, 차량, 연회비' },
  { num: 2, title: '소비 스타일', sub: '라이프스타일, 사용액' },
  { num: 3, title: '카드 & 혜택', sub: '보유카드, 혜택 타입' },
];

// ─── 스타일 (CSS-in-JS 방식 대신 <style> 태그 삽입) ──────────────
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap');

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --primary: #F5C842;
    --primary-dark: #E0AD20;
    --primary-light: #FFF7D6;
    --primary-glow: rgba(245, 200, 66, 0.3);
    --bg: #F5F4F0;
    --sidebar-bg: #1A1A1A;
    --card-bg: #FFFFFF;
    --text-dark: #1A1A1A;
    --text-mid: #555555;
    --text-light: #999999;
    --border: #E5E5E0;
    --selected-bg: #FFFBEB;
    --radius: 16px;
    --radius-sm: 12px;
    --shadow: 0 2px 16px rgba(0,0,0,0.04);
    --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  html, body { height: 100%; font-family: 'Noto Sans KR', sans-serif; color: var(--text-dark); background: var(--bg); }

  /* Layout */
  .ob-layout { display: flex; height: 100vh; overflow: hidden; }

  /* Sidebar */
  .ob-sidebar {
    width: 300px; min-width: 300px;
    background: var(--sidebar-bg); color: #fff;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 48px 32px 36px; position: relative; overflow: hidden;
  }
  .ob-sidebar::before {
    content: ''; position: absolute; top: -60%; left: -40%;
    width: 180%; height: 180%;
    background: radial-gradient(circle, rgba(245,200,66,0.08) 0%, transparent 60%);
    pointer-events: none;
  }
  .ob-sidebar-top { position: relative; z-index: 1; }

  .ob-logo { font-family: 'Outfit', sans-serif; font-size: 48px; font-weight: 900; letter-spacing: -2px; line-height: 1; margin-bottom: 4px; }
  .ob-logo .hl { color: var(--primary); }
  .ob-logo-sub { font-size: 10px; color: rgba(255,255,255,0.35); letter-spacing: 1px; margin-bottom: 48px; }

  /* Sidebar steps */
  .ob-steps { display: flex; flex-direction: column; gap: 0; }
  .ob-step { display: flex; align-items: flex-start; gap: 14px; cursor: pointer; padding: 4px 0; }
  .ob-step-track { display: flex; flex-direction: column; align-items: center; }
  .ob-step-dot {
    width: 30px; height: 30px; border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Outfit', sans-serif; font-size: 12px; font-weight: 700;
    color: rgba(255,255,255,0.25); transition: var(--transition); flex-shrink: 0;
  }
  .ob-step.active .ob-step-dot { background: var(--primary); border-color: var(--primary); color: var(--text-dark); box-shadow: 0 0 0 6px rgba(245,200,66,0.15); }
  .ob-step.done .ob-step-dot { background: transparent; border-color: var(--primary); color: var(--primary); }
  .ob-step-line { width: 2px; height: 32px; background: rgba(255,255,255,0.08); transition: var(--transition); }
  .ob-step.done .ob-step-line { background: var(--primary); }
  .ob-step:last-child .ob-step-line { display: none; }
  .ob-step-info { padding-top: 4px; }
  .ob-step-title { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.25); transition: var(--transition); margin-bottom: 2px; }
  .ob-step.active .ob-step-title { color: #fff; }
  .ob-step.done .ob-step-title { color: rgba(255,255,255,0.55); }
  .ob-step-sub { font-size: 11px; color: rgba(255,255,255,0.12); transition: var(--transition); }
  .ob-step.active .ob-step-sub { color: rgba(255,255,255,0.4); }
  .ob-step.done .ob-step-sub { color: rgba(255,255,255,0.28); }

  .ob-sidebar-footer { position: relative; z-index: 1; font-size: 10px; color: rgba(255,255,255,0.18); line-height: 1.6; }

  /* Main */
  .ob-main { flex: 1; overflow-y: auto; display: flex; justify-content: center; align-items: flex-start; padding: 60px 80px; }
  .ob-main-inner { width: 100%; max-width: 720px; }

  /* Step card animation */
  .ob-step-card { animation: cardIn 0.35s ease-out; }
  @keyframes cardIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }

  /* Step header */
  .ob-step-header { margin-bottom: 36px; }
  .ob-step-number { font-family: 'Outfit', sans-serif; font-size: 12px; font-weight: 700; color: var(--primary-dark); letter-spacing: 1px; margin-bottom: 6px; }
  .ob-step-title-text { font-size: 26px; font-weight: 700; line-height: 1.3; margin-bottom: 4px; }
  .ob-step-desc { font-size: 14px; color: var(--text-light); }

  /* Section */
  .ob-section { background: var(--card-bg); border-radius: var(--radius); padding: 24px 28px; margin-bottom: 14px; box-shadow: var(--shadow); }
  .ob-section-label { font-size: 14px; font-weight: 600; color: var(--text-dark); margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }

  /* Badge */
  .ob-badge { font-size: 10px; font-weight: 600; color: var(--text-light); background: #F0F0EC; padding: 3px 10px; border-radius: 100px; }
  .ob-badge.active { background: var(--primary); color: var(--text-dark); }

  /* Pill */
  .ob-pill-row { display: flex; gap: 10px; flex-wrap: wrap; }
  .ob-pill {
    padding: 10px 22px; border: 2px solid var(--border); border-radius: 100px;
    font-size: 13px; font-weight: 500; color: var(--text-mid);
    cursor: pointer; transition: var(--transition); user-select: none; background: #fff;
    font-family: 'Noto Sans KR', sans-serif;
  }
  .ob-pill:hover { border-color: var(--primary); background: var(--selected-bg); }
  .ob-pill.selected { border-color: var(--primary); background: var(--primary); color: var(--text-dark); font-weight: 600; }

  /* Toggle button */
  .ob-toggle-row { display: flex; gap: 10px; }
  .ob-toggle-btn {
    width: 150px; padding: 13px 0; border: 2px solid var(--border); border-radius: var(--radius-sm);
    text-align: center; font-size: 13px; font-weight: 500; color: var(--text-mid);
    cursor: pointer; transition: var(--transition); background: #fff;
    font-family: 'Noto Sans KR', sans-serif;
  }
  .ob-toggle-btn:hover { border-color: var(--primary); background: var(--selected-bg); }
  .ob-toggle-btn.selected { border-color: var(--primary); background: var(--primary); color: var(--text-dark); font-weight: 600; }

  /* Lifestyle grid */
  .ob-lifestyle-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .ob-lifestyle-card {
    background: var(--bg); border: 2px solid var(--border); border-radius: var(--radius-sm);
    padding: 20px 10px 16px; text-align: center;
    cursor: pointer; transition: var(--transition); position: relative;
  }
  .ob-lifestyle-card:hover { border-color: var(--primary); background: var(--selected-bg); transform: translateY(-2px); box-shadow: 0 4px 16px rgba(245,200,66,0.12); }
  .ob-lifestyle-card.selected { border-color: var(--primary); background: var(--selected-bg); box-shadow: 0 4px 16px rgba(245,200,66,0.15); }
  .ob-lifestyle-card.selected::after {
    content: '✓'; position: absolute; top: 8px; right: 8px;
    font-size: 10px; color: #fff; font-weight: 700;
    background: var(--primary-dark); width: 18px; height: 18px;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    line-height: 18px;
  }
  .ob-lifestyle-icon { font-size: 28px; display: block; margin-bottom: 6px; }
  .ob-lifestyle-label { font-size: 12px; font-weight: 500; color: var(--text-mid); }
  .ob-lifestyle-card.selected .ob-lifestyle-label { color: var(--text-dark); font-weight: 600; }

  /* Spending grid */
  .ob-spending-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .ob-spending-option {
    padding: 20px 16px; border: 2px solid var(--border); border-radius: var(--radius-sm);
    font-size: 14px; font-weight: 500; color: var(--text-mid);
    cursor: pointer; transition: var(--transition); text-align: center; background: var(--bg);
    font-family: 'Noto Sans KR', sans-serif;
  }
  .ob-spending-option:hover { border-color: var(--primary); background: var(--selected-bg); }
  .ob-spending-option.selected { border-color: var(--primary); background: var(--primary); color: var(--text-dark); font-weight: 600; }

  /* Card search */
  .ob-card-search { display: flex; align-items: center; gap: 10px; border: 2px solid var(--border); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 12px; background: var(--bg); transition: var(--transition); }
  .ob-card-search:focus-within { border-color: var(--primary); background: var(--selected-bg); }
  .ob-card-search input { border: none; background: transparent; font-size: 13px; color: var(--text-dark); width: 100%; outline: none; font-family: 'Noto Sans KR', sans-serif; }

  .ob-card-list { display: flex; flex-direction: column; gap: 6px; max-height: 220px; overflow-y: auto; }
  .ob-card-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border: 2px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition); background: #fff; }
  .ob-card-item:hover { border-color: var(--primary); background: var(--selected-bg); }
  .ob-card-item.selected { border-color: var(--primary); background: var(--selected-bg); }
  .ob-card-check { width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 10px; flex-shrink: 0; transition: var(--transition); }
  .ob-card-item.selected .ob-card-check { background: var(--primary); border-color: var(--primary); color: var(--text-dark); font-weight: 700; }
  .ob-card-name { font-size: 13px; font-weight: 600; color: var(--text-dark); }
  .ob-card-company { font-size: 11px; color: var(--text-light); margin-top: 1px; }

  .ob-selected-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
  .ob-selected-tag { display: flex; align-items: center; gap: 6px; background: var(--primary-light); border: 1px solid var(--primary); border-radius: 100px; padding: 5px 10px 5px 12px; font-size: 11px; font-weight: 600; color: var(--text-dark); }
  .ob-tag-rm { cursor: pointer; font-size: 14px; color: var(--text-light); line-height: 1; }
  .ob-tag-rm:hover { color: var(--text-dark); }

  /* Nav */
  .ob-nav-row { display: flex; justify-content: space-between; align-items: center; margin-top: 32px; }
  .ob-btn-back {
    padding: 12px 24px; border: 2px solid var(--border); border-radius: var(--radius-sm);
    background: var(--card-bg); font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px; font-weight: 500; color: var(--text-mid); cursor: pointer; transition: var(--transition);
  }
  .ob-btn-back:hover { border-color: var(--text-light); background: var(--bg); }
  .ob-btn-next {
    padding: 12px 36px; border: none; border-radius: var(--radius-sm);
    background: var(--primary); font-family: 'Noto Sans KR', sans-serif;
    font-size: 14px; font-weight: 700; color: var(--text-dark); cursor: pointer; transition: var(--transition);
    box-shadow: 0 2px 12px rgba(245,200,66,0.2);
  }
  .ob-btn-next:hover { background: var(--primary-dark); transform: translateY(-1px); box-shadow: 0 6px 24px rgba(245,200,66,0.3); }
  .ob-btn-next .arrow { margin-left: 6px; display: inline-block; transition: transform 0.2s; }
  .ob-btn-next:hover .arrow { transform: translateX(4px); }

  /* Completion */
  .ob-completion { text-align: center; padding: 80px 40px; }
  .ob-completion-icon { font-size: 64px; margin-bottom: 24px; display: block; }
  .ob-completion h2 { font-family: 'Outfit', sans-serif; font-size: 32px; font-weight: 800; margin-bottom: 12px; }
  .ob-completion h2 .hl { color: var(--primary-dark); }
  .ob-completion p { font-size: 15px; color: var(--text-mid); line-height: 1.7; }
`;

// ─── 메인 컴포넌트 ─────────────────────────────────────────────
export default function OnboardingPage({ onComplete }) {
  const [step, setStep] = useState(1);

  // Step 1
  const [ageGroup, setAgeGroup]         = useState('');
  const [hasCar, setHasCar]             = useState(null);   // true | false | null
  const [annualFeeRange, setAnnualFee]  = useState('');

  // Step 2
  const [lifestyles, setLifestyles]     = useState([]);
  const [monthlySpend, setMonthlySpend] = useState('');

  // Step 3
  const [cardSearch, setCardSearch]     = useState('');
  const [selectedCards, setSelectedCards] = useState(new Set());
  const [preferredBenefits, setBenefits] = useState([]);

  // ── 라이프스타일 토글 (최대 3개) ──
  const toggleLifestyle = (value) => {
    setLifestyles(prev => {
      if (prev.includes(value)) return prev.filter(v => v !== value);
      if (prev.length >= 3) return [...prev.slice(1), value];
      return [...prev, value];
    });
  };

  // ── 카드 토글 ──
  const toggleCard = (id) => {
    setSelectedCards(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // ── 혜택 토글 ──
  const toggleBenefit = (v) => {
    setBenefits(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v]);
  };

  // ── 필터된 카드 목록 ──
  const filteredCards = CARDS.filter(c =>
    c.name.includes(cardSearch) || c.company.includes(cardSearch)
  );

  // ── 완료 핸들러 ──
  const handleComplete = () => {
    const userData = {
      age_group: ageGroup,
      has_car: hasCar,
      annual_fee_range: annualFeeRange,
      lifestyles,
      monthly_spend: monthlySpend,
      owned_cards: CARDS.filter(c => selectedCards.has(c.id)).map(({ name, company, card_id }) => ({ name, company, card_id })),
      preferred_benefits: preferredBenefits,
    };
    onComplete?.(userData);
    setStep(4);
  };

  // ── 사이드바 스텝 상태 계산 ──
  const getSideStepClass = (num) => {
    if (num < step) return 'ob-step done';
    if (num === step) return 'ob-step active';
    return 'ob-step';
  };

  return (
    <>
      <style>{CSS}</style>
      <div className="ob-layout">

        {/* ── 사이드바 ── */}
        <aside className="ob-sidebar">
          <div className="ob-sidebar-top">
            <div className="ob-logo"><span className="hl">RAI</span>ch<span className="hl">U</span></div>
            <div className="ob-logo-sub">REAL AI CARD HUB SYSTEM FOR U</div>

            <div className="ob-steps">
              {STEPS.map(s => (
                <div key={s.num} className={getSideStepClass(s.num)} onClick={() => step > s.num && setStep(s.num)}>
                  <div className="ob-step-track">
                    <div className="ob-step-dot">
                      {step > s.num ? '✓' : s.num}
                    </div>
                    <div className="ob-step-line" />
                  </div>
                  <div className="ob-step-info">
                    <div className="ob-step-title">{s.title}</div>
                    <div className="ob-step-sub">{s.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="ob-sidebar-footer">
            © 2026 RAIchU<br />AI 기반 맞춤 카드 추천 서비스
          </div>
        </aside>

        {/* ── 메인 ── */}
        <main className="ob-main">
          <div className="ob-main-inner">

            {/* ── STEP 1 ── */}
            {step === 1 && (
              <div className="ob-step-card">
                <div className="ob-step-header">
                  <div className="ob-step-number">STEP 01</div>
                  <div className="ob-step-title-text">기본 프로필을 알려주세요</div>
                  <div className="ob-step-desc">맞춤 카드 추천을 위한 기본 정보예요</div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">나이대</div>
                  <div className="ob-pill-row">
                    {['20대', '30대', '40대', '50대 이상'].map(v => (
                      <div key={v} className={`ob-pill ${ageGroup === v ? 'selected' : ''}`} onClick={() => setAgeGroup(v)}>{v}</div>
                    ))}
                  </div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">자동차 보유 여부</div>
                  <div className="ob-toggle-row">
                    <div className={`ob-toggle-btn ${hasCar === true ? 'selected' : ''}`} onClick={() => setHasCar(true)}>🚗 있음</div>
                    <div className={`ob-toggle-btn ${hasCar === false ? 'selected' : ''}`} onClick={() => setHasCar(false)}>🚶 없음</div>
                  </div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">연회비 허용 범위</div>
                  <div className="ob-pill-row">
                    {['없음 선호', '3만원 이하', '5만원 이상도 OK'].map(v => (
                      <div key={v} className={`ob-pill ${annualFeeRange === v ? 'selected' : ''}`} onClick={() => setAnnualFee(v)}>{v}</div>
                    ))}
                  </div>
                </div>

                <div className="ob-nav-row">
                  <div />
                  <button className="ob-btn-next" onClick={() => setStep(2)}>다음 단계 <span className="arrow">→</span></button>
                </div>
              </div>
            )}

            {/* ── STEP 2 ── */}
            {step === 2 && (
              <div className="ob-step-card">
                <div className="ob-step-header">
                  <div className="ob-step-number">STEP 02</div>
                  <div className="ob-step-title-text">소비 스타일을 알려주세요</div>
                  <div className="ob-step-desc">주로 어디에 가장 많이 쓰시나요?</div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">
                    라이프스타일
                    <span className={`ob-badge ${lifestyles.length > 0 ? 'active' : ''}`}>{lifestyles.length} / 3</span>
                  </div>
                  <div className="ob-lifestyle-grid">
                    {LIFESTYLES.map(item => (
                      <div
                        key={item.value}
                        className={`ob-lifestyle-card ${lifestyles.includes(item.value) ? 'selected' : ''}`}
                        onClick={() => toggleLifestyle(item.value)}
                      >
                        <span className="ob-lifestyle-icon">{item.icon}</span>
                        <span className="ob-lifestyle-label">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">월 카드 사용액</div>
                  <div className="ob-spending-grid">
                    {['30만원 미만', '30~70만원', '70~150만원', '150만원 이상'].map(v => (
                      <div
                        key={v}
                        className={`ob-spending-option ${monthlySpend === v ? 'selected' : ''}`}
                        onClick={() => setMonthlySpend(v)}
                      >{v}</div>
                    ))}
                  </div>
                </div>

                <div className="ob-nav-row">
                  <button className="ob-btn-back" onClick={() => setStep(1)}>← 이전</button>
                  <button className="ob-btn-next" onClick={() => setStep(3)}>다음 단계 <span className="arrow">→</span></button>
                </div>
              </div>
            )}

            {/* ── STEP 3 ── */}
            {step === 3 && (
              <div className="ob-step-card">
                <div className="ob-step-header">
                  <div className="ob-step-number">STEP 03</div>
                  <div className="ob-step-title-text">보유 카드 & 원하는 혜택</div>
                  <div className="ob-step-desc">현재 쓰고 있는 카드와 원하는 혜택을 선택해주세요</div>
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">보유 카드 선택</div>
                  <div className="ob-card-search">
                    <span>🔍</span>
                    <input
                      type="text"
                      placeholder="카드명 또는 카드사 검색"
                      value={cardSearch}
                      onChange={e => setCardSearch(e.target.value)}
                    />
                  </div>
                  <div className="ob-card-list">
                    {filteredCards.map(c => (
                      <div
                        key={c.id}
                        className={`ob-card-item ${selectedCards.has(c.id) ? 'selected' : ''}`}
                        onClick={() => toggleCard(c.id)}
                      >
                        <div className="ob-card-check">{selectedCards.has(c.id) ? '✓' : ''}</div>
                        <div>
                          <div className="ob-card-name">{c.name}</div>
                          <div className="ob-card-company">{c.company}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {selectedCards.size > 0 && (
                    <div className="ob-selected-tags">
                      {CARDS.filter(c => selectedCards.has(c.id)).map(c => (
                        <div key={c.id} className="ob-selected-tag">
                          {c.name}
                          <span className="ob-tag-rm" onClick={e => { e.stopPropagation(); toggleCard(c.id); }}>×</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="ob-section">
                  <div className="ob-section-label">원하는 혜택 타입 <span className="ob-badge">복수 선택</span></div>
                  <div className="ob-pill-row">
                    {[
                      { label: '💰 즉시할인', value: '즉시할인' },
                      { label: '🎯 포인트적립', value: '포인트적립' },
                      { label: '✈️ 마일리지', value: '마일리지' },
                      { label: '💸 캐시백', value: '캐시백' },
                    ].map(b => (
                      <div
                        key={b.value}
                        className={`ob-pill ${preferredBenefits.includes(b.value) ? 'selected' : ''}`}
                        onClick={() => toggleBenefit(b.value)}
                      >{b.label}</div>
                    ))}
                  </div>
                </div>

                <div className="ob-nav-row">
                  <button className="ob-btn-back" onClick={() => setStep(2)}>← 이전</button>
                  <button className="ob-btn-next" onClick={handleComplete}>시작하기 ⚡</button>
                </div>
              </div>
            )}

            {/* ── STEP 4 : 완료 ── */}
            {step === 4 && (
              <div className="ob-step-card">
                <div className="ob-completion">
                  <span className="ob-completion-icon">⚡</span>
                  <h2><span className="hl">RAIchU</span> 준비 완료!</h2>
                  <p>입력하신 정보를 바탕으로<br />나에게 딱 맞는 카드를 추천해드릴게요.</p>
                  <button className="ob-btn-next" style={{ marginTop: 32 }} onClick={() => onComplete?.()}>
                    추천 카드 보기 <span className="arrow">→</span>
                  </button>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </>
  );
}
