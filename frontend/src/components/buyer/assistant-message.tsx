interface AssistantMessageProps {
  text: string;
}

export function AssistantMessage({ text }: AssistantMessageProps) {
  return (
    <div className="flex">
      <div className="max-w-[85%]">
        <p className="mb-1 text-xs font-medium text-muted-foreground">
          Assistant
        </p>
        <p className="text-sm leading-6 text-foreground">{text}</p>
      </div>
    </div>
  );
}
