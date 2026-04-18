import { ConnectorStatusCard, DeadlineList, FocusCard, ScheduleChangeList, SuggestionCard } from "@/components/dashboard/DashboardBits";
import { PageContainer } from "@/components/layout/PageContainer";
import { SectionBlock } from "@/components/layout/SectionBlock";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useDashboardQuery } from "@/features/dashboard/queries";

export function DashboardPage() {
  const { data, isLoading } = useDashboardQuery();

  return (
    <PageContainer
      title="Dashboard"
      description="A limited command surface showing what matters now, what changed, and how the assistant is steering the next few hours."
    >
      {isLoading || !data ? (
        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <LoadingSkeleton className="h-80" />
          <LoadingSkeleton className="h-80" />
        </div>
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <FocusCard tasks={data.todayFocus} />
            <ConnectorStatusCard connectors={data.connectors} />
          </div>

          <SectionBlock
            title="Suggestions"
            description="These blocks explain the assistant's current recommendations without replacing the Telegram flow."
          >
            {data.suggestions.length ? (
              <div className="grid gap-6 lg:grid-cols-2">
                {data.suggestions.map((suggestion) => (
                  <SuggestionCard key={suggestion.id} suggestion={suggestion} />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No recommendations right now"
                description="The assistant is quiet when there is nothing useful to say."
              />
            )}
          </SectionBlock>

          <div className="grid gap-6 lg:grid-cols-2">
            <DeadlineList tasks={data.deadlines} />
            <ScheduleChangeList changes={data.scheduleChanges} />
          </div>
        </>
      )}
    </PageContainer>
  );
}
