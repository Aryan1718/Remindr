import type { PropsWithChildren } from "react";
import { cn } from "@/lib/cn";

export function Badge({
  children,
  tone = "neutral",
}: PropsWithChildren<{ tone?: "neutral" | "success" | "warning" | "danger" | "info" }>) {
  const map = {
    neutral: "border border-white/18 bg-transparent text-white/72",
    success: "border border-success/40 bg-transparent text-success",
    warning: "border border-warning/40 bg-transparent text-warning",
    danger: "border border-danger/40 bg-transparent text-danger",
    info: "border border-focus/40 bg-transparent text-focus",
  };

  return (
    <span className={cn("inline-flex px-3 py-1 text-[10px] font-medium uppercase tracking-[0.22em]", map[tone])}>
      {children}
    </span>
  );
}
