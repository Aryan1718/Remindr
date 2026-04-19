import { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { beginSupabaseOAuth, type SupportedOAuthProvider } from "@/api/supabase";
import { getPostLoginRoute, useAuthStore } from "@/stores/authStore";

const blobStyles = [
  {
    animationClass: "remindr-blob-a",
    className: "-top-1/4 -right-1/4 h-[800px] w-[800px] opacity-30",
    background:
      "radial-gradient(circle, rgba(100, 200, 255, 0.4) 0%, rgba(50, 150, 220, 0.2) 40%, transparent 70%)",
    blur: "blur(80px)",
  },
  {
    animationClass: "remindr-blob-b",
    className: "-bottom-1/4 -left-1/4 h-[700px] w-[700px] opacity-25",
    background:
      "radial-gradient(circle, rgba(80, 180, 255, 0.5) 0%, rgba(30, 120, 200, 0.3) 40%, transparent 70%)",
    blur: "blur(90px)",
  },
  {
    animationClass: "remindr-blob-c",
    className: "left-1/2 top-1/3 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 opacity-20",
    background:
      "radial-gradient(circle, rgba(120, 220, 255, 0.4) 0%, rgba(60, 160, 220, 0.2) 50%, transparent 70%)",
    blur: "blur(100px)",
  },
  {
    animationClass: "remindr-blob-d",
    className: "left-1/4 top-1/4 h-[400px] w-[400px] opacity-15",
    background:
      "radial-gradient(circle, rgba(150, 230, 255, 0.5) 0%, rgba(80, 180, 240, 0.3) 50%, transparent 70%)",
    blur: "blur(70px)",
  },
  {
    animationClass: "remindr-blob-e",
    className: "bottom-1/3 right-1/4 h-[500px] w-[500px] opacity-20",
    background:
      "radial-gradient(circle, rgba(90, 190, 255, 0.4) 0%, rgba(40, 130, 210, 0.25) 50%, transparent 70%)",
    blur: "blur(85px)",
  },
] as const;

const socialProviders = [
  {
    id: "google",
    label: "Sign in with Google",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
        <path
          fill="currentColor"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="currentColor"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="currentColor"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="currentColor"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
    ),
  },
  {
    id: "apple",
    label: "Sign in with Apple",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
      </svg>
    ),
  },
  {
    id: "microsoft",
    label: "Sign in with Microsoft",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z" />
      </svg>
    ),
  },
] as const;

const fieldClassName =
  "w-full rounded-xl border border-gray-600/30 bg-black/30 py-3 text-white placeholder:text-gray-500 backdrop-blur-sm transition-all focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/50";

const socialButtonClassName =
  "w-full rounded-xl border border-gray-600/30 bg-white/5 px-4 py-3 text-white backdrop-blur-sm transition duration-200 hover:bg-white/10 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-cyan-400/50";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
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
    if (submitDisabled) return;

    setIsSubmitting(true);
    setPageError(null);
    clearAuthError();

    try {
      const snapshot = await login({ email, password, rememberMe });
      navigate(redirectPath || getPostLoginRoute(snapshot), { replace: true });
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to sign in");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleOAuth(provider: SupportedOAuthProvider) {
    setIsSubmitting(true);
    setPageError(null);
    setOauthPendingProvider(provider);
    beginSupabaseOAuth(provider);
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <div className="absolute inset-0">
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 30%, rgba(20, 50, 100, 0.8) 0%, rgba(5, 15, 35, 1) 50%, rgba(0, 5, 15, 1) 100%)",
          }}
        />
        <video
          autoPlay
          className="absolute inset-0 h-full w-full object-cover"
          loop
          muted
          playsInline
          src="/media/remindr-login-bg.mp4"
        />

        <div className="absolute inset-0 overflow-hidden">
          {blobStyles.map((blob) => (
            <div
              className={`absolute rounded-full ${blob.className} ${blob.animationClass}`}
              key={blob.animationClass}
              style={{
                background: blob.background,
                filter: blob.blur,
              }}
            />
          ))}
        </div>

        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.3)_0%,rgba(0,0,0,0.4)_45%,rgba(0,0,0,0.5)_100%)]" />
      </div>

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="remindr-login-card-entry w-full max-w-[40rem] lg:max-w-[44rem] xl:max-w-[46rem]">
          <div
            className="relative overflow-hidden rounded-[28px] p-8 shadow-2xl sm:p-12 lg:p-14 xl:p-16"
            style={{
              background: "rgba(15, 25, 45, 0.75)",
              backdropFilter: "blur(40px) saturate(180%)",
              border: "1px solid rgba(120, 200, 255, 0.15)",
              boxShadow:
                "0 8px 32px 0 rgba(0, 0, 0, 0.4), inset 0 1px 1px 0 rgba(255, 255, 255, 0.05)",
            }}
          >
            <div
              className="absolute left-0 right-0 top-0 h-32 rounded-t-[28px] opacity-40"
              style={{
                background:
                  "linear-gradient(180deg, rgba(120, 200, 255, 0.1) 0%, transparent 100%)",
              }}
            />

            <div className="relative mb-12 text-center">
              <div
                className="mx-auto mb-6 flex h-[4.75rem] w-[4.75rem] items-center justify-center rounded-full sm:h-[5.25rem] sm:w-[5.25rem]"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(100, 200, 255, 0.3) 0%, rgba(50, 150, 220, 0.4) 100%)",
                  border: "2px solid rgba(120, 210, 255, 0.4)",
                  boxShadow: "0 4px 20px rgba(100, 200, 255, 0.3)",
                }}
              >
                <span className="text-4xl font-bold text-cyan-200 sm:text-[2.65rem]">R</span>
              </div>
              <h1 className="text-[2.7rem] font-bold text-white sm:text-[3.25rem]">Remindr</h1>
              <h2 className="mt-4 text-[1.45rem] text-gray-200 sm:text-[1.75rem]">Welcome back</h2>
              <p className="mt-4 text-base text-gray-400 sm:text-[1.05rem]">
                Sign in to access your assistant dashboard
              </p>
            </div>

            <form className="relative space-y-7" onSubmit={handleSubmit}>
              {pageError ? (
                <div className="rounded-2xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                  {pageError}
                </div>
              ) : null}

              <div>
                <label className="mb-3 block text-sm font-medium text-gray-300 sm:text-base" htmlFor="email">
                  Email
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <Mail className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    autoComplete="email"
                    className={`${fieldClassName} pl-10 pr-4 sm:py-[1.1rem] sm:text-base`}
                    id="email"
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    style={{ boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.2)" }}
                    type="email"
                    value={email}
                  />
                </div>
              </div>

              <div>
                <label className="mb-3 block text-sm font-medium text-gray-300 sm:text-base" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <Lock className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    autoComplete="current-password"
                    className={`${fieldClassName} pl-10 pr-12 sm:py-[1.1rem] sm:text-base`}
                    id="password"
                    onChange={(event) => setPassword(event.target.value)}
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
                className="w-full rounded-xl px-4 py-3 font-medium text-white transition duration-200 hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98] sm:py-[1.1rem] sm:text-base"
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

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-600/30" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="bg-transparent px-4 text-gray-400">or continue with</span>
                </div>
              </div>

              <div className="space-y-3">
                {socialProviders.map((provider) => (
                  <button
                    className={`${socialButtonClassName} sm:py-[1.1rem] sm:text-base`}
                    key={provider.id}
                    onClick={() => handleOAuth(provider.id as SupportedOAuthProvider)}
                    type="button"
                  >
                    <span className="flex items-center justify-center gap-3">
                      {provider.icon}
                      <span>
                        {oauthPendingProvider === provider.id && isSubmitting
                          ? "Redirecting..."
                          : provider.label}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </form>

            <div className="relative mt-6 text-center">
              <p className="text-sm text-gray-400">
                Don&apos;t have an account?{" "}
                <Link
                  className="font-medium text-cyan-400 transition-colors hover:text-cyan-300"
                  to="/onboarding"
                >
                  Create account
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
