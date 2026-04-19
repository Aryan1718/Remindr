import { useMemo, useState } from "react";
import { Eye, EyeOff, Lock, Mail, Phone, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { AuthHeader, AuthShell, AuthSocialButtons, authFieldClassName } from "@/components/auth/AuthShell";
import { useSaveOnboardingMutation } from "@/features/onboarding/mutations";
import { useOnboardingQuery } from "@/features/onboarding/queries";
import type { OnboardingDraft } from "@/types/domain";

function createSignupDraft(fullName: string, currentDraft?: OnboardingDraft): OnboardingDraft {
  return {
    stage: "onboarding",
    name: fullName.trim(),
    timezone: "UTC-8 (Pacific Time)",
    role: "professional",
    bio: "",
    wakeTime: "07:00",
    sleepTime: "23:00",
    workStart: "09:00",
    workEnd: "17:00",
    workHours: "09:00 - 17:00",
    commitments: "",
    focusWindow: "morning",
    weekendPattern: "flexible",
    decisionStyle: "Ranked options",
    reminderTolerance: "Balanced",
    fatigueCheckIn: "Daily",
    recommendationStyle: "Balanced",
    reminderStyle: "Gentle",
    notificationFrequency: "Moderate",
    quietHoursStart: "22:00",
    quietHoursEnd: "08:00",
    goalTitle: currentDraft?.goalTitle ?? "",
    goalHorizon: currentDraft?.goalHorizon ?? "",
    goalImportance: currentDraft?.goalImportance ?? "Medium",
    goalNotes: currentDraft?.goalNotes ?? "",
    tasks: [],
    connectors: [],
    telegramConnected: false,
    completed: false,
  };
}

export function SignupPage() {
  const navigate = useNavigate();
  const { data: onboardingDraft, isLoading } = useOnboardingQuery();
  const saveOnboardingMutation = useSaveOnboardingMutation();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const submitDisabled = useMemo(
    () =>
      isLoading ||
      saveOnboardingMutation.isPending ||
      fullName.trim().length === 0 ||
      email.trim().length === 0 ||
      contact.trim().length === 0 ||
      password.trim().length === 0,
    [contact, email, fullName, isLoading, password, saveOnboardingMutation.isPending],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitDisabled) return;

    await saveOnboardingMutation.mutateAsync(createSignupDraft(fullName, onboardingDraft));
    navigate("/onboarding");
  }

  return (
    <AuthShell maxWidthClassName="max-w-[32rem] sm:max-w-[34rem] lg:max-w-[35rem] xl:max-w-[36rem]">
      <AuthHeader
        description="Create your account to start setting up your assistant workflow"
        subtitle="Create your account"
      />

      <form className="relative space-y-4 sm:space-y-5" onSubmit={handleSubmit}>
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="signup-name">
            Full name
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <User className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="name"
              className={`${authFieldClassName} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-name"
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Your full name"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="text"
              value={fullName}
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="signup-email">
            Email
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Mail className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="email"
              className={`${authFieldClassName} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="email"
              value={email}
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="signup-contact">
            Contact
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Phone className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="tel"
              className={`${authFieldClassName} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-contact"
              onChange={(event) => setContact(event.target.value)}
              placeholder="+1 (555) 123-4567"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="tel"
              value={contact}
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="signup-password">
            Password
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Lock className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="new-password"
              className={`${authFieldClassName} pl-10 pr-12 text-sm sm:text-base`}
              id="signup-password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a password"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type={showPassword ? "text" : "password"}
              value={password}
            />
            <button
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 transition-colors hover:text-gray-300"
              onClick={() => setShowPassword((current) => !current)}
              type="button"
            >
              {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>

        <button
          className="w-full rounded-xl px-4 py-3 text-sm font-medium text-white transition duration-200 hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98] sm:text-base"
          disabled={submitDisabled}
          style={{
            background:
              "linear-gradient(135deg, rgba(60, 160, 230, 1) 0%, rgba(40, 120, 200, 1) 100%)",
            boxShadow:
              "0 4px 20px rgba(60, 160, 230, 0.4), inset 0 1px 1px rgba(255, 255, 255, 0.2)",
          }}
          type="submit"
        >
          {saveOnboardingMutation.isPending ? "Creating account..." : "Create Account"}
        </button>

        <AuthSocialButtons mode="signup" />
      </form>

      <div className="relative mt-5 text-center sm:mt-6">
        <p className="text-sm text-gray-400">
          Already have an account?{" "}
          <Link className="font-medium text-cyan-400 transition-colors hover:text-cyan-300" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
