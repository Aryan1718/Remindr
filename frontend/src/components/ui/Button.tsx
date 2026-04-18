import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variants: Record<ButtonVariant, string> = {
  primary: "border border-accent bg-accent text-black hover:border-accent-strong hover:bg-accent-strong hover:text-black",
  secondary: "border border-white/50 bg-transparent text-white/90 hover:border-focus hover:bg-[#1eaedb] hover:text-white",
  ghost: "border border-transparent bg-transparent text-white/80 hover:border-white/20 hover:bg-white/5 hover:text-white",
  danger: "border border-danger/40 bg-transparent text-danger hover:bg-danger hover:text-black",
};

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <button
      className={cn(
        "inline-flex min-h-12 items-center justify-center px-6 py-3 text-[13px] font-medium uppercase tracking-[0.18em] transition duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
