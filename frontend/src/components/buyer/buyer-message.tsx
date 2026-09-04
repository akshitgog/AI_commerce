interface BuyerMessageProps {
  text: string;
}

export function BuyerMessage({ text }: BuyerMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%]">
        <p className="mb-1 text-right text-xs font-medium text-muted-foreground">
          You
        </p>
        <div className="rounded-lg bg-primary px-3.5 py-2 text-sm text-primary-foreground shadow-sm">
          {text}
        </div>
      </div>
    </div>
  );
}
