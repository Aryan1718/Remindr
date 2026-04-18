import type { PropsWithChildren } from "react";
import { Card } from "@/components/ui/Card";

export function Modal({
  open,
  onClose,
  title,
  children,
}: PropsWithChildren<{ open: boolean; onClose: () => void; title: string }>) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 p-4 backdrop-blur-sm">
      <div className="absolute inset-0" onClick={onClose} />
      <Card variant="elevated" className="relative z-10 w-full max-w-2xl rounded-panel p-0 shadow-deep">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="font-display text-2xl text-ink">{title}</h2>
          <button className="text-sm text-muted" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div className="p-6">{children}</div>
      </Card>
    </div>
  );
}
