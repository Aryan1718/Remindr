import { Link } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function NotFoundPage() {
  return (
    <PageContainer title="Not found" description="This route does not exist in the current frontend shell.">
      <Card variant="elevated" className="rounded-panel text-center">
        <p className="font-display text-5xl tracking-[-0.04em] text-ink">404</p>
        <p className="mt-3 text-sm text-muted">Return to the dashboard and continue from a stable route.</p>
        <Link className="mt-6 inline-block" to="/dashboard">
          <Button type="button">Go to dashboard</Button>
        </Link>
      </Card>
    </PageContainer>
  );
}
