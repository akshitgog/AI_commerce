"use client";

import { FlaskConical, Store } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export default function SettingsPage() {
  const { state } = useCommerce();

  return (
    <>
      <div>
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">
          Merchant profile and demo environment settings.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="size-4 text-muted-foreground" aria-hidden />
            Merchant profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline justify-between gap-4">
            <span className="text-sm text-muted-foreground">Name</span>
            <span className="text-sm font-medium">{state.merchant.name}</span>
          </div>
          <div className="flex items-baseline justify-between gap-4">
            <span className="text-sm text-muted-foreground">Merchant ID</span>
            <span className="tnum font-mono text-xs">{state.merchant.id}</span>
          </div>
          <div className="flex items-center justify-between gap-4 rounded-md border bg-muted/50 p-3">
            <div className="space-y-0.5">
              <Label
                htmlFor="test-mode"
                className="flex items-center gap-1.5 text-sm font-medium"
              >
                <FlaskConical className="size-3.5 text-muted-foreground" aria-hidden />
                Test Mode
              </Label>
              <p className="text-xs text-muted-foreground">
                Demo fixture — the payment provider runs in test mode. No real
                money moves.
              </p>
            </div>
            <Switch
              id="test-mode"
              checked
              disabled
              aria-label="Test Mode (always on in this demo)"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-sm">Danger zone</CardTitle>
          <CardDescription>
            Account-level destructive operations are not available in this
            prototype.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" disabled className="text-destructive">
            Delete merchant account
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
