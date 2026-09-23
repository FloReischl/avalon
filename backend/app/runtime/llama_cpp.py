"""Planned llama.cpp text runtime adapter."""


class LlamaCppRuntime:
    """Stub for a future local text-generation runtime."""

    async def health(self) -> bool:
        raise NotImplementedError("llama.cpp health check is not implemented yet.")

    async def generate_text(self, message: str) -> str:
        del message
        raise NotImplementedError("llama.cpp text generation is not implemented yet.")

