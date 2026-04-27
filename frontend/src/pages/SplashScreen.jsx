import { useEffect, useState } from 'react';

export default function SplashScreen({ onFinish }) {
  const [phase, setPhase] = useState('enter'); // enter → show → exit

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('show'), 100);
    const t2 = setTimeout(() => setPhase('exit'), 2200);
    const t3 = setTimeout(() => onFinish(), 2800);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: '#1A1A1A',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      zIndex: 9999,
      opacity: phase === 'exit' ? 0 : 1,
      transition: phase === 'exit' ? 'opacity 0.6s ease' : 'none',
    }}>
      {/* 배경 글로우 */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(circle at 50% 50%, rgba(245,200,66,0.08) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      {/* 로고 */}
      <div style={{
        fontFamily: 'Outfit, sans-serif',
        fontSize: 72,
        fontWeight: 900,
        letterSpacing: -3,
        lineHeight: 1,
        color: '#fff',
        opacity: phase === 'enter' ? 0 : 1,
        transform: phase === 'enter' ? 'translateY(20px)' : 'translateY(0)',
        transition: 'opacity 0.6s ease, transform 0.6s ease',
        marginBottom: 16,
      }}>
        <span style={{ color: '#F5C842' }}>RAI</span>
        ch
        <span style={{ color: '#F5C842' }}>U</span>
      </div>

      {/* 번개 이모지 */}
      <div style={{
        fontSize: 32,
        marginBottom: 24,
        opacity: phase === 'enter' ? 0 : 1,
        transition: 'opacity 0.6s ease 0.2s',
      }}>⚡</div>

      {/* 태그라인 */}
      <div style={{
        fontSize: 15,
        color: 'rgba(255,255,255,0.5)',
        letterSpacing: 1,
        fontFamily: 'Noto Sans KR, sans-serif',
        opacity: phase === 'enter' ? 0 : 1,
        transition: 'opacity 0.6s ease 0.4s',
        textAlign: 'center',
        lineHeight: 1.8,
      }}>
        나에게 딱 맞는 카드를 찾아드릴게요<br/>
        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.25)', letterSpacing: 2 }}>
          REAL AI CARD HUB SYSTEM FOR U
        </span>
      </div>

      {/* 로딩 바 */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 3,
        background: 'rgba(255,255,255,0.05)',
      }}>
        <div style={{
          height: '100%',
          background: '#F5C842',
          width: phase === 'enter' ? '0%' : phase === 'show' ? '80%' : '100%',
          transition: phase === 'enter' ? 'none' : phase === 'show' ? 'width 2s ease' : 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}
