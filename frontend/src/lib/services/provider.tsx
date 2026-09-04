"use client";

// React binding for the mock commerce store. Creates the store exactly once per
// provider instance and exposes it via context using useSyncExternalStore.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  createCommerceStore,
  type CommerceActions,
  type CommerceState,
} from "./store";

export interface CommerceContextValue {
  state: CommerceState;
  actions: CommerceActions;
}

const CommerceContext = createContext<CommerceContextValue | null>(null);

type Store = ReturnType<typeof createCommerceStore>;

/** Provides the mock commerce store (state + actions) to the subtree. */
export function CommerceProvider({ children }: { children: ReactNode }) {
  const [store] = useState<Store>(() => createCommerceStore());
  const state = useSyncExternalStore(
    store.subscribe,
    store.getState,
    store.getState,
  );
  return (
    <CommerceContext.Provider value={{ state, actions: store.actions }}>
      {children}
    </CommerceContext.Provider>
  );
}

/** Access the mock commerce store; must be used under CommerceProvider. */
export function useCommerce(): CommerceContextValue {
  const ctx = useContext(CommerceContext);
  if (!ctx) {
    throw new Error("useCommerce must be used within <CommerceProvider>");
  }
  return ctx;
}

/** Re-rendering clock (default 1s) for countdowns and relative timestamps. */
export function useNow(intervalMs: number = 1000): number {
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
