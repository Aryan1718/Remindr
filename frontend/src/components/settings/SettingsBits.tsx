import type { PropsWithChildren } from "react";
import { Card } from "@/components/ui/Card";

export function SettingsSection({
  title,
  description,
  children,
}: PropsWithChildren<{ title: string; description: string }>) {
  return (
    <Card variant="standard" className="rounded-panel">
      <div className="mb-5">
        <h3 className="font-display text-2xl text-ink">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </Card>
  );
}

export function ToggleRow({
  label,
  description,
}: {
  label: string;
  description: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-card border border-border p-4">
      <div>
        <p className="text-sm font-semibold text-ink">{label}</p>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>
      <div className="h-7 w-12 rounded-full bg-[#d6ecff] p-1">
        <div className="ml-auto h-5 w-5 rounded-full bg-accent" />
      </div>
    </div>
  );
}
