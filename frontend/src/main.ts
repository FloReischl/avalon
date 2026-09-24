import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { createApp } from "vue";

import App from "./App.vue";
import ChatWindow from "./ChatWindow.vue";
import PermissionsWindow from "./PermissionsWindow.vue";
import "./styles.css";

async function bootstrap() {
  const currentWindow = isTauri()

    ? getCurrentWindow()
    : undefined;
  const isChatWindow = currentWindow?.label === "chat";
  const isPermissionsWindow = currentWindow?.label === "permissions";

  if (currentWindow && isChatWindow) {
    await currentWindow.setTitle("Chat Window");
  }

  createApp(isPermissionsWindow ? PermissionsWindow : isChatWindow ? ChatWindow : App).mount("#app");
}

void bootstrap().catch((error) => {
  console.error("[startup] failed to initialize Avalon", error);
});
