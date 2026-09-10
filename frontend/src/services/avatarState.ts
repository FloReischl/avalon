import { emit, listen, type UnlistenFn } from "@tauri-apps/api/event";

export type AvatarVisualState =
  | "standard"
  | "listening"
  | "thinking"
  | "speaking";

export interface AvatarRuntimeState {
  state: AvatarVisualState;
  backendPending: boolean;
}

const AVATAR_RUNTIME_STATE_EVENT = "avatar-runtime-state";

export function publishAvatarRuntimeState(
  state: AvatarRuntimeState,
): Promise<void> {
  return emit(AVATAR_RUNTIME_STATE_EVENT, state);
}

export async function listenToAvatarRuntimeState(
  handler: (state: AvatarRuntimeState) => void,
): Promise<UnlistenFn> {
  return listen<AvatarRuntimeState>(
    AVATAR_RUNTIME_STATE_EVENT,
    (event) => handler(event.payload),
  );
}
