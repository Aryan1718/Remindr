import { create } from "zustand";

interface UiStore {
  sidebarOpen: boolean;
  onboardingStep: number;
  setSidebarOpen: (open: boolean) => void;
  setOnboardingStep: (step: number) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarOpen: false,
  onboardingStep: 0,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setOnboardingStep: (onboardingStep) => set({ onboardingStep }),
}));
