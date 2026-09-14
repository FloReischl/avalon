import { warmUpRuntime } from "./backend";

const WARM_UP_INTERVAL_MS = 60_000;

let lastWarmUpAt: number | undefined;
let warmUpPromise: Promise<boolean> | undefined;

export function requestRuntimeWarmUp(): Promise<boolean> {
  const now = Date.now();

  if (warmUpPromise) {
    return warmUpPromise;
  }

  if (
    lastWarmUpAt !== undefined
    && now - lastWarmUpAt < WARM_UP_INTERVAL_MS
  ) {
    return Promise.resolve(true);
  }

  warmUpPromise = warmUpRuntime()
    .then(() => {
      lastWarmUpAt = Date.now();
      return true;
    })
    .catch((error) => {
      console.error("[runtime] model warm-up failed", error);
      return false;
    })
    .finally(() => {
      warmUpPromise = undefined;
    });

  return warmUpPromise;
}