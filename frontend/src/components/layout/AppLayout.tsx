import { Menu, X } from "lucide-react";
import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { useUiStore } from "@/stores/uiStore";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Tasks", to: "/tasks" },
  { label: "Goals", to: "/goals" },
  { label: "Integrations", to: "/integrations" },
  { label: "Settings", to: "/settings" },
];

export function AppLayout({ children }: PropsWithChildren) {
  const { sidebarOpen, setSidebarOpen } = useUiStore();

  return (
    <div className="min-h-screen bg-surface">
      <div className="relative flex min-h-screen">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 w-72 border-r border-white/10 bg-black px-5 py-6 transition md:static md:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">DaFUK</p>
              <p className="font-display text-3xl uppercase tracking-[0.08em] text-ink">Assistant</p>
            </div>
            <button className="md:hidden" onClick={() => setSidebarOpen(false)} type="button">
              <X className="h-5 w-5" />
            </button>
          </div>
          <p className="mt-4 max-w-[15rem] text-sm leading-7 text-faint">
            A command surface for visibility, review, and final control after setup is complete.
          </p>
          <nav className="mt-8 space-y-2">
            {navItems.map((item) => (
              <NavLink
                className={({ isActive }) =>
                  cn(
                    "block border border-transparent px-4 py-3 text-[12px] font-medium uppercase tracking-[0.18em] text-white/62 transition hover:border-white/12 hover:bg-surface-alt hover:text-white",
                    isActive && "border-accent bg-surface-alt text-accent",
                  )
                }
                key={item.to}
                onClick={() => setSidebarOpen(false)}
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-8 rounded-panel border border-white/12 bg-surface-alt p-4">
            <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">
              Primary channel
            </p>
            <p className="mt-3 text-base uppercase tracking-[0.08em] text-ink">Telegram is live.</p>
            <p className="mt-2 text-sm leading-7 text-faint">Daily suggestions are handled outside the dashboard.</p>
            <Button className="mt-4 w-full" type="button" variant="secondary">
              Review onboarding
            </Button>
          </div>
        </aside>
        {sidebarOpen ? (
          <button
            aria-label="Close sidebar"
            className="fixed inset-0 z-30 bg-black/20 md:hidden"
            onClick={() => setSidebarOpen(false)}
            type="button"
          />
        ) : null}
        <div className="flex-1">
          <header className="sticky top-0 z-20 border-b border-white/10 bg-black/85 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
              <div>
                <p className="text-[10px] uppercase tracking-[0.3em] text-faint">Today</p>
                <p className="text-sm font-medium uppercase tracking-[0.08em] text-ink">Review the surface. Let Telegram handle the nudging.</p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  aria-label="Open navigation"
                  className="border border-white/20 p-2 md:hidden"
                  onClick={() => setSidebarOpen(true)}
                  type="button"
                >
                  <Menu className="h-5 w-5" />
                </button>
                <Button type="button">Review next move</Button>
              </div>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
