"use client";

import { useState } from "react";
import { SendHorizonal, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface BuyerComposerProps {
  disabled: boolean;
  initialized: boolean;
  onSend: (text: string) => void;
}

export function BuyerComposer({ disabled, initialized, onSend }: BuyerComposerProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const isInitializing = !initialized;

  return (
    <div className="flex flex-col gap-2">
      <form
        className="flex items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={isInitializing ? "Loading..." : "Ask about products…"}
          disabled={disabled}
          aria-label="Message the shopping assistant"
          autoComplete="off"
          className={isInitializing ? "animate-pulse" : ""}
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <SendHorizonal aria-hidden />
        </Button>
      </form>
      {isInitializing && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" aria-hidden />
          <span>Initializing shopping assistant...</span>
        </div>
      )}
    </div>
  );
}
