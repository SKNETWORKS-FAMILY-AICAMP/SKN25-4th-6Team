import { create } from 'zustand';

const useUserStore = create((set) => ({
  profile: {
    age_group: '',
    has_car: null,
    annual_fee_range: '',
    lifestyles: [],
    monthly_spend: '',
    owned_cards: [],
    preferred_benefits: [],
  },
  isOnboarded: false,
  setProfile: (profile) => set({ profile, isOnboarded: true }),
  updateProfile: (fields) =>
    set((state) => ({ profile: { ...state.profile, ...fields } })),
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
