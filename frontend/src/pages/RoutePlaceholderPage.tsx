import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function RoutePlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="min-h-screen bg-black px-4 py-8 text-white sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl items-center justify-center">
        <Card
          className="w-full rounded-[28px] border-white/10 bg-[rgba(12,18,32,0.84)] p-8 text-center shadow-2xl sm:p-10"
          variant="elevated"
        >
          <p className="text-[11px] uppercase tracking-[0.28em] text-cyan-300/75">
            Screen in redesign
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-white sm:text-5xl">{title}</h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-8 text-gray-300">{description}</p>
          <p className="mx-auto mt-5 max-w-lg text-sm leading-7 text-gray-400">
            The previous UI for this route has been removed from the live app surface. Send the next
            Figma screen and this placeholder will be replaced.
          </p>
          <div className="mt-8 flex justify-center">
            <Link to="/login">
              <Button type="button">Back to login</Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
