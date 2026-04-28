import { useEffect, useState } from 'react';
import raichuImg from '../assets/raichu.png';

export default function SplashScreen({ onFinish }) {
  const [phase, setPhase] = useState('enter');

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('show'), 100);
    const t2 = setTimeout(() => setPhase('exit'), 2500);
    const t3 = setTimeout(() => onFinish(), 3100);
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
        background: 'radial-gradient(circle at 50% 45%, rgba(245,200,66,0.1) 0%, transparent 65%)',
        pointerEvents: 'none',
      }} />

      {/* 라이츄 이미지 */}
      <div style={{
        opacity: phase === 'enter' ? 0 : 1,
        transform: phase === 'enter' ? 'translateY(30px) scale(0.85)' : 'translateY(0) scale(1)',
        transition: 'opacity 0.7s ease, transform 0.7s cubic-bezier(0.34, 1.56, 0.64, 1)',
        marginBottom: 20,
        filter: 'drop-shadow(0 8px 24px rgba(245,200,66,0.35))',
      }}>
        <img src={raichuImg} alt="RAIchU" style={{ width: 160, height: 160, objectFit: 'contain' }} />
      </div>

      {/* 로고 */}
      <div style={{
        fontFamily: 'Outfit, sans-serif',
        fontSize: 64,
        fontWeight: 900,
        letterSpacing: -3,
        lineHeight: 1,
        color: '#fff',
        opacity: phase === 'enter' ? 0 : 1,
        transform: phase === 'enter' ? 'translateY(16px)' : 'translateY(0)',
        transition: 'opacity 0.6s ease 0.15s, transform 0.6s ease 0.15s',
        marginBottom: 10,
      }}>
        <span style={{ color: '#F5C842' }}>RAI</span>ch<span style={{ color: '#F5C842' }}>U</span>
      </div>

      {/* 태그라인 */}
      <div style={{
        fontSize: 14,
        color: 'rgba(255,255,255,0.45)',
        letterSpacing: 1,
        fontFamily: 'Noto Sans KR, sans-serif',
        opacity: phase === 'enter' ? 0 : 1,
        transition: 'opacity 0.6s ease 0.35s',
        textAlign: 'center',
        lineHeight: 1.9,
      }}>
        나에게 딱 맞는 카드를 찾아드릴게요
        <br />
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', letterSpacing: 2 }}>
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
          background: 'linear-gradient(90deg, #F5C842, #E0AD20)',
          width: phase === 'enter' ? '0%' : phase === 'show' ? '80%' : '100%',
          transition: phase === 'enter' ? 'none' : phase === 'show' ? 'width 2.3s ease' : 'width 0.5s ease',
          borderRadius: '0 2px 2px 0',
        }} />
      </div>
    </div>
  );
}
