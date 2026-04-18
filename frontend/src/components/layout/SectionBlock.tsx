import type { PropsWithChildren, ReactNode } from "react";

export function SectionBlock({
  title,
  description,
  action,
  children,
}: PropsWithChildren<{ title: string; description?: string; action?: ReactNode }>) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-display text-3xl uppercase leading-[1.02] tracking-[0.04em] text-ink">{title}</h2>
          {description ? <p className="mt-2 max-w-2xl text-sm leading-7 text-faint">{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
