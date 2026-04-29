import { create } from 'zustand';
import { persist } from 'zustand/middleware';

<<<<<<< HEAD
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
    avatar: '🧑‍💻',
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
=======
const initialProfile = {
  age_group: '',
  has_car: null,
  annual_fee_range: '',
  lifestyles: [],
  monthly_spend: '',
  owned_cards: [],
  preferred_benefits: [],
  avatar: '🧑‍💻',
};

const isProfileComplete = (profile) =>
  Boolean(
    profile?.age_group &&
    profile?.annual_fee_range &&
    profile?.monthly_spend &&
    Array.isArray(profile?.lifestyles) &&
    profile.lifestyles.length > 0 &&
    profile?.has_car !== null
  );

const useUserStore = create(
  persist(
    (set) => ({
      profile: initialProfile,
>>>>>>> 0ef5ed9599f9d88a1438c53e8d22a5fae8bddda2
      isOnboarded: false,
      hasHydrated: false,
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      setProfile: (profile) => set({ profile, isOnboarded: true }),
      updateProfile: (fields) =>
        set((state) => ({
          profile: { ...state.profile, ...fields },
          isOnboarded: true,
        })),
      resetOnboarding: () =>
        set({
          isOnboarded: false,
          profile: initialProfile,
        }),
    }),
    {
      name: 'raichu-user-store',
      merge: (persistedState, currentState) => {
        const merged = {
          ...currentState,
          ...persistedState,
          profile: {
            ...currentState.profile,
            ...(persistedState?.profile ?? {}),
          },
        };

        return {
          ...merged,
          isOnboarded:
            Boolean(persistedState?.isOnboarded) || isProfileComplete(merged.profile),
        };
      },
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated?.(true);
      },
    }
  )
);

export default useUserStore;
