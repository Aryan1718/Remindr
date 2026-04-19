import { frontendEnv } from "@/lib/env";

const oauthProviderMap = {
  google: "google",
  apple: "apple",
  microsoft: "azure",
} as const;

export type SupportedOAuthProvider = keyof typeof oauthProviderMap;

export function beginSupabaseOAuth(provider: SupportedOAuthProvider) {
  const redirectTo = `${window.location.origin}/login`;
  const url = new URL(`${frontendEnv.supabaseUrl}/auth/v1/authorize`);
  url.searchParams.set("provider", oauthProviderMap[provider]);
  url.searchParams.set("redirect_to", redirectTo);
  window.location.assign(url.toString());
}
