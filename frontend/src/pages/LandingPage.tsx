import {
  ArrowRight,
  CalendarDays,
  Mail,
  MessageCircleMore,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";

const navItems = ["About", "Flow", "Docs"];

const stats = [
  { label: "Calendar", value: "2 sources" },
  { label: "Email", value: "18 threads" },
  { label: "Channel", value: "Telegram" },
];

const infraItems = [
  {
    icon: CalendarDays,
    title: "Calendar context",
    text: "Meetings, commitments, and real free space become machine-readable before planning starts.",
  },
  {
    icon: Mail,
    title: "Email pressure",
    text: "Urgency, follow-ups, and timing-sensitive threads are pulled into the assistant's reasoning layer.",
  },
  {
    icon: MessageCircleMore,
    title: "Telegram delivery",
    text: "The daily loop stays in channel, while the web app remains a setup and visibility surface.",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <div className="mx-auto max-w-7xl border-x border-white/10">
        <header className="border-b border-white/10">
          <div className="flex items-center justify-between gap-6 px-6 py-6 lg:px-8">
            <div className="flex items-center gap-10">
              <Link className="flex items-center gap-3" to="/">
                <div className="grid h-9 w-9 place-items-center border border-white/16 bg-surface-alt">
                  <div className="relative h-4 w-4">
                    <span className="absolute left-1/2 top-0 h-full w-[2px] -translate-x-1/2 bg-white" />
                    <span className="absolute top-1/2 h-[2px] w-full -translate-y-1/2 bg-white" />
                    <span className="absolute left-1 top-1 h-2 w-2 border-l-2 border-t-2 border-accent" />
                  </div>
                </div>
                <div>
                  <p className="font-display text-3xl uppercase tracking-[0.04em] text-white">
                    DaFUK Assistant
                  </p>
                </div>
              </Link>

              <nav className="hidden items-center gap-8 lg:flex">
                {navItems.map((item) => (
                  <a
                    className="text-sm uppercase tracking-[0.14em] text-white/72 transition hover:text-white"
                    href="#"
                    key={item}
                  >
                    {item}
                  </a>
                ))}
              </nav>
            </div>

            <div className="hidden items-center gap-6 lg:flex">
              <Link to="/start">
                <Button type="button">Start setup</Button>
              </Link>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-4 border-b border-white/10">
          {[0, 1, 2, 3].map((item) => (
            <div className="h-10 border-r border-dashed border-white/10 last:border-r-0" key={item} />
          ))}
        </div>

        <section className="border-b border-white/10 px-6 py-6 lg:px-8">
          <div className="inline-flex items-center gap-3 border border-white/12 bg-surface-alt px-4 py-2 text-sm uppercase tracking-[0.12em] text-white/82">
            <span className="h-2.5 w-2.5 bg-accent" />
            Landing Flow
            <span className="text-white/52">Home → Onboarding → Connectors → Channel → Dashboard</span>
          </div>
        </section>

        <section className="grid min-h-[calc(100vh-180px)] items-center gap-12 px-6 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:px-8 lg:py-20">
          <div className="max-w-2xl">
            <p className="text-[11px] uppercase tracking-[0.32em] text-faint">Assistant Operating Surface</p>
            <h1 className="mt-6 font-display text-[2.6rem] uppercase leading-[0.96] tracking-[0.02em] text-white md:text-[3.5rem] xl:text-[4.2rem]">
              Your assistant is only as good as the context it can act on.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-white/66">
              Build the control surface first. Capture routine, connect the right sources, link the
              delivery channel, and then open a dashboard that reflects real context instead of empty
              widgets.
            </p>

            <div className="mt-10 flex flex-wrap gap-4">
              <Link to="/start">
                <Button className="gap-2" type="button">
                  Start setup <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Button type="button" variant="secondary">
                View the flow
              </Button>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {stats.map((item) => (
                <div className="border border-white/10 bg-surface-alt px-4 py-4" key={item.label}>
                  <p className="text-[10px] uppercase tracking-[0.22em] text-faint">{item.label}</p>
                  <p className="mt-2 text-sm uppercase tracking-[0.1em] text-white">{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-white/10 bg-surface-alt">
            <div className="grid grid-cols-2 border-b border-white/10">
              <div className="border-r border-white/10 px-6 py-5">
                <p className="text-[10px] uppercase tracking-[0.24em] text-faint">Step 01</p>
                <p className="mt-2 text-base uppercase tracking-[0.08em] text-white">Onboarding</p>
              </div>
              <div className="px-6 py-5">
                <p className="text-[10px] uppercase tracking-[0.24em] text-faint">Step 02</p>
                <p className="mt-2 text-base uppercase tracking-[0.08em] text-white">Connectors</p>
              </div>
            </div>

            <div className="grid grid-cols-2 border-b border-white/10">
              <div className="border-r border-white/10 px-6 py-5">
                <p className="text-[10px] uppercase tracking-[0.24em] text-faint">Step 03</p>
                <p className="mt-2 text-base uppercase tracking-[0.08em] text-white">Channel</p>
              </div>
              <div className="px-6 py-5">
                <p className="text-[10px] uppercase tracking-[0.24em] text-faint">Step 04</p>
                <p className="mt-2 text-base uppercase tracking-[0.08em] text-white">Dashboard</p>
              </div>
            </div>

            <div className="px-6 py-8">
              <p className="text-[10px] uppercase tracking-[0.24em] text-faint">What this home page should do</p>
              <div className="mt-4 space-y-4">
                <div className="border border-white/10 bg-black px-4 py-4">
                  <p className="text-sm uppercase tracking-[0.08em] text-white">Explain the product clearly</p>
                  <p className="mt-2 text-sm leading-7 text-white/60">
                    The user should understand the assistant before entering setup.
                  </p>
                </div>
                <div className="border border-white/10 bg-black px-4 py-4">
                  <p className="text-sm uppercase tracking-[0.08em] text-white">Drive one primary action</p>
                  <p className="mt-2 text-sm leading-7 text-white/60">
                    The only important action here is starting the flow.
                  </p>
                </div>
                <div className="border border-white/10 bg-black px-4 py-4">
                  <p className="text-sm uppercase tracking-[0.08em] text-white">Set expectations for the sequence</p>
                  <p className="mt-2 text-sm leading-7 text-white/60">
                    Home first, then onboarding, connectors, channel, and dashboard after completion.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid border-t border-white/10 lg:grid-cols-3">
          {infraItems.map((item) => {
            const Icon = item.icon;

            return (
              <div className="border-b border-r border-white/10 px-6 py-8 last:border-r-0 lg:border-b-0 lg:px-8" key={item.title}>
                <Icon className="h-5 w-5 text-accent" />
                <p className="mt-5 text-lg uppercase tracking-[0.1em] text-white">{item.title}</p>
                <p className="mt-3 max-w-md text-sm leading-7 text-white/60">{item.text}</p>
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
