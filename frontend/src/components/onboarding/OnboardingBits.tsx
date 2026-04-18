import { Check, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { OnboardingDraft } from "@/types/domain";
import { formatTime } from "@/lib/utils";

const steps = [
  "Welcome",
  "Basic profile",
  "Routine",
  "Decision preferences",
  "Initial goal",
  "Connectors",
  "Telegram setup",
  "Finish",
];

export function StepProgress({ currentStep }: { currentStep: number }) {
  return (
    <Card variant="standard" className="rounded-panel">
      <p className="text-xs uppercase tracking-[0.18em] text-muted">Onboarding progress</p>
      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {steps.map((step, index) => (
          <div className="rounded-card border border-border p-3" key={step}>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-surface-alt text-xs font-semibold text-ink">
                {index < currentStep ? <Check className="h-4 w-4" /> : index + 1}
              </div>
              <p className="text-sm font-medium text-ink">{step}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function OnboardingSummary({ draft }: { draft: OnboardingDraft }) {
  return (
    <Card variant="elevated" className="rounded-panel">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted">Finish</p>
          <h3 className="mt-2 font-display text-3xl tracking-[-0.03em] text-ink">
            The assistant is ready to start nudging.
          </h3>
        </div>
        <ChevronRight className="h-5 w-5 text-muted" />
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-card border border-border p-4">
          <p className="text-sm font-semibold text-ink">Routine</p>
          <p className="mt-2 text-sm text-muted">
            Wake {formatTime(draft.wakeTime)}, sleep {formatTime(draft.sleepTime)}
          </p>
          <p className="mt-1 text-sm text-muted">Best focus: {draft.focusWindow}</p>
        </div>
        <div className="rounded-card border border-border p-4">
          <p className="text-sm font-semibold text-ink">Primary channel</p>
          <p className="mt-2 text-sm text-muted">
            Telegram {draft.telegramConnected ? "connected" : "not connected"}
          </p>
          <p className="mt-1 text-sm text-muted">Connectors: {draft.connectors.join(", ") || "none yet"}</p>
        </div>
      </div>
    </Card>
  );
}
