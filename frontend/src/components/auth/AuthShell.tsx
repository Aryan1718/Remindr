import type { ReactNode } from "react";

const blobStyles = [
  {
    animationClass: "remindr-blob-a",
    className: "-top-1/4 -right-1/4 h-[800px] w-[800px] opacity-30",
    background:
      "radial-gradient(circle, rgba(100, 200, 255, 0.4) 0%, rgba(50, 150, 220, 0.2) 40%, transparent 70%)",
    blur: "blur(60px)",
  },
  {
    animationClass: "remindr-blob-b",
    className: "-bottom-1/4 -left-1/4 h-[700px] w-[700px] opacity-25",
    background:
      "radial-gradient(circle, rgba(80, 180, 255, 0.5) 0%, rgba(30, 120, 200, 0.3) 40%, transparent 70%)",
    blur: "blur(64px)",
  },
  {
    animationClass: "remindr-blob-c",
    className: "left-1/2 top-1/3 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 opacity-20",
    background:
      "radial-gradient(circle, rgba(120, 220, 255, 0.4) 0%, rgba(60, 160, 220, 0.2) 50%, transparent 70%)",
    blur: "blur(72px)",
  },
  {
    animationClass: "remindr-blob-d",
    className: "left-1/4 top-1/4 h-[400px] w-[400px] opacity-15",
    background:
      "radial-gradient(circle, rgba(150, 230, 255, 0.5) 0%, rgba(80, 180, 240, 0.3) 50%, transparent 70%)",
    blur: "blur(48px)",
  },
  {
    animationClass: "remindr-blob-e",
    className: "bottom-1/3 right-1/4 h-[500px] w-[500px] opacity-20",
    background:
      "radial-gradient(circle, rgba(90, 190, 255, 0.4) 0%, rgba(40, 130, 210, 0.25) 50%, transparent 70%)",
    blur: "blur(56px)",
  },
] as const;

const socialProviders = [
  {
    id: "google",
    provider: "Google",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
        <path
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          fill="currentColor"
        />
        <path
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          fill="currentColor"
        />
        <path
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          fill="currentColor"
        />
        <path
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  {
    id: "apple",
    provider: "Apple",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
      </svg>
    ),
  },
  {
    id: "microsoft",
    provider: "Microsoft",
    icon: (
      <svg aria-hidden="true" className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z" />
      </svg>
    ),
  },
] as const;

export const authFieldClassName =
  "w-full rounded-xl border border-gray-600/30 bg-black/30 py-3 text-white placeholder:text-gray-500 backdrop-blur-sm transition-all focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/50";

const socialButtonClassName =
  "w-full rounded-xl border border-gray-600/30 bg-white/5 px-4 py-3 text-white backdrop-blur-sm transition duration-200 hover:bg-white/10 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-cyan-400/50";

export type AuthSocialProvider = (typeof socialProviders)[number]["id"];

interface AuthShellProps {
  children: ReactNode;
  maxWidthClassName?: string;
}

interface AuthHeaderProps {
  description: string;
  subtitle: string;
}

interface SocialButtonsProps {
  mode: "signin" | "signup";
  busy?: boolean;
  onSelect?: (provider: AuthSocialProvider) => void;
  pendingProvider?: AuthSocialProvider | null;
}

export function AuthShell({
  children,
  maxWidthClassName = "max-w-[31rem] sm:max-w-[33rem] lg:max-w-[35rem] xl:max-w-[36rem]",
}: AuthShellProps) {
  return (
    <div
      className="relative min-h-screen overflow-hidden bg-black text-white"
      style={{
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif',
        MozOsxFontSmoothing: "grayscale",
        WebkitFontSmoothing: "antialiased",
      }}
    >
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
                willChange: "transform",
              }}
            />
          ))}
        </div>

        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.3)_0%,rgba(0,0,0,0.4)_45%,rgba(0,0,0,0.5)_100%)]" />
      </div>

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
        <div className={`remindr-login-card-entry w-full ${maxWidthClassName}`}>
          <div
            className="relative overflow-hidden rounded-[28px] p-6 shadow-2xl sm:p-8 lg:p-10 xl:p-11"
            style={{
              background: "rgba(15, 25, 45, 0.75)",
              backdropFilter: "blur(22px) saturate(150%)",
              WebkitBackdropFilter: "blur(22px) saturate(150%)",
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
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AuthHeader({ description, subtitle }: AuthHeaderProps) {
  return (
    <div className="relative mb-8 text-center sm:mb-10">
      <div
        className="mx-auto mb-5 flex h-[4.1rem] w-[4.1rem] items-center justify-center rounded-full sm:h-[4.5rem] sm:w-[4.5rem]"
        style={{
          background:
            "linear-gradient(135deg, rgba(100, 200, 255, 0.3) 0%, rgba(50, 150, 220, 0.4) 100%)",
          border: "2px solid rgba(120, 210, 255, 0.4)",
          boxShadow: "0 4px 20px rgba(100, 200, 255, 0.3)",
        }}
      >
        <span className="text-[2rem] font-bold text-cyan-200 sm:text-[2.3rem]">R</span>
      </div>
      <h1 className="text-[2.3rem] font-bold leading-none tracking-[-0.02em] text-white sm:text-[2.75rem]">
        Remindr
      </h1>
      <h2 className="mt-3 text-[1.2rem] leading-tight text-gray-200 sm:text-[1.4rem]">{subtitle}</h2>
      <p className="mt-3 text-sm text-gray-400 sm:text-base">{description}</p>
    </div>
  );
}

export function AuthSocialButtons({ mode, busy = false, onSelect, pendingProvider = null }: SocialButtonsProps) {
  const prefix = mode === "signup" ? "Create account with" : "Sign in with";

  return (
    <>
      <div className="relative my-5 sm:my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-600/30" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-transparent px-4 text-gray-400">or continue with</span>
        </div>
      </div>

      <div className="space-y-2.5 sm:space-y-3">
        {socialProviders.map((provider) => (
          <button
            className={`${socialButtonClassName} text-sm sm:text-base disabled:cursor-wait disabled:opacity-80`}
            disabled={busy && pendingProvider !== null && pendingProvider !== provider.id}
            key={provider.id}
            onClick={onSelect ? () => onSelect(provider.id) : undefined}
            type="button"
          >
            <span className="flex items-center justify-center gap-3">
              {provider.icon}
              <span>
                {busy && pendingProvider === provider.id ? "Redirecting..." : `${prefix} ${provider.provider}`}
              </span>
            </span>
          </button>
        ))}
      </div>
    </>
  );
}
