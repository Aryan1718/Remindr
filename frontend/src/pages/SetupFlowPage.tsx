import { ArrowRight, Check, Link2, MessageCircle } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useSaveOnboardingMutation } from "@/features/onboarding/mutations";
import { useOnboardingQuery } from "@/features/onboarding/queries";
import type { OnboardingDraft } from "@/types/domain";

const schema = z.object({
  stage: z.enum(["onboarding", "connectors", "channel", "complete"]),
  name: z.string().min(1),
  timezone: z.string().min(1),
  role: z.string().min(1),
  wakeTime: z.string().min(1),
  sleepTime: z.string().min(1),
  workHours: z.string().min(1),
  commitments: z.string().min(1),
  focusWindow: z.string().min(1),
  decisionStyle: z.enum(["Direct recommendation", "Ranked options"]),
  reminderTolerance: z.enum(["Light", "Balanced", "High"]),
  fatigueCheckIn: z.enum(["Daily", "Only when needed", "Manual only"]),
  goalTitle: z.string(),
  goalHorizon: z.string(),
  goalImportance: z.enum(["Low", "Medium", "High"]),
  goalNotes: z.string(),
  connectors: z.array(z.enum(["calendar", "gmail"])),
  telegramConnected: z.boolean(),
  completed: z.boolean(),
});

const stageMeta = [
  {
    eyebrow: "Start",
    title: "Basic onboarding",
    text: "Collect the smallest reusable context set first.",
  },
  {
    eyebrow: "Connectors",
    title: "Connect the sources",
    text: "Link calendar and email before the channel step.",
  },
  {
    eyebrow: "Channel",
    title: "Link Telegram",
    text: "Finish setup by connecting the primary communication channel.",
  },
];

const onboardingQuestions = [
  {
    field: "name",
    label: "What should the assistant call you?",
    hint: "This becomes the default name across setup and assistant messages.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("name")} />,
  },
  {
    field: "timezone",
    label: "What timezone should the assistant schedule around?",
    hint: "Use a city or timezone label like PST, EST, or America/Los_Angeles.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("timezone")} />,
  },
  {
    field: "role",
    label: "What best describes your current context?",
    hint: "This helps the assistant frame the language and timing of recommendations.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Select autoFocus {...form.register("role")}>
        <option>Student</option>
        <option>Job seeker</option>
        <option>Professional</option>
        <option>Other</option>
      </Select>
    ),
  },
  {
    field: "wakeTime",
    label: "When do you usually wake up?",
    hint: "This sets the earliest realistic time for nudges or suggestions.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Input autoFocus type="time" {...form.register("wakeTime")} />
    ),
  },
  {
    field: "sleepTime",
    label: "When do you usually stop for the day?",
    hint: "The assistant uses this to avoid pushing too late.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Input autoFocus type="time" {...form.register("sleepTime")} />
    ),
  },
  {
    field: "workHours",
    label: "What are your usual work or class hours?",
    hint: "A simple range is enough. Example: 9am to 5pm.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("workHours")} />,
  },
  {
    field: "commitments",
    label: "What recurring commitments should the assistant respect?",
    hint: "Classes, gym, pickups, prayer, study blocks, anything that repeats.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Textarea autoFocus {...form.register("commitments")} />,
  },
  {
    field: "focusWindow",
    label: "When do you usually do your best focused work?",
    hint: "This helps the system place demanding work in the right window.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("focusWindow")} />,
  },
  {
    field: "decisionStyle",
    label: "How should the assistant make recommendations?",
    hint: "Direct recommendation is faster. Ranked options gives you more control.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Select autoFocus {...form.register("decisionStyle")}>
        <option>Direct recommendation</option>
        <option>Ranked options</option>
      </Select>
    ),
  },
  {
    field: "reminderTolerance",
    label: "How much reminder pressure feels acceptable?",
    hint: "This shapes how persistent the assistant should be when timing matters.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Select autoFocus {...form.register("reminderTolerance")}>
        <option>Light</option>
        <option>Balanced</option>
        <option>High</option>
      </Select>
    ),
  },
  {
    field: "fatigueCheckIn",
    label: "How often should the assistant check in on fatigue?",
    hint: "Choose how much explicit energy-checking you want in the loop.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Select autoFocus {...form.register("fatigueCheckIn")}>
        <option>Daily</option>
        <option>Only when needed</option>
        <option>Manual only</option>
      </Select>
    ),
  },
  {
    field: "goalTitle",
    label: "What is one goal the assistant should keep in view?",
    hint: "This one is optional. Leave it blank if you want to skip it for now.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("goalTitle")} />,
  },
  {
    field: "goalHorizon",
    label: "What time horizon fits that goal?",
    hint: "Example: this week, this month, this quarter.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Input autoFocus {...form.register("goalHorizon")} />,
  },
  {
    field: "goalImportance",
    label: "How important is that goal right now?",
    hint: "This helps the assistant decide when to surface related work.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => (
      <Select autoFocus {...form.register("goalImportance")}>
        <option>Low</option>
        <option>Medium</option>
        <option>High</option>
      </Select>
    ),
  },
  {
    field: "goalNotes",
    label: "Any notes the assistant should keep with that goal?",
    hint: "Optional context, constraints, or anything you do not want the system to miss.",
    render: (form: ReturnType<typeof useForm<OnboardingDraft>>) => <Textarea autoFocus {...form.register("goalNotes")} />,
  },
] as const;

export function SetupFlowPage() {
  const navigate = useNavigate();
  const { data } = useOnboardingQuery();
  const mutation = useSaveOnboardingMutation();
  const [questionIndex, setQuestionIndex] = useState(0);
  const form = useForm<OnboardingDraft>({
    resolver: zodResolver(schema),
    values: data,
  });

  useEffect(() => {
    if (data) form.reset(data);
  }, [data, form]);

  useEffect(() => {
    if (data?.stage === "onboarding") {
      setQuestionIndex(0);
    }
  }, [data?.stage]);

  const draft = form.watch();

  const currentStage = useMemo(() => {
    if (draft.stage === "onboarding") return 0;
    if (draft.stage === "connectors") return 1;
    return 2;
  }, [draft.stage]);

  const currentQuestion = onboardingQuestions[questionIndex];
  const questionsLeft = onboardingQuestions.length - (questionIndex + 1);
  const progressPercent = ((questionIndex + 1) / onboardingQuestions.length) * 100;
  const estimatedMinutesLeft = Math.max(1, Math.ceil((questionsLeft * 20) / 60));

  if (!data) {
    return (
      <div className="min-h-screen bg-surface px-4 py-8 md:px-8">
        <Card variant="warm" className="mx-auto max-w-5xl rounded-panel">
          Loading setup flow...
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-4 py-8 md:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <Card variant="standard" className="rounded-panel">
          <div className="grid gap-4 md:grid-cols-3">
            {stageMeta.map((stage, index) => (
              <div className="border border-white/10 p-4" key={stage.title}>
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center border border-white/12 bg-black text-sm font-medium text-ink">
                    {index < currentStage ? <Check className="h-4 w-4" /> : index + 1}
                  </div>
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-faint">
                      {stage.eyebrow}
                    </p>
                    <p className="text-sm font-medium uppercase tracking-[0.08em] text-ink">{stage.title}</p>
                  </div>
                </div>
                <p className="mt-3 text-sm leading-7 text-faint">{stage.text}</p>
              </div>
            ))}
          </div>
        </Card>

        {draft.stage === "onboarding" ? (
          <Card variant="elevated" className="rounded-panel">
            <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Onboarding</p>
            <h1 className="mt-3 font-display text-5xl uppercase leading-[0.92] tracking-[0.04em] text-ink">
              START WITH THE PERSON, NOT THE DASHBOARD.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-faint">
              One question at a time. Finish the reusable context first, then move into connectors.
            </p>
            <div className="mt-8 border border-white/10 bg-black">
              <div className="border-b border-white/10 px-6 py-5">
                <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">
                      Question {questionIndex + 1} of {onboardingQuestions.length}
                    </p>
                    <p className="mt-2 text-sm uppercase tracking-[0.12em] text-white/76">
                      {questionsLeft} {questionsLeft === 1 ? "question" : "questions"} left
                    </p>
                  </div>
                  <div className="text-left md:text-right">
                    <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Estimated time left</p>
                    <p className="mt-2 text-sm uppercase tracking-[0.12em] text-white/76">
                      About {estimatedMinutesLeft} {estimatedMinutesLeft === 1 ? "minute" : "minutes"}
                    </p>
                  </div>
                </div>
                <div className="mt-5 h-2 bg-white/8">
                  <div className="h-full bg-accent transition-all duration-300" style={{ width: `${progressPercent}%` }} />
                </div>
              </div>

              <div className="px-6 py-8 md:px-8 md:py-10">
                <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Current prompt</p>
                <h2 className="mt-4 max-w-3xl font-display text-3xl uppercase leading-[1] tracking-[0.04em] text-ink md:text-4xl">
                  {currentQuestion.label}
                </h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-faint">{currentQuestion.hint}</p>

                <div className="mt-8 max-w-2xl">{currentQuestion.render(form)}</div>

                <div className="mt-8 flex items-center justify-between gap-4">
                  <Button
                    disabled={questionIndex === 0}
                    onClick={() => setQuestionIndex((current) => Math.max(0, current - 1))}
                    type="button"
                    variant="secondary"
                  >
                    Previous
                  </Button>

                  {questionIndex === onboardingQuestions.length - 1 ? (
                    <Button
                      className="gap-2"
                      onClick={form.handleSubmit(async (values) => {
                        await mutation.mutateAsync({
                          ...values,
                          stage: "connectors",
                          completed: false,
                          telegramConnected: false,
                        });
                        setQuestionIndex(0);
                      })}
                      type="button"
                    >
                      Continue to connectors <ArrowRight className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      className="gap-2"
                      onClick={async () => {
                        const isValid = await form.trigger(currentQuestion.field);
                        if (isValid) {
                          setQuestionIndex((current) => Math.min(onboardingQuestions.length - 1, current + 1));
                        }
                      }}
                      type="button"
                    >
                      Next question <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ) : null}

        {draft.stage === "connectors" ? (
          <Card variant="elevated" className="rounded-panel">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Connectors</p>
                <h1 className="mt-3 font-display text-5xl uppercase leading-[0.92] tracking-[0.04em] text-ink">
                  CONNECT THE ASSISTANT INPUTS.
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-faint">
                  This stage should feel explicit: connect the external sources first, then move into the communication channel.
                </p>
              </div>
              <Link2 className="mt-2 h-5 w-5 text-muted" />
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              {[
                {
                  id: "calendar",
                  title: "Google Calendar",
                  text: "Used for routine structure, commitments, and open focus windows.",
                },
                {
                  id: "gmail",
                  title: "Gmail",
                  text: "Used for urgent threads, timing pressure, and follow-up signals.",
                },
              ].map((item) => {
                const selected = draft.connectors.includes(item.id as "calendar" | "gmail");

                return (
                  <button
                    className={`border p-5 text-left transition ${
                      selected ? "border-accent bg-[#161100]" : "border-white/12 bg-black hover:border-white/28 hover:bg-surface-alt"
                    }`}
                    key={item.id}
                    onClick={() => {
                      const next = selected
                        ? draft.connectors.filter((entry) => entry !== item.id)
                        : [...draft.connectors, item.id as "calendar" | "gmail"];
                      form.setValue("connectors", next);
                    }}
                    type="button"
                  >
                    <p className="text-base font-medium uppercase tracking-[0.08em] text-ink">{item.title}</p>
                    <p className="mt-2 text-sm leading-7 text-faint">{item.text}</p>
                    <p className="mt-4 text-[10px] font-medium uppercase tracking-[0.28em] text-faint">
                      {selected ? "Connected in mock flow" : "Tap to connect"}
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="mt-8 flex items-center justify-between gap-4">
              <Button
                onClick={() => form.setValue("stage", "onboarding")}
                type="button"
                variant="secondary"
              >
                Back to onboarding
              </Button>
              <Button
                className="gap-2"
                disabled={!draft.connectors.length}
                onClick={form.handleSubmit(async (values) => {
                  await mutation.mutateAsync({
                    ...values,
                    stage: "channel",
                    completed: false,
                  });
                })}
                type="button"
              >
                Continue to channel <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        ) : null}

        {draft.stage !== "onboarding" ? (
          <Card variant="warm" className="rounded-panel">
            <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Connected sources</p>
            <div className="mt-4 flex flex-wrap gap-3">
              {draft.connectors.map((item) => (
                <span
                  className="inline-flex border border-white/16 bg-black px-3 py-2 text-[10px] font-medium uppercase tracking-[0.22em] text-ink"
                  key={item}
                >
                  {item === "calendar" ? "Google Calendar" : "Gmail"}
                </span>
              ))}
            </div>
          </Card>
        ) : null}

        {draft.stage === "channel" ? (
          <Card variant="elevated" className="rounded-panel">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-[0.3em] text-faint">Channel</p>
                <h1 className="mt-3 font-display text-5xl uppercase leading-[0.92] tracking-[0.04em] text-ink">
                  FINISH BY LINKING TELEGRAM.
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-faint">
                  This is the last required step. After Telegram is linked, the dashboard unlocks and the assistant can move into the daily loop.
                </p>
              </div>
              <MessageCircle className="mt-2 h-5 w-5 text-muted" />
            </div>

            <div className="mt-8 rounded-panel border border-white/12 bg-black p-6">
              <p className="text-base font-medium uppercase tracking-[0.08em] text-ink">Telegram channel status</p>
              <p className="mt-2 text-sm leading-7 text-faint">
                {draft.telegramConnected
                  ? "Telegram is linked in the mock environment."
                  : "Telegram is not linked yet. Link it before opening the dashboard."}
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button
                  onClick={() => form.setValue("telegramConnected", !draft.telegramConnected)}
                  type="button"
                >
                  {draft.telegramConnected ? "Telegram linked" : "Link Telegram"}
                </Button>
                <Button
                  onClick={async () => {
                    await mutation.mutateAsync({
                      ...form.getValues(),
                      stage: "channel",
                      telegramConnected: false,
                      completed: false,
                    });
                  }}
                  type="button"
                  variant="secondary"
                >
                  Save channel step
                </Button>
              </div>
            </div>

            <div className="mt-8 flex items-center justify-between gap-4">
              <Button
                onClick={() => {
                  form.setValue("stage", "connectors");
                  form.setValue("telegramConnected", false);
                }}
                type="button"
                variant="secondary"
              >
                Back to connectors
              </Button>
              <Button
                className="gap-2"
                disabled={!draft.telegramConnected}
                onClick={form.handleSubmit(async (values) => {
                  await mutation.mutateAsync({
                    ...values,
                    stage: "complete",
                    completed: true,
                  });
                  navigate("/dashboard");
                })}
                type="button"
              >
                Open dashboard <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
