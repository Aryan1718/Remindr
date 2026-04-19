import { useMemo, useState } from "react";
import { Eye, EyeOff, Lock, Mail, Phone, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { AuthHeader, AuthShell, AuthSocialButtons, authFieldClassName } from "@/components/auth/AuthShell";
import { getAuthErrorMessage, validateEmail, validatePassword, validateRequired } from "@/lib/authValidation";
import { getPostLoginRoute, useAuthStore } from "@/stores/authStore";

function fieldClass(hasError: boolean) {
  return hasError ? `${authFieldClassName} border-red-400/60 focus:border-red-400/70 focus:ring-red-400/40` : authFieldClassName;
}

export function SignupPage() {
  const navigate = useNavigate();
  const signup = useAuthStore((state) => state.signup);
  const authError = useAuthStore((state) => state.error);
  const clearAuthError = useAuthStore((state) => state.clearError);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [contact, setContact] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    fullName?: string;
    email?: string;
    contact?: string;
    password?: string;
  }>({});

  const submitDisabled = useMemo(
    () =>
      isSubmitting ||
      fullName.trim().length === 0 ||
      email.trim().length === 0 ||
      contact.trim().length === 0 ||
      password.trim().length === 0,
    [contact, email, fullName, isSubmitting, password],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextFieldErrors = {
      fullName: validateRequired(fullName, "Full name") ?? undefined,
      email: validateEmail(email) ?? undefined,
      contact: validateRequired(contact, "Contact") ?? undefined,
      password: validatePassword(password, { minimumLength: 6, required: true }) ?? undefined,
    };

    setFieldErrors(nextFieldErrors);
    if (nextFieldErrors.fullName || nextFieldErrors.email || nextFieldErrors.contact || nextFieldErrors.password) {
      return;
    }

    setIsSubmitting(true);
    setPageError(null);
    setPageMessage(null);
    clearAuthError();

    try {
      const result = await signup({
        fullName: fullName.trim(),
        email: email.trim(),
        contact: contact.trim(),
        password,
        rememberMe: true,
      });

      if (result.requiresEmailConfirmation) {
        setPageMessage("Account created. Check your email to confirm your account before signing in.");
        return;
      }

      navigate(getPostLoginRoute(result.snapshot), { replace: true });
    } catch (error) {
      setPageError(getAuthErrorMessage(error, authError || "Unable to create account"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell maxWidthClassName="max-w-[32rem] sm:max-w-[34rem] lg:max-w-[35rem] xl:max-w-[36rem]">
      <AuthHeader
        description="Create your account to start setting up your assistant workflow"
        subtitle="Create your account"
      />

      <form className="relative space-y-4 sm:space-y-5" onSubmit={handleSubmit}>
        {pageError ? (
          <div className="rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {pageError}
          </div>
        ) : null}

        {pageMessage ? (
          <div className="rounded-2xl border border-cyan-400/25 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-100">
            {pageMessage}
          </div>
        ) : null}

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
              className={`${fieldClass(Boolean(fieldErrors.fullName))} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-name"
              onBlur={() =>
                setFieldErrors((current) => ({
                  ...current,
                  fullName: validateRequired(fullName, "Full name") ?? undefined,
                }))
              }
              onChange={(event) => {
                setFullName(event.target.value);
                if (fieldErrors.fullName || pageError) {
                  setFieldErrors((current) => ({
                    ...current,
                    fullName: validateRequired(event.target.value, "Full name") ?? undefined,
                  }));
                  setPageError(null);
                }
              }}
              placeholder="Your full name"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="text"
              value={fullName}
            />
          </div>
          {fieldErrors.fullName ? <p className="mt-2 text-sm text-red-200">{fieldErrors.fullName}</p> : null}
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
              className={`${fieldClass(Boolean(fieldErrors.email))} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-email"
              onBlur={() =>
                setFieldErrors((current) => ({
                  ...current,
                  email: validateEmail(email) ?? undefined,
                }))
              }
              onChange={(event) => {
                setEmail(event.target.value);
                if (fieldErrors.email || pageError) {
                  setFieldErrors((current) => ({
                    ...current,
                    email: validateEmail(event.target.value) ?? undefined,
                  }));
                  setPageError(null);
                }
              }}
              placeholder="you@example.com"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="email"
              value={email}
            />
          </div>
          {fieldErrors.email ? <p className="mt-2 text-sm text-red-200">{fieldErrors.email}</p> : null}
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
              className={`${fieldClass(Boolean(fieldErrors.contact))} pl-10 pr-4 text-sm sm:text-base`}
              id="signup-contact"
              onBlur={() =>
                setFieldErrors((current) => ({
                  ...current,
                  contact: validateRequired(contact, "Contact") ?? undefined,
                }))
              }
              onChange={(event) => {
                setContact(event.target.value);
                if (fieldErrors.contact || pageError) {
                  setFieldErrors((current) => ({
                    ...current,
                    contact: validateRequired(event.target.value, "Contact") ?? undefined,
                  }));
                  setPageError(null);
                }
              }}
              placeholder="+1 (555) 123-4567"
              style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
              type="tel"
              value={contact}
            />
          </div>
          {fieldErrors.contact ? <p className="mt-2 text-sm text-red-200">{fieldErrors.contact}</p> : null}
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
              className={`${fieldClass(Boolean(fieldErrors.password))} pl-10 pr-12 text-sm sm:text-base`}
              id="signup-password"
              onBlur={() =>
                setFieldErrors((current) => ({
                  ...current,
                  password: validatePassword(password, { minimumLength: 6, required: true }) ?? undefined,
                }))
              }
              onChange={(event) => {
                setPassword(event.target.value);
                if (fieldErrors.password || pageError) {
                  setFieldErrors((current) => ({
                    ...current,
                    password: validatePassword(event.target.value, { minimumLength: 6, required: true }) ?? undefined,
                  }));
                  setPageError(null);
                }
              }}
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
          {fieldErrors.password ? <p className="mt-2 text-sm text-red-200">{fieldErrors.password}</p> : null}
          {!fieldErrors.password ? (
            <p className="mt-2 text-sm text-gray-400">Use at least 6 characters to meet Supabase password rules.</p>
          ) : null}
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
          {isSubmitting ? "Creating account..." : "Create Account"}
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
