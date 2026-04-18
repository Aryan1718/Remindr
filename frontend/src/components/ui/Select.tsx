import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "w-full border border-white/22 bg-black px-4 py-3 text-sm uppercase tracking-[0.05em] text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
        props.className,
      )}
    />
  );
}
