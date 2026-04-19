import { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { beginSupabaseOAuth, type SupportedOAuthProvider } from "@/api/supabase";
import {
  AuthHeader,
  AuthShell,
  AuthSocialButtons,
  authFieldClassName,
  type AuthSocialProvider,
} from "@/components/auth/AuthShell";
import { getAuthErrorMessage, validateEmail, validatePassword } from "@/lib/authValidation";
import { getPostLoginRoute, useAuthStore } from "@/stores/authStore";

function fieldClass(hasError: boolean) {
  return hasError ? `${authFieldClassName} border-red-400/60 focus:border-red-400/70 focus:ring-red-400/40` : authFieldClassName;
}

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [oauthPendingProvider, setOauthPendingProvider] = useState<SupportedOAuthProvider | null>(null);
  const authError = useAuthStore((state) => state.error);
  const clearAuthError = useAuthStore((state) => state.clearError);
  const completeOAuthLogin = useAuthStore((state) => state.completeOAuthLogin);
  const login = useAuthStore((state) => state.login);

  const submitDisabled = useMemo(
    () => isSubmitting || email.trim().length === 0 || password.trim().length === 0,
    [email, isSubmitting, password],
  );

  const redirectPath = searchParams.get("redirect");

  useEffect(() => {
    if (authError) {
      setPageError(authError);
    }
  }, [authError]);

  useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const accessToken = hashParams.get("access_token");

    if (!accessToken) {
      return;
    }

    const refreshToken = hashParams.get("refresh_token");
    setIsSubmitting(true);
    setPageError(null);

    void completeOAuthLogin({ accessToken, refreshToken })
      .then((snapshot) => {
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
        navigate(redirectPath || getPostLoginRoute(snapshot), { replace: true });
      })
      .catch((error) => {
        setPageError(error instanceof Error ? error.message : "Unable to complete sign in");
      })
      .finally(() => {
        setIsSubmitting(false);
        setOauthPendingProvider(null);
      });
  }, [completeOAuthLogin, navigate, redirectPath]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextFieldErrors = {
      email: validateEmail(email) ?? undefined,
      password: validatePassword(password, { minimumLength: 6, required: true }) ?? undefined,
    };

    setFieldErrors(nextFieldErrors);
    if (nextFieldErrors.email || nextFieldErrors.password) {
      return;
    }

    setIsSubmitting(true);
    setPageError(null);
    clearAuthError();

    try {
      const snapshot = await login({ email: email.trim(), password, rememberMe });
      navigate(redirectPath || getPostLoginRoute(snapshot), { replace: true });
    } catch (error) {
      setPageError(getAuthErrorMessage(error, "Unable to sign in"));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleOAuth(provider: AuthSocialProvider) {
    setIsSubmitting(true);
    setPageError(null);
    setOauthPendingProvider(provider as SupportedOAuthProvider);
    beginSupabaseOAuth(provider as SupportedOAuthProvider);
  }

  return (
    <AuthShell>
      <AuthHeader description="Sign in to access your assistant dashboard" subtitle="Welcome back" />

      <form className="relative space-y-5 sm:space-y-6" onSubmit={handleSubmit}>
        {pageError ? (
          <div className="rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {pageError}
          </div>
        ) : null}

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="email">
            Email
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Mail className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="email"
              className={`${fieldClass(Boolean(fieldErrors.email))} pl-10 pr-4 text-sm sm:text-base`}
              id="email"
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
          <label className="mb-2 block text-sm font-medium text-gray-300" htmlFor="password">
            Password
          </label>
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Lock className="h-5 w-5 text-gray-500" />
            </div>
            <input
              autoComplete="current-password"
              className={`${fieldClass(Boolean(fieldErrors.password))} pl-10 pr-12 text-sm sm:text-base`}
              id="password"
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
              placeholder="••••••••"
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
        </div>

        <div className="flex items-center justify-between gap-4">
          <label className="flex items-center text-sm text-gray-300" htmlFor="remember">
            <input
              checked={rememberMe}
              className="h-4 w-4 rounded border-gray-600 bg-black/30 text-cyan-500 focus:ring-cyan-400/50 focus:ring-offset-0"
              id="remember"
              onChange={(event) => setRememberMe(event.target.checked)}
              type="checkbox"
            />
            <span className="ml-2">Remember me</span>
          </label>
          <Link className="text-sm text-cyan-400 transition-colors hover:text-cyan-300" to="/login">
            Forgot password?
          </Link>
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
          {isSubmitting ? "Signing in..." : "Sign In"}
        </button>

        <AuthSocialButtons
          busy={isSubmitting}
          mode="signin"
          onSelect={handleOAuth}
          pendingProvider={oauthPendingProvider}
        />
      </form>

      <div className="relative mt-5 text-center sm:mt-6">
        <p className="text-sm text-gray-400">
          Don&apos;t have an account?{" "}
          <Link className="font-medium text-cyan-400 transition-colors hover:text-cyan-300" to="/signup">
            Create account
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
