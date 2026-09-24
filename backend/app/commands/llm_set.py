import logging

from app.config import settings
from app.runtime.ollama import OllamaRuntime
from app.state import AvalonState


logger = logging.getLogger(__name__)


class LlmCommand:
    """Select the process-local current LLM."""

    key = "llm_set"

    def __init__(
        self,
        state: AvalonState,
        runtime: OllamaRuntime,
    ) -> None:
        self._state = state
        self._runtime = runtime

    async def execute(self, payload: str) -> str:
        key = payload.strip()

        if self._state.llm_inference_active:
            return "LLM inference is active."

        if self._state.llm_switch_active:
            return "LLM switch is already active."

        target = next(
            (
                llm
                for llm in settings.llm_models
                if llm.key == key
            ),
            None,
        )

        if target is None:
            return f"Unknown LLM: '{key}'."

        current = self._state.current_llm

        if target.key == current.key:
            return f"'{key}' already active."

        self._state.begin_llm_switch()

        try:
            if not await self._runtime.model_exists(target.model):
                return f"LLM '{key}' is unavailable."

            await self._runtime.unload_model(current.model)

            try:
                await self._runtime.warm_up_model(target.model)
            except Exception as target_error:
                logger.exception(
                    "Failed to warm up target LLM '%s'",
                    target.key,
                )

                try:
                    await self._runtime.warm_up_model(current.model)
                except Exception as recovery_error:
                    logger.exception(
                        "Failed to recover previous LLM '%s'",
                        current.key,
                    )
                    raise SystemExit(
                        f"Failed to recover previous LLM '{current.key}'."
                    ) from recovery_error

                raise RuntimeError(
                    f"Failed to activate LLM '{target.key}'."
                ) from target_error

            if not self._state.set_current_llm(target.key):
                raise RuntimeError(
                    f"Failed to select configured LLM '{target.key}'."
                )

            return f"'{target.key}' activated."
        finally:
            self._state.end_llm_switch()