import { getCurrentWindow } from "@tauri-apps/api/window";

export async function startAvatarWindowDrag(): Promise<void> {
  await getCurrentWindow().startDragging();
}