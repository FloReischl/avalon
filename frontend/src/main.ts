import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { createApp } from "vue";

import App from "./App.vue";
import ChatWindow from "./ChatWindow.vue";
import ConfirmationWindow from "./ConfirmationWindow.vue";
import "./styles.css";

async function bootstrap() {
  const currentWindow = isTauri()

    ? getCurrentWindow()
    : undefined;
  const isChatWindow = currentWindow?.label === "chat";
  const isConfirmationWindow = currentWindow?.label === "confirmation";

  if (currentWindow && isChatWindow) {
    await currentWindow.setTitle("New Chat - Avalon");
  }

  createApp(isConfirmationWindow ? ConfirmationWindow : isChatWindow ? ChatWindow : App).mount("#app");
}

void bootstrap().catch((error) => {
  console.error("[startup] failed to initialize Avalon", error);
});
