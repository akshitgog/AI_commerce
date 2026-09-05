"use client";

import { useState } from "react";

import { useCommerce } from "@/lib/services/provider";
import type { PolicyMode } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const POLICIES: {
  mode: PolicyMode;
  title: string;
  summary: string;
  consequence: string;
}[] = [
  {
    mode: "MANUAL_ALL",
    title: "Review every purchase",
    summary: "You approve or deny every AI-initiated purchase.",
    consequence:
      "Every AI-initiated purchase will wait in your Review Queue until you approve or deny it. Nothing is paid automatically.",
  },
  {
    mode: "AUTO_BELOW_LIMIT",
    title: "Automatically accept below a limit",
    summary:
      "Eligible purchases at or below your limit are accepted automatically.",
    consequence:
      "Eligible purchases at or below your limit are accepted without manual review. Anything above the limit, or otherwise ineligible, goes to your Review Queue.",
  },
  {
    mode: "DENY_ALL",
    title: "Block AI purchases",
    summary: "No AI-initiated purchases are accepted.",
    consequence:
      "All AI-initiated purchases are declined. Buyers will not be able to complete a purchase from your catalog via the AI gateway.",
  },
];

export default function PolicyPage() {
  const { state, actions } = useCommerce();
  const saved = state.policy;

  const [mode, setMode] = useState<PolicyMode>(saved.mode);
  const [maxRupees, setMaxRupees] = useState<string>(() =>
    saved.maxAmount ? (saved.maxAmount.amount_minor / 100).toString() : ""
  );
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const savedMaxRupees = saved.maxAmount
    ? (saved.maxAmount.amount_minor / 100).toString()
    : "";
  const dirty = mode !== saved.mode || maxRupees !== savedMaxRupees;

  const selected = POLICIES.find((p) => p.mode === mode)!;
  const maxAmountInvalid =
    mode === "AUTO_BELOW_LIMIT" &&
    (maxRupees.trim() === "" ||
      !Number.isFinite(Number(maxRupees)) ||
      Number(maxRupees) <= 0);

  async function handleSave() {
    if (maxAmountInvalid) return;
    setSaving(true);
    setError(null);
    setSavedNotice(false);
    try {
      await actions.updatePolicy({
        mode,
        maxAmount:
          mode === "AUTO_BELOW_LIMIT"
            ? {
                amount_minor: Math.round(Number(maxRupees) * 100),
                currency: "INR",
              }
            : undefined,
      });
      setSavedNotice(true);
      window.setTimeout(() => setSavedNotice(false), 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the policy.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div>
        <h2 className="text-lg font-semibold">Purchase policy</h2>
        <p className="text-sm text-muted-foreground">
          Decide how AI-initiated purchases are accepted. Buyer authorization is
          always separate from your merchant acceptance.
        </p>
      </div>

      <div aria-live="polite" className="space-y-3">
        {savedNotice ? (
          <Alert variant="success">
            <AlertTitle>Policy saved</AlertTitle>
            <AlertDescription>
              Your purchase policy was updated.
            </AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive" role="alert">
            <AlertTitle>Could not save policy</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Policy mode</CardTitle>
          <CardDescription>
            Current saved policy:{" "}
            <span className="font-medium text-foreground">
              {POLICIES.find((p) => p.mode === saved.mode)?.title}
            </span>{" "}
            <span className="tnum font-mono text-xs">(v{saved.version})</span>
            {saved.mode === "AUTO_BELOW_LIMIT" && saved.maxAmount
              ? ` — ${formatMoney(saved.maxAmount)}`
              : ""}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            role="radiogroup"
            aria-label="Purchase policy mode"
            className="grid gap-3 md:grid-cols-3"
          >
            {POLICIES.map((policy) => {
              const checked = mode === policy.mode;
              return (
                <button
                  key={policy.mode}
                  type="button"
                  role="radio"
                  aria-checked={checked}
                  onClick={() => {
                    setMode(policy.mode);
                    setSavedNotice(false);
                  }}
                  className={cn(
                    "rounded-md border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    checked
                      ? "border-primary ring-1 ring-primary"
                      : "hover:border-input"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className={cn(
                        "flex size-4 shrink-0 items-center justify-center rounded-full border",
                        checked ? "border-primary" : "border-input"
                      )}
                    >
                      {checked ? (
                        <span className="size-2 rounded-full bg-primary" />
                      ) : null}
                    </span>
                    <span className="text-sm font-medium">{policy.title}</span>
                  </span>
                  <span className="mt-2 block text-sm text-muted-foreground">
                    {policy.summary}
                  </span>
                </button>
              );
            })}
          </div>

          {mode === "AUTO_BELOW_LIMIT" ? (
            <div className="max-w-xs space-y-2">
              <Label htmlFor="policy-max">Maximum amount (INR)</Label>
              <Input
                id="policy-max"
                type="number"
                min="0"
                step="0.01"
                inputMode="decimal"
                className="tnum"
                value={maxRupees}
                onChange={(e) => {
                  setMaxRupees(e.target.value);
                  setSavedNotice(false);
                }}
                placeholder="1000"
              />
              {maxAmountInvalid ? (
                <p className="text-sm text-destructive" role="alert">
                  Enter an amount greater than zero.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Purchases at or below this amount may be accepted
                  automatically.
                </p>
              )}
            </div>
          ) : null}

          <div className="rounded-md border bg-muted/50 p-3">
            <p className="text-xs font-medium text-muted-foreground">
              What this means
            </p>
            <p className="mt-1 text-sm">{selected.consequence}</p>
          </div>

          <div className="flex flex-col items-end gap-2">
            {!dirty && !saving && (
              <p className="text-xs text-muted-foreground">No changes to save</p>
            )}
            {maxAmountInvalid && (
              <p className="text-xs text-destructive">Enter a valid maximum amount (greater than ₹0)</p>
            )}
            <Button
              onClick={() => void handleSave()}
              disabled={!dirty || saving || maxAmountInvalid}
            >
              {saving ? "Saving…" : "Save policy"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
