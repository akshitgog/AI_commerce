"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ExpiredProposalCardProps {
  busy: boolean;
  onCreateNew: () => void;
}

export function ExpiredProposalCard({
  busy,
  onCreateNew,
}: ExpiredProposalCardProps) {
  return (
    <Card className="bg-warning">
      <CardHeader className="p-5 pb-3">
        <p className="text-xs font-medium uppercase tracking-wide text-warning">
          Purchase Proposal
        </p>
        <CardTitle className="text-base">Proposal expired</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 p-5 pt-0">
        <p className="text-sm text-muted-foreground">
          The purchase proposal is no longer valid. Product price, stock or
          availability may have changed.
        </p>
        <div>
          <Button size="sm" onClick={onCreateNew} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" aria-hidden /> : null}
            Create new proposal
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
