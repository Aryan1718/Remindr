export interface ApiErrorEnvelope {
  success?: false;
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
}

export interface ApiSuccessEnvelope<T> {
  success: true;
  data: T;
  message?: string | null;
  meta?: Record<string, unknown>;
}

export interface UserProfile {
  id: string;
  auth_user_id: string;
  email: string | null;
  full_name: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface UserPreferences {
  user_id: string;
  sleep_time: string | null;
  wake_time: string | null;
  work_start_time: string | null;
  work_end_time: string | null;
  work_days: number[];
  preferred_response_style: string | null;
  decision_style_default: string | null;
  reminder_tolerance: string | null;
  fatigue_prompt_enabled: boolean;
  onboarding_completed: boolean;
  profile_json: Record<string, unknown>;
}

export interface UserSnapshot {
  user: UserProfile;
  preferences: UserPreferences;
}

export interface SupabaseAuthUser {
  id: string;
  email?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface SupabasePasswordSession {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: SupabaseAuthUser;
}

export interface SupabaseSignupResponse {
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: SupabaseAuthUser | null;
  session?: {
    access_token?: string;
    refresh_token?: string;
    token_type?: string;
    expires_in?: number;
  } | null;
}
