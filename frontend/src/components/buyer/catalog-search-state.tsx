"use client";

import { Loader2 } from "lucide-react";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface CatalogSearchStateProps {
  state: "searching" | "empty" | "error";
  merchantName: string;
  onRetry?: () => void;
}

export function CatalogSearchState({
  state,
  merchantName,
  onRetry,
}: CatalogSearchStateProps) {
  if (state === "searching") {
    return (
      <div
        className="flex items-center gap-2 text-sm text-muted-foreground"
        role="status"
      >
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Searching {merchantName} catalog…
      </div>
    );
  }

  if (state === "empty") {
    return (
      <p className="text-sm text-muted-foreground">
        No matching published products found. Try changing your request.
      </p>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTitle>We couldn&apos;t search the catalog right now.</AlertTitle>
      <AlertDescription className="mt-2">
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </AlertDescription>
    </Alert>
  );
}
