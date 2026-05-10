import { AuthApiError } from "@/api/auth";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 6;

export function validateEmail(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Email is required.";
  }
  if (!EMAIL_PATTERN.test(trimmed)) {
    return "Enter a valid email address.";
  }
  return null;
}

export function validatePassword(value: string, options: { required?: boolean; minimumLength?: number } = {}) {
  const minimumLength = options.minimumLength;
  if (!value.trim()) {
    return options.required === false ? null : "Password is required.";
  }
  if (minimumLength !== undefined && value.length < minimumLength) {
    return `Password must be at least ${minimumLength} characters.`;
  }
  return null;
}

export function validateRequired(value: string, label: string) {
  if (!value.trim()) {
    return `${label} is required.`;
  }
  return null;
}

export function getAuthErrorMessage(error: unknown, fallback: string) {
  const rawMessage = error instanceof Error ? error.message : fallback;
  const normalized = rawMessage.toLowerCase();

  if (normalized.includes("invalid login credentials")) {
    return "Incorrect email or password.";
  }
  if (normalized.includes("email not confirmed")) {
    return "Please check your email and confirm your account before signing in.";
  }
  if (normalized.includes("user already registered")) {
    return "An account with this email already exists. Try signing in instead.";
  }
  if (normalized.includes("email rate limit exceeded")) {
    return "Too many confirmation emails were sent. Please wait and try again.";
  }
  if (normalized.includes("signup is disabled")) {
    return "Email sign-up is currently disabled for this project.";
  }
  if (normalized.includes("password should be at least")) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (normalized.includes("unable to validate email address")) {
    return "Enter a valid email address.";
  }

  if (error instanceof AuthApiError && error.status === 429) {
    return "Too many requests. Please wait and try again.";
  }

  return rawMessage || fallback;
}
