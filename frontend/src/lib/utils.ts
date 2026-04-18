export function sleep(ms = 250) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export function formatRelativeDate(iso: string) {
  const target = new Date(iso);
  const now = new Date();
  const diff = Math.ceil((target.getTime() - now.getTime()) / 86_400_000);

  if (diff <= 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff < 7) return `In ${diff} days`;

  return target.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatTime(value: string) {
  const [hourText, minute] = value.split(":");
  const hour = Number(hourText);
  const suffix = hour >= 12 ? "PM" : "AM";
  const normalized = hour % 12 || 12;
  return `${normalized}:${minute} ${suffix}`;
}
