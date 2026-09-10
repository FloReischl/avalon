import { BACKEND_BASE_URL } from "./services/backend";

export type UiSpriteRegion = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type UiAvatarAnimation = {
  key: string;
  category: string;
  spriteSetUrl: string;
  sprites: UiSpriteRegion[];
};

export type UiConfig = {
  name: string;
  avatar: {
    standard: {
      key: "standard";
      url: string;
    };
    animations: UiAvatarAnimation[];
  };
};

let uiConfig: UiConfig | undefined;
let uiConfigPromise: Promise<UiConfig> | undefined;

async function requestUiConfig(): Promise<UiConfig> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/ui/config`,
  );

  if (!response.ok) {
    throw new Error(
      `UI config request failed with HTTP ${response.status}`,
    );
  }

  return await response.json() as UiConfig;
}

export async function loadUiConfig(): Promise<UiConfig> {
  if (uiConfig) {
    return uiConfig;
  }

  uiConfigPromise ??= requestUiConfig();

  try {
    uiConfig = await uiConfigPromise;
    return uiConfig;
  } catch (error) {
    uiConfigPromise = undefined;
    throw error;
  }
}

