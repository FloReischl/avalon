import { getCurrentWindow } from "@tauri-apps/api/window";

export async function setAvatarWindowTitle(title: string): Promise<void> {
  await getCurrentWindow().setTitle(title);
}
