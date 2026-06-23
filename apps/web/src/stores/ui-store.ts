"use client";

import { create } from "zustand";

/**
 * UI-only state via Zustand.
 * Rule: NEVER store server data (runs, artifacts, approvals) here.
 * Server data goes through TanStack Query.
 */
interface UIState {
	sidebarOpen: boolean;
	toggleSidebar: () => void;
	theme: "light" | "dark" | "system";
	setTheme: (theme: "light" | "dark" | "system") => void;
}

export const useUIStore = create<UIState>((set) => ({
	sidebarOpen: true,
	toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
	theme: "system",
	setTheme: (theme) => set({ theme }),
}));
