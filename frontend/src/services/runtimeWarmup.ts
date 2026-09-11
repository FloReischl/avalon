import { warmUpRuntime } from "./backend";

const WARM_UP_INTERVAL_MS = 60_000;

let lastWarmUpAt: number | undefined;

export function requestRuntimeWarmUp(): void {
  const now = Date.now();

  if (
    lastWarmUpAt !== undefined
    && now - lastWarmUpAt < WARM_UP_INTERVAL_MS
  ) {
    return;
  }

  lastWarmUpAt = now;

  void warmUpRuntime().catch((error) => {
    console.error("[runtime] model warm-up failed", error);
  });
}