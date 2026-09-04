// Formatting helpers. Presentation only — values always come from the
// service layer (mock now, FastAPI backend later).

import type { Money } from "./types";

export function formatMoney(money: Money): string {
  const major = money.amount_minor / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: money.currency,
    minimumFractionDigits: Number.isInteger(major) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(major);
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const abs = Math.abs(diffMs);
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (abs < 60_000) return rtf.format(Math.round(-diffMs / 1000), "second");
  if (abs < 3_600_000) return rtf.format(Math.round(-diffMs / 60_000), "minute");
  if (abs < 86_400_000) return rtf.format(Math.round(-diffMs / 3_600_000), "hour");
  return rtf.format(Math.round(-diffMs / 86_400_000), "day");
}

export function formatCountdown(expiresAtIso: string, nowMs: number): string {
  const remaining = Math.max(0, new Date(expiresAtIso).getTime() - nowMs);
  const totalSeconds = Math.floor(remaining / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
