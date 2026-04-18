import { sleep } from "@/lib/utils";

export async function simulateRequest<T>(resolver: () => T): Promise<T> {
  await sleep(200);
  return resolver();
}
