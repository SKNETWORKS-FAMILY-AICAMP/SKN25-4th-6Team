import { create } from 'zustand';

const useUserStore = create((set) => ({
  // 온보딩 데이터
  profile: {
    age_group: '',
    has_car: null,
    annual_fee_range: '',
    lifestyles: [],
    monthly_spend: '',
    owned_cards: [],
    preferred_benefits: [],
  },

  // 온보딩 완료 여부
  isOnboarded: false,

  // 프로필 업데이트
  setProfile: (profile) => set({ profile, isOnboarded: true }),

  // 개별 필드 업데이트
  updateProfile: (fields) =>
    set((state) => ({ profile: { ...state.profile, ...fields } })),

  // 온보딩 초기화 (마이페이지에서 수정 시)
  resetOnboarding: () =>
    set({
      isOnboarded: false,
      profile: {
        age_group: '',
        has_car: null,
        annual_fee_range: '',
        lifestyles: [],
        monthly_spend: '',
        owned_cards: [],
        preferred_benefits: [],
      },
    }),
}));

export default useUserStore;
