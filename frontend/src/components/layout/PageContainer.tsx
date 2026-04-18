import type { PropsWithChildren, ReactNode } from "react";

export function PageContainer({
  title,
  description,
  actions,
  children,
}: PropsWithChildren<{
  title: string;
  description: string;
  actions?: ReactNode;
}>) {
  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 md:px-8 md:py-10">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Assistant control panel</p>
          <h1 className="font-display text-4xl uppercase leading-[0.95] tracking-[0.02em] text-ink md:text-6xl">
            {title}
          </h1>
          <p className="max-w-2xl text-sm leading-7 text-faint">{description}</p>
        </div>
        {actions}
      </div>
      {children}
    </div>
  );
}
