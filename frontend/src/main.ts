import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { createApp } from "vue";

import App from "./App.vue";
import ChatWindow from "./ChatWindow.vue";
import "./styles.css";

const rootComponent =
  isTauri() && getCurrentWindow().label === "chat"
    ? ChatWindow
    : App;

createApp(rootComponent).mount("#app");

