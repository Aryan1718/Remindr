export function LoadingSkeleton({ className = "h-24" }: { className?: string }) {
  return <div className={`animate-pulse rounded-card border border-border bg-surface-alt ${className}`} />;
}
