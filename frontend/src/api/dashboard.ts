import { simulateRequest } from "@/api/client";
import { getDb } from "@/mocks/db";

export function getDashboard() {
  return simulateRequest(() => getDb().dashboard);
}
