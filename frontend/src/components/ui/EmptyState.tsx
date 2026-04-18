import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <Card variant="warm" className="rounded-panel border-dashed text-center">
      <p className="font-display text-2xl uppercase tracking-[0.06em] text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-7 text-faint">{description}</p>
      {actionLabel && onAction ? (
        <Button className="mt-5" onClick={onAction} type="button" variant="secondary">
          {actionLabel}
        </Button>
      ) : null}
    </Card>
  );
}
