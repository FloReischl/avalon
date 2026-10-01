import { BACKEND_BASE_URL, setPrincipalBearerToken } from "./services/backend";

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
  principalBearerToken: string;
  avatar: {
    greetingAudioUrl: string;
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

  const config = await response.json() as UiConfig;
  setPrincipalBearerToken(config.principalBearerToken);
  return config;
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
