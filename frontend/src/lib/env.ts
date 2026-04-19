function readRequiredEnv(name: string): string {
  const value = import.meta.env[name];
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Missing required frontend env var: ${name}`);
  }
  return value;
}

export const frontendEnv = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "http://127.0.0.1:8000/api/v1",
  supabaseUrl: readRequiredEnv("VITE_SUPABASE_URL").replace(/\/+$/, ""),
  supabaseAnonKey: readRequiredEnv("VITE_SUPABASE_ANON_KEY"),
};
