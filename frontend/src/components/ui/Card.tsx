import type { HTMLAttributes, PropsWithChildren } from "react";
import { cn } from "@/lib/cn";

type CardVariant = "standard" | "elevated" | "warm" | "clickable";

const variants: Record<CardVariant, string> = {
  standard: "border border-border bg-surface-alt",
  elevated: "border border-border bg-surface-elevated",
  warm: "border border-border bg-surface",
  clickable: "border border-border bg-surface-alt transition hover:border-white/30 hover:bg-surface-elevated",
};

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

export function Card({
  children,
  className,
  variant = "standard",
  ...props
}: PropsWithChildren<CardProps>) {
  return (
    <div className={cn("rounded-card p-5", variants[variant], className)} {...props}>
      {children}
    </div>
  );
}
