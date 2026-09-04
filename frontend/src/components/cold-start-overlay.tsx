"use client";

import { useCommerce } from "@/lib/services/provider";

export function ColdStartOverlay() {
  const { state } = useCommerce();
  const show = (state as any)._coldStartOverlay;

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-4 rounded-lg bg-card p-8 shadow-xl border text-card-foreground">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <h2 className="text-xl font-semibold">Waking Up Server</h2>
        <p className="text-sm text-muted-foreground text-center max-w-xs">
          The backend is cold-starting. This usually takes about 30 seconds...
        </p>
      </div>
    </div>
  );
}
