import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

export interface BackendSnapshot {
  status: string;
  logs: string[];
}

export interface BackendLifecycleHandlers {
  onStatus: (status: string) => void;
  onLog: (message: string) => void;
}

export async function getBackendSnapshot(): Promise<BackendSnapshot> {
  return invoke<BackendSnapshot>("get_backend_snapshot");
}

export async function listenToBackendLifecycle(
  handlers: BackendLifecycleHandlers,
): Promise<UnlistenFn> {
  const unlistenStatus = await listen<string>(
    "backend-status",
    (event) => handlers.onStatus(event.payload),
  );

  const unlistenLog = await listen<string>(
    "backend-log",
    (event) => handlers.onLog(event.payload),
  );

  return () => {
    unlistenStatus();
    unlistenLog();
  };
}
