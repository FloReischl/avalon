import { BACKEND_BASE_URL, setAgentBearerToken } from "./services/backend";

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
  agentBearerToken: string;
  avatarZoom: number;
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

const UI_CONFIG_RETRY_COUNT = 10;
const UI_CONFIG_RETRY_DELAY_MS = 500;

class UiConfigHttpError extends Error {
  constructor(readonly status: number) {
    super(`UI config request failed with HTTP ${status}`);
  }
}

function waitForUiConfigRetry(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, UI_CONFIG_RETRY_DELAY_MS);
  });
}

async function requestUiConfigOnce(): Promise<UiConfig> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/ui/config`,
  );

  if (!response.ok) {
    throw new UiConfigHttpError(response.status);
  }

  const config = await response.json() as UiConfig;
  setAgentBearerToken(config.agentBearerToken);
  return config;
}

async function requestUiConfig(): Promise<UiConfig> {
  for (let retry = 0; ; retry += 1) {
    try {
      return await requestUiConfigOnce();
    } catch (error) {
      const retryable =
        !(error instanceof UiConfigHttpError)
        || error.status >= 500;

      if (!retryable || retry >= UI_CONFIG_RETRY_COUNT) {
        throw error;
      }

      await waitForUiConfigRetry();
    }
  }
}

export async function loadUiConfig(): Promise<UiConfig> {
  if (uiConfig) {
    setAgentBearerToken(uiConfig.agentBearerToken);
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
