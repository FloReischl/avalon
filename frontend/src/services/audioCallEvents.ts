import { emit, listen, type UnlistenFn } from "@tauri-apps/api/event";

const AUDIO_CALL_CHANGED_EVENT = "audio-call-changed";

export function publishAudioCallChanged(): Promise<void> {
  return emit(AUDIO_CALL_CHANGED_EVENT);
}

export async function listenToAudioCallChanged(
  handler: () => void,
): Promise<UnlistenFn> {
  return listen(
    AUDIO_CALL_CHANGED_EVENT,
    () => handler(),
  );
}