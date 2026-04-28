import { create } from 'zustand';
import { persist } from 'zustand/middleware';

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
