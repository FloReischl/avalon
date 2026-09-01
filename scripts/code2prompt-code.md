Project Path: avalo

Source Tree:

```txt
avalo
├── AGENTS.md
├── AIDER_INSTRUCTIONS.md
├── README.md
├── backend
│   └── app
│       ├── __init__.py
│       ├── api
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── routes
│       │   │   ├── __init__.py
│       │   │   ├── chat.py
│       │   │   └── health.py
│       │   └── schemas.py
│       ├── application
│       │   ├── __init__.py
│       │   └── chat_service.py
│       ├── audio
│       │   ├── __init__.py
│       │   └── input.py
│       ├── config.py
│       ├── main.py
│       ├── runtime
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── llama_cpp.py
│       │   └── ollama.py
│       └── tts
│           ├── __init__.py
│           ├── base.py
│           └── chatterbox.py
├── docs
├── frontend
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── src
│   │   ├── App.vue
│   │   ├── env.d.ts
│   │   ├── main.ts
│   │   ├── services
│   │   │   └── backend.ts
│   │   ├── styles.css
│   │   └── types
│   │       └── chat.ts
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── pyproject.toml
├── scripts
│   ├── code2prompt-adrs.md
│   ├── code2prompt-adrs.sh
│   ├── code2prompt-code.sh
│   ├── frieda-dump.md
│   ├── frieda-dump.sh
│   ├── prompt2code-patch.yaml
│   ├── prompt2code.sh
│   ├── start-backend.sh
│   └── start-frontend.sh
├── tests
│   ├── backend
│   │   ├── test_chat_contract.py
│   │   ├── test_config.py
│   │   ├── test_health.py
│   │   ├── test_ollama_runtime.py
│   │   ├── test_runtime_blueprint.py
│   │   └── test_tts_blueprint.py
│   ├── data
│   │   └── german-transcription.wav
│   ├── frontend
│   │   └── App.spec.ts
│   └── integration
│       ├── test_ollama_integration.py
│       └── test_text_chat_blueprint.py
└── tmp

```

`AGENTS.md`:

```md
# Zusammenarbeit in Avalo

## Ziel

Avalo ist zugleich ein reales Softwareprojekt und ein Lernprojekt für AI Augmented Engineering. Codex unterstützt Flo als Requirements-, Architektur-, Test- und Dev-Lead-Assistentin. Fachliche und technische Verantwortung werden gemeinsam getragen; Flo trifft die finale Entscheidung.

## Arbeitsweise

- Vor der Implementierung werden Anforderungen, Akzeptanzkriterien und relevante Architekturentscheidungen geklärt.
- Bei offenen wesentlichen Fragen führt Codex ein fokussiertes Interview und stellt immer nur eine Frage gleichzeitig.
- Die Zahl der Fragen richtet sich nach Komplexität und Risiko. Triviale Themen werden nicht künstlich aufgeblasen.
- Codex benennt Annahmen, Unsicherheiten, Risiken und begründete Einwände klar.
- Architekturvarianten werden mit ihren Konsequenzen diskutiert. Tragfähige, langfristig relevante Entscheidungen können als ADR dokumentiert werden.
- Tests werden vor der Übergabe an die Implementierung festgelegt. Sie umfassen sinnvolle Unit- und Integrationstests sowie prüfbare Akzeptanzkriterien.
- Erst nach abgeschlossenen Anforderungen und Architektur wird die Umsetzung in kleine, klar abgegrenzte Pakete für Aider mit `qwen2.5-coder:14b-instruct` geschnitten.
- Jedes Aider-Paket enthält Kontext, konkreten Auftrag, Grenzen, betroffene Tests und ein eindeutiges Fertig-Kriterium.
- Ergebnisse von Aider/Qwen werden nach jedem Paket durch Codex und Flo anhand von Diff, Tests und Akzeptanzkriterien geprüft.
- Keine Commits, Pushes oder sonstigen externen Änderungen ohne ausdrücklichen Auftrag.

## Rollen von Codex

1. Requirements Engineering: Wesentliches klären und Anforderungen präzisieren.
2. Architekturassistenz: Gemeinsam mit Flo werden Optionen bewertet, Entscheidungen erarbeitet und bei Bedarf ADRs formulieren.
3. Test Lead: Teststrategie, relevante Testfälle und Akzeptanzkriterien definieren.
4. Dev Lead: Arbeitspakete und kopierfertige Aider-Prompts erstellen.
5. Review: Implementierung und Testergebnisse kritisch gegen die vereinbarten Grundlagen prüfen.

Ausführlicher Prozess: `docs/way-of-working.md`.

```
`AIDER_INSTRUCTIONS.md`:

```md
# Aider Instructions

## Role

You are the implementation agent for the Avalo project.

Product decisions, architectural decisions, requirements refinement, and task scoping are performed outside Aider.

Your responsibility is to implement the explicitly provided work package precisely and with minimal deviation.

## Working Rules

- Modify only files necessary to complete the requested task.
- Implement only the explicitly requested scope.
- Do not add features, endpoints, abstractions, refactorings, or improvements on your own initiative.
- Respect the existing architecture, public contracts, conventions, and project structure.
- If a requirement is unclear, contradictory, or appears technically infeasible, stop and ask for clarification instead of guessing.
- If a task explicitly requests read-only work, analysis, explanation, review, or inspection, do not modify any files.
- Do not change dependencies, build configuration, tooling, or versions unless explicitly requested.
- Do not remove or replace existing code outside the required scope.
- Do not fix unrelated problems discovered while working. Report them instead.
- Implement the tests specified by the work package together with the requested change.
- Tests should verify required behavior rather than implementation details.
- Run all tests and verification steps requested by the work package.
- If tests cannot be executed because prerequisites are unavailable, state this explicitly.
- Never claim successful verification unless it was actually performed.
- Do not create commits, tags, branches, pushes, or other Git changes unless explicitly requested.
- Do not perform external changes unless explicitly requested.

## Completion

After implementation, briefly report:

- files changed;
- what was implemented;
- tests and verification performed;
- any remaining risks, assumptions, or unresolved issues.

Do not perform additional work after completing the requested scope.
```
`README.md`:

```md
# Avalo

Lokales Entwicklungsgerüst für Avalo. Produktidee, Arbeitsweise und Architekturentscheidungen stehen unter [`docs/`](docs/).

## Voraussetzungen

- Linux
- Python 3.11 oder neuer
- Node.js mit npm

## Backend einrichten und starten

```bash
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
./scripts/start-backend.sh
```

Der Health-Endpunkt ist danach unter `http://127.0.0.1:8095/health` erreichbar. Der Chat-Endpunkt ist absichtlich nur ein Stub und antwortet mit HTTP 501.

## Frontend einrichten und starten

In einem zweiten Terminal:

```bash
cd frontend
npm install
npm run dev
```

Das Frontend läuft im Entwicklungsmodus unter `http://127.0.0.1:5173`.

## Tests

```bash
./.venv/bin/python -m pytest
cd frontend
npm test
```

Noch nicht implementierte Produktfunktionen sind als übersprungene Tests beziehungsweise `todo` markiert. Sie dürfen nicht als bestandene Funktionalität interpretiert werden.

## Aktueller Umfang

- startbares FastAPI-Backend mit Health-Endpunkt;
- minimale startbare Vue-Oberfläche;
- öffentliche Stub-Verträge für Textchat, natives Audio, LLM-Runtime und TTS;
- keine Modell-, Audio- oder TTS-Implementierung;
- kein Tauri und kein Packaging.

```
`backend/app/__init__.py`:

```py
"""Avalo backend package."""


```
`backend/app/api/__init__.py`:

```py
"""HTTP API package."""


```
`backend/app/api/router.py`:

```py
"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import chat, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router, prefix="/api/v1")


```
`backend/app/api/routes/__init__.py`:

```py
"""API route modules."""


```
`backend/app/api/routes/chat.py`:

```py
"""Text-chat endpoint contract."""

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def create_chat_response(request: ChatRequest) -> ChatResponse:
    """Return a complete model response once chat is implemented."""

    del request
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Text chat is not implemented yet.",
    )


```
`backend/app/api/routes/health.py`:

```py
"""Backend health endpoint."""

from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the HTTP backend is ready."""

    return HealthResponse(service=settings.app_name)


```
`backend/app/api/schemas.py`:

```py
"""Public request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend readiness information."""

    status: Literal["ok"] = "ok"
    service: str


class ChatRequest(BaseModel):
    """A single text-chat input."""

    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """A complete text-chat response."""

    message: str


```
`backend/app/application/__init__.py`:

```py
"""Application use cases."""


```
`backend/app/application/chat_service.py`:

```py
"""Text-chat orchestration boundary."""

from app.runtime.base import ModelRuntime


class ChatService:
    """Coordinate an in-memory chat with a model runtime."""

    def __init__(self, runtime: ModelRuntime) -> None:
        self._runtime = runtime

    async def reply(self, message: str) -> str:
        """Generate a complete response for a text message."""

        del message
        raise NotImplementedError("Chat orchestration is not implemented yet.")


```
`backend/app/audio/__init__.py`:

```py
"""Native audio input boundaries."""


```
`backend/app/audio/input.py`:

```py
"""Audio input preparation contract."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PreparedAudio:
    """Audio normalized for Gemma 4 input."""

    path: Path
    duration_seconds: float
    sample_rate_hz: int = 16_000
    channels: int = 1


class AudioInputPreparer(Protocol):
    """Normalize and validate a push-to-talk recording."""

    async def prepare(self, source: Path) -> PreparedAudio:
        """Prepare one recording with a maximum duration of 30 seconds."""
        ...


```
`backend/app/config.py`:

```py
"""Central backend configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Static settings for the initial local development setup."""

    app_name: str = "Avalo Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8095
    frontend_dev_origin: str = "http://127.0.0.1:5173"
    default_language: str = "de"
    audio_max_seconds: int = 30
    ollama_host: str = "127.0.0.1:11434"
    ollama_model: str = "gemma4:e4b-it-q4_K_M"


settings = Settings()

```
`backend/app/main.py`:

```py
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings


def create_app() -> FastAPI:
    """Create the backend application."""

    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(api_router)
    return application


app = create_app()

```
`backend/app/runtime/__init__.py`:

```py
"""Local model runtime adapters."""


```
`backend/app/runtime/base.py`:

```py
"""Runtime-independent model contracts."""

from pathlib import Path
from typing import Protocol


class ModelRuntime(Protocol):
    """Contract implemented by a local Gemma runtime adapter."""

    async def health(self) -> bool:
        """Return whether the runtime is ready for requests."""
        ...

    async def generate_text(self, message: str) -> str:
        """Generate a complete response from text input."""
        ...

    async def generate_from_audio(self, audio_file: Path) -> str:
        """Generate a complete response from native audio input."""
        ...


```
`backend/app/runtime/llama_cpp.py`:

```py
"""Planned llama.cpp runtime adapter."""

from pathlib import Path


class LlamaCppRuntime:
    """Stub for the runtime selected by the Gemma 4 spike."""

    async def health(self) -> bool:
        raise NotImplementedError("llama.cpp health check is not implemented yet.")

    async def generate_text(self, message: str) -> str:
        del message
        raise NotImplementedError("llama.cpp text generation is not implemented yet.")

    async def generate_from_audio(self, audio_file: Path) -> str:
        del audio_file
        raise NotImplementedError("llama.cpp audio generation is not implemented yet.")


```
`backend/app/runtime/ollama.py`:

```py
"""Ollama runtime adapter."""

import base64
from pathlib import Path

import httpx

from app.config import settings
from app.runtime.base import ModelRuntime


class OllamaRuntime(ModelRuntime):
    """Ollama runtime adapter."""

    async def health(self) -> bool:
        """Return whether the configured model is available in Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/show",
                    json={"model": settings.ollama_model},
                )
                response.raise_for_status()
                return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def generate_text(self, message: str) -> str:
        """Generate a complete response from text input."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": message,
                        "stream": False,
                    },
                )
                response.raise_for_status()

                data = response.json()
                text = data.get("response")

                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Invalid Ollama response")

                return text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

    async def generate_from_audio(self, audio_file: Path) -> str:
        """Generate a complete response from native audio input."""
        try:
            with open(audio_file, "rb") as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"http://{settings.ollama_host}/v1/chat/completions",
                    json={
                        "model": settings.ollama_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Transcribe and respond in German:",
                                    },
                                    {
                                        "type": "input_audio",
                                        "input_audio": {
                                            "data": audio_base64,
                                            "format": "wav",
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                )
                response.raise_for_status()

                data = response.json()
                choices = data.get("choices")

                if not isinstance(choices, list) or not choices:
                    raise ValueError("Invalid Ollama response")

                message = choices[0].get("message")
                if not isinstance(message, dict):
                    raise ValueError("Invalid Ollama response")

                text = message.get("content")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Invalid Ollama response")

                return text
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise RuntimeError(f"Ollama error: {exc}") from exc

```
`backend/app/tts/__init__.py`:

```py
"""Text-to-speech adapters."""


```
`backend/app/tts/base.py`:

```py
"""Runtime-independent text-to-speech contract."""

from pathlib import Path
from typing import Protocol


class TextToSpeech(Protocol):
    """Synthesize local speech from a completed response."""

    async def synthesize(self, text: str) -> Path:
        """Create an audio file and return its local path."""
        ...


```
`backend/app/tts/chatterbox.py`:

```py
"""Planned Chatterbox Multilingual adapter."""

from pathlib import Path


class ChatterboxTextToSpeech:
    """Stub for the TTS candidate selected in ADR 007."""

    async def synthesize(self, text: str) -> Path:
        del text
        raise NotImplementedError("Chatterbox TTS is not implemented yet.")


```
`frontend/index.html`:

```html
<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Avalo</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>


```
`frontend/package-lock.json`:

```json
{
  "name": "avalo-frontend",
  "version": "0.1.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "avalo-frontend",
      "version": "0.1.0",
      "dependencies": {
        "vue": "^3.5.0"
      },
      "devDependencies": {
        "@types/node": "^22.0.0",
        "@vitejs/plugin-vue": "^5.2.0",
        "@vue/test-utils": "^2.4.0",
        "jsdom": "^26.0.0",
        "typescript": "^5.8.0",
        "vite": "^6.0.0",
        "vitest": "^3.2.0",
        "vue-tsc": "^3.0.0"
      }
    },
    "node_modules/@asamuzakjp/css-color": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/@asamuzakjp/css-color/-/css-color-3.2.0.tgz",
      "integrity": "sha512-K1A6z8tS3XsmCMM86xoWdn7Fkdn9m6RSVtocUrJYIwZnFVkng/PvkEoWtOWmP+Scc6saYWHWZYbndEEXxl24jw==",
      "dev": true,
      "dependencies": {
        "@csstools/css-calc": "^2.1.3",
        "@csstools/css-color-parser": "^3.0.9",
        "@csstools/css-parser-algorithms": "^3.0.4",
        "@csstools/css-tokenizer": "^3.0.3",
        "lru-cache": "^10.4.3"
      }
    },
    "node_modules/@babel/helper-string-parser": {
      "version": "7.29.7",
      "resolved": "https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.29.7.tgz",
      "integrity": "sha512-Pb5ijPrZ89GDH8223L4UP8i6QApWxs04RbPQJTeWDV0/keR2E36MeKnyr6LYmUUvqRRI+Iv87SuF1W6ErINzYw==",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-identifier": {
      "version": "7.29.7",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.29.7.tgz",
      "integrity": "sha512-qehxGkRj55h/ff8EMaJ+cYhyaKlHIxqYDn682wQD7RNp9UujOQsHog2uS0r2vzr4pW+sXf90NeeayjcNaX3fFg==",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/parser": {
      "version": "7.29.8",
      "resolved": "https://registry.npmjs.org/@babel/parser/-/parser-7.29.8.tgz",
      "integrity": "sha512-E8lTAYNB1KW+FH+VGJuZM1ioAx2E6oVlvQFRrf5P8ZZmsiJXYAD9vTFV7yyEURNzgh1dFqMZuO6tUwcARbqFCA==",
      "dependencies": {
        "@babel/types": "^7.29.8"
      },
      "bin": {
        "parser": "bin/babel-parser.js"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@babel/types": {
      "version": "7.29.8",
      "resolved": "https://registry.npmjs.org/@babel/types/-/types-7.29.8.tgz",
      "integrity": "sha512-Vj1jF3cPfxg7OAfoI7QnVKLoILlm2JF9pnVHrX8qx7AHMiYWT+NDAA7jChlNgRS4WTLc/fD1lXLmPixluj+3Gg==",
      "dependencies": {
        "@babel/helper-string-parser": "^7.29.7",
        "@babel/helper-validator-identifier": "^7.29.7"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@csstools/color-helpers": {
      "version": "5.1.0",
      "resolved": "https://registry.npmjs.org/@csstools/color-helpers/-/color-helpers-5.1.0.tgz",
      "integrity": "sha512-S11EXWJyy0Mz5SYvRmY8nJYTFFd1LCNV+7cXyAgQtOOuzb4EsgfqDufL+9esx72/eLhsRdGZwaldu/h+E4t4BA==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@csstools/css-calc": {
      "version": "2.1.4",
      "resolved": "https://registry.npmjs.org/@csstools/css-calc/-/css-calc-2.1.4.tgz",
      "integrity": "sha512-3N8oaj+0juUw/1H3YwmDDJXCgTB1gKU6Hc/bB502u9zR0q2vd786XJH9QfrKIEgFlZmhZiq6epXl4rHqhzsIgQ==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "@csstools/css-parser-algorithms": "^3.0.5",
        "@csstools/css-tokenizer": "^3.0.4"
      }
    },
    "node_modules/@csstools/css-color-parser": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/@csstools/css-color-parser/-/css-color-parser-3.1.0.tgz",
      "integrity": "sha512-nbtKwh3a6xNVIp/VRuXV64yTKnb1IjTAEEh3irzS+HkKjAOYLTGNb9pmVNntZ8iVBHcWDA2Dof0QtPgFI1BaTA==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "dependencies": {
        "@csstools/color-helpers": "^5.1.0",
        "@csstools/css-calc": "^2.1.4"
      },
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "@csstools/css-parser-algorithms": "^3.0.5",
        "@csstools/css-tokenizer": "^3.0.4"
      }
    },
    "node_modules/@csstools/css-parser-algorithms": {
      "version": "3.0.5",
      "resolved": "https://registry.npmjs.org/@csstools/css-parser-algorithms/-/css-parser-algorithms-3.0.5.tgz",
      "integrity": "sha512-DaDeUkXZKjdGhgYaHNJTV9pV7Y9B3b644jCLs9Upc3VeNGg6LWARAT6O+Q+/COo+2gg/bM5rhpMAtf70WqfBdQ==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "@csstools/css-tokenizer": "^3.0.4"
      }
    },
    "node_modules/@csstools/css-tokenizer": {
      "version": "3.0.4",
      "resolved": "https://registry.npmjs.org/@csstools/css-tokenizer/-/css-tokenizer-3.0.4.tgz",
      "integrity": "sha512-Vd/9EVDiu6PPJt9yAh6roZP6El1xHrdvIVGjyBsHR0RYwNHgL7FJPyIIW4fANJNG6FtyZfvlRPpFI4ZM/lubvw==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/aix-ppc64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/aix-ppc64/-/aix-ppc64-0.25.12.tgz",
      "integrity": "sha512-Hhmwd6CInZ3dwpuGTF8fJG6yoWmsToE+vYgD4nytZVxcu1ulHpUQRAB1UJ8+N1Am3Mz4+xOByoQoSZf4D+CpkA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "aix"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-arm": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm/-/android-arm-0.25.12.tgz",
      "integrity": "sha512-VJ+sKvNA/GE7Ccacc9Cha7bpS8nyzVv0jdVgwNDaR4gDMC/2TTRc33Ip8qrNYUcpkOHUT5OZ0bUcNNVZQ9RLlg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-0.25.12.tgz",
      "integrity": "sha512-6AAmLG7zwD1Z159jCKPvAxZd4y/VTO0VkprYy+3N2FtJ8+BQWFXU+OxARIwA46c5tdD9SsKGZ/1ocqBS/gAKHg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/android-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/android-x64/-/android-x64-0.25.12.tgz",
      "integrity": "sha512-5jbb+2hhDHx5phYR2By8GTWEzn6I9UqR11Kwf22iKbNpYrsmRB18aX/9ivc5cabcUiAT/wM+YIZ6SG9QO6a8kg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/darwin-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-0.25.12.tgz",
      "integrity": "sha512-N3zl+lxHCifgIlcMUP5016ESkeQjLj/959RxxNYIthIg+CQHInujFuXeWbWMgnTo4cp5XVHqFPmpyu9J65C1Yg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/darwin-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-x64/-/darwin-x64-0.25.12.tgz",
      "integrity": "sha512-HQ9ka4Kx21qHXwtlTUVbKJOAnmG1ipXhdWTmNXiPzPfWKpXqASVcWdnf2bnL73wgjNrFXAa3yYvBSd9pzfEIpA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/freebsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-arm64/-/freebsd-arm64-0.25.12.tgz",
      "integrity": "sha512-gA0Bx759+7Jve03K1S0vkOu5Lg/85dou3EseOGUes8flVOGxbhDDh/iZaoek11Y8mtyKPGF3vP8XhnkDEAmzeg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/freebsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-x64/-/freebsd-x64-0.25.12.tgz",
      "integrity": "sha512-TGbO26Yw2xsHzxtbVFGEXBFH0FRAP7gtcPE7P5yP7wGy7cXK2oO7RyOhL5NLiqTlBh47XhmIUXuGciXEqYFfBQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-arm": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm/-/linux-arm-0.25.12.tgz",
      "integrity": "sha512-lPDGyC1JPDou8kGcywY0YILzWlhhnRjdof3UlcoqYmS9El818LLfJJc3PXXgZHrHCAKs/Z2SeZtDJr5MrkxtOw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm64/-/linux-arm64-0.25.12.tgz",
      "integrity": "sha512-8bwX7a8FghIgrupcxb4aUmYDLp8pX06rGh5HqDT7bB+8Rdells6mHvrFHHW2JAOPZUbnjUpKTLg6ECyzvas2AQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-ia32": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ia32/-/linux-ia32-0.25.12.tgz",
      "integrity": "sha512-0y9KrdVnbMM2/vG8KfU0byhUN+EFCny9+8g202gYqSSVMonbsCfLjUO+rCci7pM0WBEtz+oK/PIwHkzxkyharA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-loong64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-loong64/-/linux-loong64-0.25.12.tgz",
      "integrity": "sha512-h///Lr5a9rib/v1GGqXVGzjL4TMvVTv+s1DPoxQdz7l/AYv6LDSxdIwzxkrPW438oUXiDtwM10o9PmwS/6Z0Ng==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-mips64el": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-mips64el/-/linux-mips64el-0.25.12.tgz",
      "integrity": "sha512-iyRrM1Pzy9GFMDLsXn1iHUm18nhKnNMWscjmp4+hpafcZjrr2WbT//d20xaGljXDBYHqRcl8HnxbX6uaA/eGVw==",
      "cpu": [
        "mips64el"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-ppc64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ppc64/-/linux-ppc64-0.25.12.tgz",
      "integrity": "sha512-9meM/lRXxMi5PSUqEXRCtVjEZBGwB7P/D4yT8UG/mwIdze2aV4Vo6U5gD3+RsoHXKkHCfSxZKzmDssVlRj1QQA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-riscv64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-riscv64/-/linux-riscv64-0.25.12.tgz",
      "integrity": "sha512-Zr7KR4hgKUpWAwb1f3o5ygT04MzqVrGEGXGLnj15YQDJErYu/BGg+wmFlIDOdJp0PmB0lLvxFIOXZgFRrdjR0w==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-s390x": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-s390x/-/linux-s390x-0.25.12.tgz",
      "integrity": "sha512-MsKncOcgTNvdtiISc/jZs/Zf8d0cl/t3gYWX8J9ubBnVOwlk65UIEEvgBORTiljloIWnBzLs4qhzPkJcitIzIg==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/linux-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.25.12.tgz",
      "integrity": "sha512-uqZMTLr/zR/ed4jIGnwSLkaHmPjOjJvnm6TVVitAa08SLS9Z0VM8wIRx7gWbJB5/J54YuIMInDquWyYvQLZkgw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/netbsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-arm64/-/netbsd-arm64-0.25.12.tgz",
      "integrity": "sha512-xXwcTq4GhRM7J9A8Gv5boanHhRa/Q9KLVmcyXHCTaM4wKfIpWkdXiMog/KsnxzJ0A1+nD+zoecuzqPmCRyBGjg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/netbsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-x64/-/netbsd-x64-0.25.12.tgz",
      "integrity": "sha512-Ld5pTlzPy3YwGec4OuHh1aCVCRvOXdH8DgRjfDy/oumVovmuSzWfnSJg+VtakB9Cm0gxNO9BzWkj6mtO1FMXkQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openbsd-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-arm64/-/openbsd-arm64-0.25.12.tgz",
      "integrity": "sha512-fF96T6KsBo/pkQI950FARU9apGNTSlZGsv1jZBAlcLL1MLjLNIWPBkj5NlSz8aAzYKg+eNqknrUJ24QBybeR5A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openbsd-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-x64/-/openbsd-x64-0.25.12.tgz",
      "integrity": "sha512-MZyXUkZHjQxUvzK7rN8DJ3SRmrVrke8ZyRusHlP+kuwqTcfWLyqMOE3sScPPyeIXN/mDJIfGXvcMqCgYKekoQw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/openharmony-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/openharmony-arm64/-/openharmony-arm64-0.25.12.tgz",
      "integrity": "sha512-rm0YWsqUSRrjncSXGA7Zv78Nbnw4XL6/dzr20cyrQf7ZmRcsovpcRBdhD43Nuk3y7XIoW2OxMVvwuRvk9XdASg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "openharmony"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/sunos-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/sunos-x64/-/sunos-x64-0.25.12.tgz",
      "integrity": "sha512-3wGSCDyuTHQUzt0nV7bocDy72r2lI33QL3gkDNGkod22EsYl04sMf0qLb8luNKTOmgF/eDEDP5BFNwoBKH441w==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "sunos"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-arm64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-arm64/-/win32-arm64-0.25.12.tgz",
      "integrity": "sha512-rMmLrur64A7+DKlnSuwqUdRKyd3UE7oPJZmnljqEptesKM8wx9J8gx5u0+9Pq0fQQW8vqeKebwNXdfOyP+8Bsg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-ia32": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-ia32/-/win32-ia32-0.25.12.tgz",
      "integrity": "sha512-HkqnmmBoCbCwxUKKNPBixiWDGCpQGVsrQfJoVGYLPT41XWF8lHuE5N6WhVia2n4o5QK5M4tYr21827fNhi4byQ==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@esbuild/win32-x64": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.25.12.tgz",
      "integrity": "sha512-alJC0uCZpTFrSL0CCDjcgleBXPnCrEAhTBILpeAp7M/OFgoqtAetfBzX0xM00MUsVVPpVjlPuMbREqnZCXaTnA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@isaacs/cliui": {
      "version": "8.0.2",
      "resolved": "https://registry.npmjs.org/@isaacs/cliui/-/cliui-8.0.2.tgz",
      "integrity": "sha512-O8jcjabXaleOG9DQ0+ARXWZBTfnP4WNAqzuiJK7ll44AmxGKv/J2M4TPjxjY3znBCfvBXFzucm1twdyFybFqEA==",
      "dev": true,
      "dependencies": {
        "string-width": "^5.1.2",
        "string-width-cjs": "npm:string-width@^4.2.0",
        "strip-ansi": "^7.0.1",
        "strip-ansi-cjs": "npm:strip-ansi@^6.0.1",
        "wrap-ansi": "^8.1.0",
        "wrap-ansi-cjs": "npm:wrap-ansi@^7.0.0"
      },
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.5.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.5.5.tgz",
      "integrity": "sha512-cYQ9310grqxueWbl+WuIUIaiUaDcj7WOq5fVhEljNVgRfOUhY9fy2zTvfoqWsnebh8Sl70VScFbICvJnLKB0Og=="
    },
    "node_modules/@napi-rs/lzma-linux-x64-gnu": {
      "version": "1.5.1",
      "resolved": "https://registry.npmjs.org/@napi-rs/lzma-linux-x64-gnu/-/lzma-linux-x64-gnu-1.5.1.tgz",
      "integrity": "sha512-oTXEIha4SsuXdTA4Iyskj0kpdx2yVXdhd75c2v3xGrHFfVMsbhTPZU/nMPL4sWKo4pBHm3aucLaqGlF696dTyQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^22.20 || ^24.12 || >=25"
      }
    },
    "node_modules/@one-ini/wasm": {
      "version": "0.1.1",
      "resolved": "https://registry.npmjs.org/@one-ini/wasm/-/wasm-0.1.1.tgz",
      "integrity": "sha512-XuySG1E38YScSJoMlqovLru4KTUNSjgVTIjyh7qMX6aNN5HY5Ct5LhRJdxO79JtTzKfzV/bnWpz+zquYrISsvw==",
      "dev": true
    },
    "node_modules/@pkgjs/parseargs": {
      "version": "0.11.0",
      "resolved": "https://registry.npmjs.org/@pkgjs/parseargs/-/parseargs-0.11.0.tgz",
      "integrity": "sha512-+1VkjdD0QBLPodGrJUeqarH8VAIvQODIbwh9XpP5Syisf7YoQgsJKPNFoqqLQlu+VQ/tVSshMR6loPMn8U+dPg==",
      "dev": true,
      "optional": true,
      "engines": {
        "node": ">=14"
      }
    },
    "node_modules/@rollup/rollup-android-arm-eabi": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm-eabi/-/rollup-android-arm-eabi-4.63.0.tgz",
      "integrity": "sha512-70TeIFezKKy65LgAVyQh+w94/gjWhvPWaLaGGeMEgVrPkQhuj/M5bAYYZzIFUj9Y69oHyTm5Um/R6gcLh4A8JA==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-android-arm64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm64/-/rollup-android-arm64-4.63.0.tgz",
      "integrity": "sha512-YC86tYIHK6M1IV+wbzO+Bxk8RCBr6ZyWYgWxUCzaZD8mc8rrFoIJDNzDrkHBYRc/wKdrsIXmm6/F7NzrAO+OrA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-darwin-arm64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-arm64/-/rollup-darwin-arm64-4.63.0.tgz",
      "integrity": "sha512-oI+ECtUcli0y0fi4xpW82GdPIXdTkI8G8DSjG2LRuw09fPAGykaWYH/hXxiKuTxiAjiPSTIIuYUqof5Z2hShWw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-darwin-x64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-x64/-/rollup-darwin-x64-4.63.0.tgz",
      "integrity": "sha512-NwV+1s7TiKrMe4owHyKB/dTLD7ZJD0YEBEhIz+hvav1Cu1GReJjF+rsdNwjzENQeIAbE/CoNiaAc5Vz2h5DPAA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-arm64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-arm64/-/rollup-freebsd-arm64-4.63.0.tgz",
      "integrity": "sha512-tWtHBTu5gOPK4u4Urtk4qAHW3zZ9rQAmbssO8gp7ELvGTGI3aCiq6NqyTQ0PCIg7KbHJF2UkGDDs77YZGxfjCA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-x64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-x64/-/rollup-freebsd-x64-4.63.0.tgz",
      "integrity": "sha512-2qPoJiwTvtHQ27NnYvTnsgk8laXWYuVmNESG8WFZBcEPKLfZ3I27qBJarjVRQtwGeYyRfq5ZowHXih9lm2BItw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-gnueabihf": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-gnueabihf/-/rollup-linux-arm-gnueabihf-4.63.0.tgz",
      "integrity": "sha512-FQwsTRvLNuHoTdICABJQfbPUSEueISGmnpT06tXTMpfprf5NiKLSXKA0A+w45wJnCmZAnzgqBwbt6ARFuyOi5w==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-musleabihf": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-musleabihf/-/rollup-linux-arm-musleabihf-4.63.0.tgz",
      "integrity": "sha512-BBVTXziw8mY1a4ZbWME9tZyfzqXCDPqaC7Z3heQ29p5dkvXzwL0NwelO8zLa8c3RBKvl3YTuSnBgsBhYBtwjIw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-gnu/-/rollup-linux-arm64-gnu-4.63.0.tgz",
      "integrity": "sha512-w2Iyy9+RqKwx3d9qWMKsJg0FfRBsY0/pXNv0mCQ3ueRvJI6+QAScfD4nrMlzFLs2HNVW6Ew+mtZfDl9b7Ew5/Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-musl": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-musl/-/rollup-linux-arm64-musl-4.63.0.tgz",
      "integrity": "sha512-YK++KtrFRHYE0P6/RtYEAy9t8F37znP+K03RrIuLPYOL6SVlObRumf/0OE4V/h63xL9DwkWbNssZfmA9hawuDA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-gnu/-/rollup-linux-loong64-gnu-4.63.0.tgz",
      "integrity": "sha512-aBfOG6fP7YkkPmTqPwufRJeFyz7WPpECv9XNbnsk9+vg7rxdih0lbtEel7jcRng4LZrrmU3FfitCFyEj4BWDWg==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-musl": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-musl/-/rollup-linux-loong64-musl-4.63.0.tgz",
      "integrity": "sha512-LGaHEOeHNAag9VuS1Crs5DFg4RrU9MPi2nVnNJk9DTePx/B6RRYKVmrIXt2h7YOJlwjaFJ6lwtFDliZxScTLrQ==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-gnu/-/rollup-linux-ppc64-gnu-4.63.0.tgz",
      "integrity": "sha512-jClvk+J0FC3b7Udvegiw5/4hErbHtmsNsQgENnKXDWtNCJXsJYZH5WURvu7imDOO38xYml24eeh5x3A04ppwCw==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-musl": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-musl/-/rollup-linux-ppc64-musl-4.63.0.tgz",
      "integrity": "sha512-0OJlaGK+8+B777Ql5okIpD7ua5Ro9+VB9Ve0OKa28OQJZ1RbuUBVNHK/e3pr4BROqsyPl1JrPO1ZxJseCNffcA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-gnu/-/rollup-linux-riscv64-gnu-4.63.0.tgz",
      "integrity": "sha512-Ygsx+HoNH7afwi1bTIXbnTvVnsO+zurPLSYxybV1hHFVU72OWOCl6v05ql/z0hkpAPx+DK7Kn9Bi7MayCcjLTA==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-musl": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-musl/-/rollup-linux-riscv64-musl-4.63.0.tgz",
      "integrity": "sha512-pDQxtMGb+OvG3fLwR2OkZlSd47hW+kWg4BYMG/++sR6RqorQccwPTDsxda5hPwiIeIErAnCF9ma3SAU06bdQtQ==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-s390x-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-s390x-gnu/-/rollup-linux-s390x-gnu-4.63.0.tgz",
      "integrity": "sha512-0BnUG9mS8I4SSHr3XsxVhuCMEiu+rX61xxZF5vujso4LaiAGFZFxvDjg6Xn6tLPNTUAfuCvQYas4LMQMVsKRSQ==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-gnu/-/rollup-linux-x64-gnu-4.63.0.tgz",
      "integrity": "sha512-Adu/VttB1dpPNW+FEacrZ+xVm9tFty84+RrFzsqlFaPxoJB+9XXyDGtp5dCOoBwGBIEVH0To7lExFXEx0BIF4A==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-musl": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-musl/-/rollup-linux-x64-musl-4.63.0.tgz",
      "integrity": "sha512-NQ3bDvjUbFKmP23671xUlXtKmqVsUBd6M4PQCvbmNtOy06hnQIdKHy8oG/6S3R/S6He1JgPk6A5VT+prAJMYEw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-openbsd-x64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openbsd-x64/-/rollup-openbsd-x64-4.63.0.tgz",
      "integrity": "sha512-u2eDAl4+0aFvA13GxlGBtTI3SS3sdgwgtV0HyjZ0QaQVCgNE+jqNGey+GtxWiq+wxr/UycAx/OnfJzApCFamvA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "openbsd"
      ]
    },
    "node_modules/@rollup/rollup-openharmony-arm64": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openharmony-arm64/-/rollup-openharmony-arm64-4.63.0.tgz",
      "integrity": "sha512-XvRb5vfW3wAZQ+ZUG21AnHHDKtNcw99eigzEhjr//NZ3u7SoBaPP0seSc7FgP7p1epAEdAoZckMW9WY/+4w70w==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "openharmony"
      ]
    },
    "node_modules/@rollup/rollup-win32-arm64-msvc": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-arm64-msvc/-/rollup-win32-arm64-msvc-4.63.0.tgz",
      "integrity": "sha512-iZPmniy4kNBf5yo2RezbkYNNK5HPbXE9+g+twnbqSng7dtLEJy1SKoxiE/ni4FDacjyuZpEeb9U054N4EoKHYw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-ia32-msvc": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-ia32-msvc/-/rollup-win32-ia32-msvc-4.63.0.tgz",
      "integrity": "sha512-mFBBd+LF37fnE8JnYUOH+imj0aPFPK30vpar4ehJkgnLj9sZn8ZxiRENmLtgIwxK7TC8klF6N57fxdNBwQoqOA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-gnu": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-gnu/-/rollup-win32-x64-gnu-4.63.0.tgz",
      "integrity": "sha512-ujeqEY3B+zbGn3Z4Q03cUBG/LGWnBJncVT36WER31LcOsQk9+1dmINKKtvmmfChUvRbK1G0R8OhMWFgHgaZtAw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-msvc": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-msvc/-/rollup-win32-x64-msvc-4.63.0.tgz",
      "integrity": "sha512-hncn90N4sOky0L2LKE5oESKLbxCPeVo4eLA2LSMoDzM+879ml4WSr+Rr4DWknNIVVvS1Hirkc9hx02W6YxS8rQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@types/chai": {
      "version": "5.2.3",
      "resolved": "https://registry.npmjs.org/@types/chai/-/chai-5.2.3.tgz",
      "integrity": "sha512-Mw558oeA9fFbv65/y4mHtXDs9bPnFMZAL/jxdPFUpOHHIXX91mcgEHbS5Lahr+pwZFR8A7GQleRWeI6cGFC2UA==",
      "dev": true,
      "dependencies": {
        "@types/deep-eql": "*",
        "assertion-error": "^2.0.1"
      }
    },
    "node_modules/@types/deep-eql": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/@types/deep-eql/-/deep-eql-4.0.2.tgz",
      "integrity": "sha512-c9h9dVVMigMPc4bwTvC5dxqtqJZwQPePsWjPlpSOnojbor6pGqdk541lfA7AqFQr5pB1BRdq0juY9db81BwyFw==",
      "dev": true
    },
    "node_modules/@types/estree": {
      "version": "1.0.9",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.9.tgz",
      "integrity": "sha512-GhdPgy1el4/ImP05X05Uw4cw2/M93BCUmnEvWZNStlCzEKME4Fkk+YpoA5OiHNQmoS7Cafb8Xa3Pya8m1Qrzeg==",
      "dev": true
    },
    "node_modules/@types/node": {
      "version": "22.20.1",
      "resolved": "https://registry.npmjs.org/@types/node/-/node-22.20.1.tgz",
      "integrity": "sha512-EANqOCF9QFyra+4pfxUcX9STKJpCLjMbObVzljIJomAWSnuSIEAvyzEU53GaajbXJEgdh0iEcPL+DGvpUd4k1Q==",
      "dev": true,
      "dependencies": {
        "undici-types": "~6.21.0"
      }
    },
    "node_modules/@vitejs/plugin-vue": {
      "version": "5.2.4",
      "resolved": "https://registry.npmjs.org/@vitejs/plugin-vue/-/plugin-vue-5.2.4.tgz",
      "integrity": "sha512-7Yx/SXSOcQq5HiiV3orevHUFn+pmMB4cgbEkDYgnkUWb0WfeQ/wa2yFv6D5ICiCQOVpjA7vYDXrC7AGO8yjDHA==",
      "dev": true,
      "engines": {
        "node": "^18.0.0 || >=20.0.0"
      },
      "peerDependencies": {
        "vite": "^5.0.0 || ^6.0.0",
        "vue": "^3.2.25"
      }
    },
    "node_modules/@vitest/expect": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/expect/-/expect-3.2.7.tgz",
      "integrity": "sha512-E8eBXaKibuvH2pSZErOjdVb5vF4PbKYcrnluBTYxEk1l/VhhwZg1kZQsdtjq+CsF5CFydf2Rdkz7jDHKSisi3w==",
      "dev": true,
      "dependencies": {
        "@types/chai": "^5.2.2",
        "@vitest/spy": "3.2.7",
        "@vitest/utils": "3.2.7",
        "chai": "^5.2.0",
        "tinyrainbow": "^2.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/mocker": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/mocker/-/mocker-3.2.7.tgz",
      "integrity": "sha512-Trr0hYO9CM3Wj6ksWHRhK9IZpIY6wTMO5u/MqXurMxT57sWBaOPEtP3Oq60ihZuh5JsiagKfz95OcxdEP6dBrA==",
      "dev": true,
      "dependencies": {
        "@vitest/spy": "3.2.7",
        "estree-walker": "^3.0.3",
        "magic-string": "^0.30.17"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "msw": "^2.4.9",
        "vite": "^5.0.0 || ^6.0.0 || ^7.0.0-0"
      },
      "peerDependenciesMeta": {
        "msw": {
          "optional": true
        },
        "vite": {
          "optional": true
        }
      }
    },
    "node_modules/@vitest/mocker/node_modules/estree-walker": {
      "version": "3.0.3",
      "resolved": "https://registry.npmjs.org/estree-walker/-/estree-walker-3.0.3.tgz",
      "integrity": "sha512-7RUKfXgSMMkzt6ZuXmqapOurLGPPfgj6l9uRZ7lRGolvk0y2yocc35LdcxKC5PQZdn2DMqioAQ2NoWcrTKmm6g==",
      "dev": true,
      "dependencies": {
        "@types/estree": "^1.0.0"
      }
    },
    "node_modules/@vitest/pretty-format": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/pretty-format/-/pretty-format-3.2.7.tgz",
      "integrity": "sha512-KUHlwqVu0sRlhCdyPdQ/wBoTfRahjUky1MubOmYw9fWfIZy1gNoHpuaaQBPAaMaVYdQYHJLurzj8ECCj5OwTqA==",
      "dev": true,
      "dependencies": {
        "tinyrainbow": "^2.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/runner": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/runner/-/runner-3.2.7.tgz",
      "integrity": "sha512-sB9y4ovltoQP+WaUPwmSxO9WIg9Ig694Di5PalVPsYHklAdE027mehpWF2SQSVq+k6sFgaivbTjTJwZLSHbedA==",
      "dev": true,
      "dependencies": {
        "@vitest/utils": "3.2.7",
        "pathe": "^2.0.3",
        "strip-literal": "^3.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/snapshot": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/snapshot/-/snapshot-3.2.7.tgz",
      "integrity": "sha512-7C+MwShwtBSI5Buwoyg3s/iY1eHL9PKAf+O1wVh/TdnjXUtkoL/9YQtre90i4MtNXM6edP1wJ2zOBpfCyhIS7g==",
      "dev": true,
      "dependencies": {
        "@vitest/pretty-format": "3.2.7",
        "magic-string": "^0.30.17",
        "pathe": "^2.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/spy": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/spy/-/spy-3.2.7.tgz",
      "integrity": "sha512-Q2eQGI6d2L/hBtZ0qNuKcAGid68XK6cv1xsoaIma6PaJhHPoqcEJhYpXZ/5myCMqkNgtP6UKuBhbc0nHKnrkuQ==",
      "dev": true,
      "dependencies": {
        "tinyspy": "^4.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/utils": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/@vitest/utils/-/utils-3.2.7.tgz",
      "integrity": "sha512-x6BDOd7dyo3PFLY3I9/HJ25X/6OurhGXk2/B9gOZNPF7XDVjeBK4k01lQE5uvDpbuheErh91qYuE1E2OEjK3Rw==",
      "dev": true,
      "dependencies": {
        "@vitest/pretty-format": "3.2.7",
        "loupe": "^3.1.4",
        "tinyrainbow": "^2.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@volar/language-core": {
      "version": "2.4.28",
      "resolved": "https://registry.npmjs.org/@volar/language-core/-/language-core-2.4.28.tgz",
      "integrity": "sha512-w4qhIJ8ZSitgLAkVay6AbcnC7gP3glYM3fYwKV3srj8m494E3xtrCv6E+bWviiK/8hs6e6t1ij1s2Endql7vzQ==",
      "dev": true,
      "dependencies": {
        "@volar/source-map": "2.4.28"
      }
    },
    "node_modules/@volar/source-map": {
      "version": "2.4.28",
      "resolved": "https://registry.npmjs.org/@volar/source-map/-/source-map-2.4.28.tgz",
      "integrity": "sha512-yX2BDBqJkRXfKw8my8VarTyjv48QwxdJtvRgUpNE5erCsgEUdI2DsLbpa+rOQVAJYshY99szEcRDmyHbF10ggQ==",
      "dev": true
    },
    "node_modules/@volar/typescript": {
      "version": "2.4.28",
      "resolved": "https://registry.npmjs.org/@volar/typescript/-/typescript-2.4.28.tgz",
      "integrity": "sha512-Ja6yvWrbis2QtN4ClAKreeUZPVYMARDYZl9LMEv1iQ1QdepB6wn0jTRxA9MftYmYa4DQ4k/DaSZpFPUfxl8giw==",
      "dev": true,
      "dependencies": {
        "@volar/language-core": "2.4.28",
        "path-browserify": "^1.0.1",
        "vscode-uri": "^3.0.8"
      }
    },
    "node_modules/@vue/compiler-core": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/compiler-core/-/compiler-core-3.5.41.tgz",
      "integrity": "sha512-q0Xtv/F9w2YO/7htQhtiL+Ev2WCJbe5N2hc+XfgyKkEKqWpSxknmT8QOuGdEKNdjPq0c3F7rNpFkTo3Kfrm7pg==",
      "dependencies": {
        "@babel/parser": "^7.29.8",
        "@vue/shared": "3.5.41",
        "entities": "^7.0.1",
        "estree-walker": "^2.0.2",
        "source-map-js": "^1.2.1"
      }
    },
    "node_modules/@vue/compiler-dom": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/compiler-dom/-/compiler-dom-3.5.41.tgz",
      "integrity": "sha512-oKacVfNglLvGjnS6BXOlGL7EyG2h8X03pqXCjzotRZUaXGjbrTJUnVAQjrCqUnS+lyu31nwQjZY/d817GmCnfw==",
      "dependencies": {
        "@vue/compiler-core": "3.5.41",
        "@vue/shared": "3.5.41"
      }
    },
    "node_modules/@vue/compiler-sfc": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/compiler-sfc/-/compiler-sfc-3.5.41.tgz",
      "integrity": "sha512-XJhip7R2wy6vX3knCxdZN4KracFaZUef58s1KYewqluedHIJaPIVfXoYT7MF1F8nCvv6k8bWWxDC8opMkg1VTQ==",
      "dependencies": {
        "@babel/parser": "^7.29.8",
        "@vue/compiler-core": "3.5.41",
        "@vue/compiler-dom": "3.5.41",
        "@vue/compiler-ssr": "3.5.41",
        "@vue/shared": "3.5.41",
        "estree-walker": "^2.0.2",
        "magic-string": "^0.30.21",
        "postcss": "^8.5.19",
        "source-map-js": "^1.2.1"
      }
    },
    "node_modules/@vue/compiler-ssr": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/compiler-ssr/-/compiler-ssr-3.5.41.tgz",
      "integrity": "sha512-U3v5OejKEGqOI0Wy0+Sz7hGuIFZHA4LSXzrNM3IMIeDyJEBBfTpX26n3SDgToRpP2bLc9FfI2j/kSgcJ8Emq5A==",
      "dependencies": {
        "@vue/compiler-dom": "3.5.41",
        "@vue/shared": "3.5.41"
      }
    },
    "node_modules/@vue/language-core": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/@vue/language-core/-/language-core-3.3.11.tgz",
      "integrity": "sha512-QJmpliwAVpC/OxubIByPAhNzsQPRc8/gxlN2qnVzVfIMjMDz/9RnXRFoetjz5yEgXVXyp4LqhXq3V53PjmNzFw==",
      "dev": true,
      "dependencies": {
        "@volar/language-core": "2.4.28",
        "@vue/compiler-dom": "^3.5.0",
        "@vue/shared": "^3.5.0",
        "alien-signals": "^3.2.1",
        "muggle-string": "^0.4.1",
        "path-browserify": "^1.0.1",
        "picomatch": "^4.0.4"
      }
    },
    "node_modules/@vue/reactivity": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/reactivity/-/reactivity-3.5.41.tgz",
      "integrity": "sha512-rznsqKM0np0x18EjzF8x88MpEhdNsffbvFbckLL5+oUKz1BxAImEmO7J1ArRYSyo6aQaVoBDp7jEkT91OOxydA==",
      "dependencies": {
        "@vue/shared": "3.5.41"
      }
    },
    "node_modules/@vue/runtime-core": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/runtime-core/-/runtime-core-3.5.41.tgz",
      "integrity": "sha512-Vcry58hiAKwGen9Z1jUZE0feFsNArPCMOImYI8el48A9Idf6DuQYD0U05zZIF2Iad1hGhPSvcbBbAOhNr55fhg==",
      "dependencies": {
        "@vue/reactivity": "3.5.41",
        "@vue/shared": "3.5.41"
      }
    },
    "node_modules/@vue/runtime-dom": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/runtime-dom/-/runtime-dom-3.5.41.tgz",
      "integrity": "sha512-3vVBahVBS9+U6cmXBLyb8nE6/yYo4J/CGI9eVFs3KiMc0YHuudwKyShTD65jtJy/L9PUUxNAFu4cj4LiJ0UFbw==",
      "dependencies": {
        "@vue/reactivity": "3.5.41",
        "@vue/runtime-core": "3.5.41",
        "@vue/shared": "3.5.41",
        "csstype": "^3.2.3"
      }
    },
    "node_modules/@vue/server-renderer": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/server-renderer/-/server-renderer-3.5.41.tgz",
      "integrity": "sha512-n6hx/pNFfbD6SuyeuMVkvqox8bwf/ET9JlA/kAz/imw8sw++wkqKe2mHX5KutjPpbKE4Z56yTHszoOjGMI9igQ==",
      "dependencies": {
        "@vue/compiler-ssr": "3.5.41",
        "@vue/runtime-dom": "3.5.41",
        "@vue/shared": "3.5.41"
      }
    },
    "node_modules/@vue/shared": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/@vue/shared/-/shared-3.5.41.tgz",
      "integrity": "sha512-IOnwSCma8j+9xJT6b8H0dEYidC80NsYmNMlZxRsukYcSoGaDBohog5hDxzeUXdFeGWFA++vWvxqOmrr96VlqMA=="
    },
    "node_modules/@vue/test-utils": {
      "version": "2.4.11",
      "resolved": "https://registry.npmjs.org/@vue/test-utils/-/test-utils-2.4.11.tgz",
      "integrity": "sha512-GDqaqZsA6m2E5vNzej0aYiIb6BX8xV9pNSbbbXKOfEYwg7ZNblVX8suyqmUBThq8VIrgAJNxn+z72hVtUeiWHA==",
      "dev": true,
      "dependencies": {
        "js-beautify": "^1.14.9",
        "vue-component-type-helpers": "^3.0.0"
      },
      "peerDependencies": {
        "@vue/compiler-dom": "3.x",
        "@vue/server-renderer": "3.x",
        "vue": "3.x"
      },
      "peerDependenciesMeta": {
        "@vue/server-renderer": {
          "optional": true
        }
      }
    },
    "node_modules/abbrev": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/abbrev/-/abbrev-2.0.0.tgz",
      "integrity": "sha512-6/mh1E2u2YgEsCHdY0Yx5oW+61gZU+1vXaoiHHrpKeuRNNgFvS+/jrwHiQhB5apAf5oB7UB7E19ol2R2LKH8hQ==",
      "dev": true,
      "engines": {
        "node": "^14.17.0 || ^16.13.0 || >=18.0.0"
      }
    },
    "node_modules/agent-base": {
      "version": "7.1.4",
      "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-7.1.4.tgz",
      "integrity": "sha512-MnA+YT8fwfJPgBx3m60MNqakm30XOkyIoH1y6huTQvC0PwZG7ki8NacLBcrPbNoo8vEZy7Jpuk7+jMO+CUovTQ==",
      "dev": true,
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/alien-signals": {
      "version": "3.2.1",
      "resolved": "https://registry.npmjs.org/alien-signals/-/alien-signals-3.2.1.tgz",
      "integrity": "sha512-I8FjmltrfnDFoZedi5CG8DghVYNhzb/Ijluz7tCSJH0xpd0484Kowhbb1XDYOxfJpU1p5wnM2X54dA+IfGyD1g==",
      "dev": true
    },
    "node_modules/ansi-regex": {
      "version": "6.3.0",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-6.3.0.tgz",
      "integrity": "sha512-WpDfL7NO6j7tH88IDBNVdUJxDh9nmCteAVW9dsep846XdwF4naCBK+/tGLX3KJgcpgMRXCFlTM2hKGoK9FsdrQ==",
      "dev": true,
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/chalk/ansi-regex?sponsor=1"
      }
    },
    "node_modules/ansi-styles": {
      "version": "6.2.3",
      "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-6.2.3.tgz",
      "integrity": "sha512-4Dj6M28JB+oAH8kFkTLUo+a2jwOFkuqb3yucU0CANcRRUbxS0cP0nZYCGjcc3BNXwRIsUVmDGgzawme7zvJHvg==",
      "dev": true,
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/chalk/ansi-styles?sponsor=1"
      }
    },
    "node_modules/assertion-error": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/assertion-error/-/assertion-error-2.0.1.tgz",
      "integrity": "sha512-Izi8RQcffqCeNVgFigKli1ssklIbpHnCYc6AknXGYoB6grJqyeby7jv12JUQgmTAnIDnbck1uxksT4dzN3PWBA==",
      "dev": true,
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/balanced-match": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/balanced-match/-/balanced-match-1.0.2.tgz",
      "integrity": "sha512-3oSeUO0TMV67hN1AmbXsK4yaqU7tjiHlbxRDZOpH0KW9+CeX4bRAaX0Anxt0tx2MrpRpWwQaPwIlISEJhYU5Pw==",
      "dev": true
    },
    "node_modules/brace-expansion": {
      "version": "2.1.4",
      "resolved": "https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.4.tgz",
      "integrity": "sha512-hGfVzPxthbf3+2yjg/RBs60cB0FhqBS/zvdV/4wn4/BmN0bNMMHPc4V/BbFieqf1TKAGGAHnY4eSjajCl0f2Xg==",
      "dev": true,
      "dependencies": {
        "balanced-match": "^1.0.0"
      }
    },
    "node_modules/cac": {
      "version": "6.7.14",
      "resolved": "https://registry.npmjs.org/cac/-/cac-6.7.14.tgz",
      "integrity": "sha512-b6Ilus+c3RrdDk+JhLKUAQfzzgLEPy6wcXqS7f/xe1EETvsDP6GORG7SFuOs6cID5YkqchW/LXZbX5bc8j7ZcQ==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/chai": {
      "version": "5.3.3",
      "resolved": "https://registry.npmjs.org/chai/-/chai-5.3.3.tgz",
      "integrity": "sha512-4zNhdJD/iOjSH0A05ea+Ke6MU5mmpQcbQsSOkgdaUMJ9zTlDTD/GYlwohmIE2u0gaxHYiVHEn1Fw9mZ/ktJWgw==",
      "dev": true,
      "dependencies": {
        "assertion-error": "^2.0.1",
        "check-error": "^2.1.1",
        "deep-eql": "^5.0.1",
        "loupe": "^3.1.0",
        "pathval": "^2.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/check-error": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/check-error/-/check-error-2.1.3.tgz",
      "integrity": "sha512-PAJdDJusoxnwm1VwW07VWwUN1sl7smmC3OKggvndJFadxxDRyFJBX/ggnu/KE4kQAB7a3Dp8f/YXC1FlUprWmA==",
      "dev": true,
      "engines": {
        "node": ">= 16"
      }
    },
    "node_modules/color-convert": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/color-convert/-/color-convert-2.0.1.tgz",
      "integrity": "sha512-RRECPsj7iu/xb5oKYcsFHSppFNnsj/52OVTRKb4zP5onXwVF3zVmmToNcOfGC+CRDpfK/U584fMg38ZHCaElKQ==",
      "dev": true,
      "dependencies": {
        "color-name": "~1.1.4"
      },
      "engines": {
        "node": ">=7.0.0"
      }
    },
    "node_modules/color-name": {
      "version": "1.1.4",
      "resolved": "https://registry.npmjs.org/color-name/-/color-name-1.1.4.tgz",
      "integrity": "sha512-dOy+3AuW3a2wNbZHIuMZpTcgjGuLU/uBL/ubcZF9OXbDo8ff4O8yVp5Bf0efS8uEoYo5q4Fx7dY9OgQGXgAsQA==",
      "dev": true
    },
    "node_modules/commander": {
      "version": "10.0.1",
      "resolved": "https://registry.npmjs.org/commander/-/commander-10.0.1.tgz",
      "integrity": "sha512-y4Mg2tXshplEbSGzx7amzPwKKOCGuoSRP/CjEdwwk0FOGlUbq6lKuoyDZTNZkmxHdJtp54hdfY/JUrdL7Xfdug==",
      "dev": true,
      "engines": {
        "node": ">=14"
      }
    },
    "node_modules/config-chain": {
      "version": "1.1.13",
      "resolved": "https://registry.npmjs.org/config-chain/-/config-chain-1.1.13.tgz",
      "integrity": "sha512-qj+f8APARXHrM0hraqXYb2/bOVSV4PvJQlNZ/DVj0QrmNM2q2euizkeuVckQ57J+W0mRH6Hvi+k50M4Jul2VRQ==",
      "dev": true,
      "dependencies": {
        "ini": "^1.3.4",
        "proto-list": "~1.2.1"
      }
    },
    "node_modules/cross-spawn": {
      "version": "7.0.6",
      "resolved": "https://registry.npmjs.org/cross-spawn/-/cross-spawn-7.0.6.tgz",
      "integrity": "sha512-uV2QOWP2nWzsy2aMp8aRibhi9dlzF5Hgh5SHaB9OiTGEyDTiJJyx0uy51QXdyWbtAHNua4XJzUKca3OzKUd3vA==",
      "dev": true,
      "dependencies": {
        "path-key": "^3.1.0",
        "shebang-command": "^2.0.0",
        "which": "^2.0.1"
      },
      "engines": {
        "node": ">= 8"
      }
    },
    "node_modules/cssstyle": {
      "version": "4.6.0",
      "resolved": "https://registry.npmjs.org/cssstyle/-/cssstyle-4.6.0.tgz",
      "integrity": "sha512-2z+rWdzbbSZv6/rhtvzvqeZQHrBaqgogqt85sqFNbabZOuFbCVFb8kPeEtZjiKkbrm395irpNKiYeFeLiQnFPg==",
      "dev": true,
      "dependencies": {
        "@asamuzakjp/css-color": "^3.2.0",
        "rrweb-cssom": "^0.8.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/csstype": {
      "version": "3.2.3",
      "resolved": "https://registry.npmjs.org/csstype/-/csstype-3.2.3.tgz",
      "integrity": "sha512-z1HGKcYy2xA8AGQfwrn0PAy+PB7X/GSj3UVJW9qKyn43xWa+gl5nXmU4qqLMRzWVLFC8KusUX8T/0kCiOYpAIQ=="
    },
    "node_modules/data-urls": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/data-urls/-/data-urls-5.0.0.tgz",
      "integrity": "sha512-ZYP5VBHshaDAiVZxjbRVcFJpc+4xGgT0bK3vzy1HLN8jTO975HEbuYzZJcHoQEY5K1a0z8YayJkyVETa08eNTg==",
      "dev": true,
      "dependencies": {
        "whatwg-mimetype": "^4.0.0",
        "whatwg-url": "^14.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/debug": {
      "version": "4.4.3",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
      "dev": true,
      "dependencies": {
        "ms": "^2.1.3"
      },
      "engines": {
        "node": ">=6.0"
      },
      "peerDependenciesMeta": {
        "supports-color": {
          "optional": true
        }
      }
    },
    "node_modules/decimal.js": {
      "version": "10.6.0",
      "resolved": "https://registry.npmjs.org/decimal.js/-/decimal.js-10.6.0.tgz",
      "integrity": "sha512-YpgQiITW3JXGntzdUmyUR1V812Hn8T1YVXhCu+wO3OpS4eU9l4YdD3qjyiKdV6mvV29zapkMeD390UVEf2lkUg==",
      "dev": true
    },
    "node_modules/deep-eql": {
      "version": "5.0.2",
      "resolved": "https://registry.npmjs.org/deep-eql/-/deep-eql-5.0.2.tgz",
      "integrity": "sha512-h5k/5U50IJJFpzfL6nO9jaaumfjO/f2NjK/oYB2Djzm4p9L+3T9qWpZqZ2hAbLPuuYq9wrU08WQyBTL5GbPk5Q==",
      "dev": true,
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/eastasianwidth": {
      "version": "0.2.0",
      "resolved": "https://registry.npmjs.org/eastasianwidth/-/eastasianwidth-0.2.0.tgz",
      "integrity": "sha512-I88TYZWc9XiYHRQ4/3c5rjjfgkjhLyW2luGIheGERbNQ6OY7yTybanSpDXZa8y7VUP9YmDcYa+eyq4ca7iLqWA==",
      "dev": true
    },
    "node_modules/editorconfig": {
      "version": "1.0.7",
      "resolved": "https://registry.npmjs.org/editorconfig/-/editorconfig-1.0.7.tgz",
      "integrity": "sha512-e0GOtq/aTQhVdNyDU9e02+wz9oDDM+SIOQxWME2QRjzRX5yyLAuHDE+0aE8vHb9XRC8XD37eO2u57+F09JqFhw==",
      "dev": true,
      "dependencies": {
        "@one-ini/wasm": "0.1.1",
        "commander": "^10.0.0",
        "minimatch": "^9.0.1",
        "semver": "^7.5.3"
      },
      "bin": {
        "editorconfig": "bin/editorconfig"
      },
      "engines": {
        "node": ">=14"
      }
    },
    "node_modules/emoji-regex": {
      "version": "9.2.2",
      "resolved": "https://registry.npmjs.org/emoji-regex/-/emoji-regex-9.2.2.tgz",
      "integrity": "sha512-L18DaJsXSUk2+42pv8mLs5jJT2hqFkFE4j21wOmgbUqsZ2hL72NsUU785g9RXgo3s0ZNgVl42TiHp3ZtOv/Vyg==",
      "dev": true
    },
    "node_modules/entities": {
      "version": "7.0.1",
      "resolved": "https://registry.npmjs.org/entities/-/entities-7.0.1.tgz",
      "integrity": "sha512-TWrgLOFUQTH994YUyl1yT4uyavY5nNB5muff+RtWaqNVCAK408b5ZnnbNAUEWLTCpum9w6arT70i1XdQ4UeOPA==",
      "engines": {
        "node": ">=0.12"
      },
      "funding": {
        "url": "https://github.com/fb55/entities?sponsor=1"
      }
    },
    "node_modules/es-module-lexer": {
      "version": "1.7.0",
      "resolved": "https://registry.npmjs.org/es-module-lexer/-/es-module-lexer-1.7.0.tgz",
      "integrity": "sha512-jEQoCwk8hyb2AZziIOLhDqpm5+2ww5uIE6lkO/6jcOCusfk6LhMHpXXfBLXTZ7Ydyt0j4VoUQv6uGNYbdW+kBA==",
      "dev": true
    },
    "node_modules/esbuild": {
      "version": "0.25.12",
      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.25.12.tgz",
      "integrity": "sha512-bbPBYYrtZbkt6Os6FiTLCTFxvq4tt3JKall1vRwshA3fdVztsLAatFaZobhkBC8/BrPetoa0oksYoKXoG4ryJg==",
      "dev": true,
      "hasInstallScript": true,
      "bin": {
        "esbuild": "bin/esbuild"
      },
      "engines": {
        "node": ">=18"
      },
      "optionalDependencies": {
        "@esbuild/aix-ppc64": "0.25.12",
        "@esbuild/android-arm": "0.25.12",
        "@esbuild/android-arm64": "0.25.12",
        "@esbuild/android-x64": "0.25.12",
        "@esbuild/darwin-arm64": "0.25.12",
        "@esbuild/darwin-x64": "0.25.12",
        "@esbuild/freebsd-arm64": "0.25.12",
        "@esbuild/freebsd-x64": "0.25.12",
        "@esbuild/linux-arm": "0.25.12",
        "@esbuild/linux-arm64": "0.25.12",
        "@esbuild/linux-ia32": "0.25.12",
        "@esbuild/linux-loong64": "0.25.12",
        "@esbuild/linux-mips64el": "0.25.12",
        "@esbuild/linux-ppc64": "0.25.12",
        "@esbuild/linux-riscv64": "0.25.12",
        "@esbuild/linux-s390x": "0.25.12",
        "@esbuild/linux-x64": "0.25.12",
        "@esbuild/netbsd-arm64": "0.25.12",
        "@esbuild/netbsd-x64": "0.25.12",
        "@esbuild/openbsd-arm64": "0.25.12",
        "@esbuild/openbsd-x64": "0.25.12",
        "@esbuild/openharmony-arm64": "0.25.12",
        "@esbuild/sunos-x64": "0.25.12",
        "@esbuild/win32-arm64": "0.25.12",
        "@esbuild/win32-ia32": "0.25.12",
        "@esbuild/win32-x64": "0.25.12"
      }
    },
    "node_modules/estree-walker": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/estree-walker/-/estree-walker-2.0.2.tgz",
      "integrity": "sha512-Rfkk/Mp/DL7JVje3u18FxFujQlTNR2q6QfMSMB7AvCBx91NGj/ba3kCfza0f6dVDbw7YlRf/nDrn7pQrCCyQ/w=="
    },
    "node_modules/expect-type": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/expect-type/-/expect-type-1.4.0.tgz",
      "integrity": "sha512-KfYbmpRm0VbLjEvVa9yGwCi9GI34xvi7A/HXYWQO65CSD2u3MczUJSuwXKFIxlGsgBQizV9q5J9NHj4VG0n+pA==",
      "dev": true,
      "engines": {
        "node": ">=12.0.0"
      }
    },
    "node_modules/fdir": {
      "version": "6.5.0",
      "resolved": "https://registry.npmjs.org/fdir/-/fdir-6.5.0.tgz",
      "integrity": "sha512-tIbYtZbucOs0BRGqPJkshJUYdL+SDH7dVM8gjy+ERp3WAUjLEFJE+02kanyHtwjWOnwrKYBiwAmM0p4kLJAnXg==",
      "dev": true,
      "engines": {
        "node": ">=12.0.0"
      },
      "peerDependencies": {
        "picomatch": "^3 || ^4"
      },
      "peerDependenciesMeta": {
        "picomatch": {
          "optional": true
        }
      }
    },
    "node_modules/foreground-child": {
      "version": "3.3.1",
      "resolved": "https://registry.npmjs.org/foreground-child/-/foreground-child-3.3.1.tgz",
      "integrity": "sha512-gIXjKqtFuWEgzFRJA9WCQeSJLZDjgJUOMCMzxtvFq/37KojM1BFGufqsCy0r4qSQmYLsZYMeyRqzIWOMup03sw==",
      "dev": true,
      "dependencies": {
        "cross-spawn": "^7.0.6",
        "signal-exit": "^4.0.1"
      },
      "engines": {
        "node": ">=14"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/fsevents": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz",
      "integrity": "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw==",
      "dev": true,
      "hasInstallScript": true,
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^8.16.0 || ^10.6.0 || >=11.0.0"
      }
    },
    "node_modules/glob": {
      "version": "10.5.0",
      "resolved": "https://registry.npmjs.org/glob/-/glob-10.5.0.tgz",
      "integrity": "sha512-DfXN8DfhJ7NH3Oe7cFmu3NCu1wKbkReJ8TorzSAFbSKrlNaQSKfIzqYqVY8zlbs2NLBbWpRiU52GX2PbaBVNkg==",
      "deprecated": "Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me",
      "dev": true,
      "dependencies": {
        "foreground-child": "^3.1.0",
        "jackspeak": "^3.1.2",
        "minimatch": "^9.0.4",
        "minipass": "^7.1.2",
        "package-json-from-dist": "^1.0.0",
        "path-scurry": "^1.11.1"
      },
      "bin": {
        "glob": "dist/esm/bin.mjs"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/html-encoding-sniffer": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/html-encoding-sniffer/-/html-encoding-sniffer-4.0.0.tgz",
      "integrity": "sha512-Y22oTqIU4uuPgEemfz7NDJz6OeKf12Lsu+QC+s3BVpda64lTiMYCyGwg5ki4vFxkMwQdeZDl2adZoqUgdFuTgQ==",
      "dev": true,
      "dependencies": {
        "whatwg-encoding": "^3.1.1"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/http-proxy-agent": {
      "version": "7.0.2",
      "resolved": "https://registry.npmjs.org/http-proxy-agent/-/http-proxy-agent-7.0.2.tgz",
      "integrity": "sha512-T1gkAiYYDWYx3V5Bmyu7HcfcvL7mUrTWiM6yOfa3PIphViJ/gFPbvidQ+veqSOHci/PxBcDabeUNCzpOODJZig==",
      "dev": true,
      "dependencies": {
        "agent-base": "^7.1.0",
        "debug": "^4.3.4"
      },
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/https-proxy-agent": {
      "version": "7.0.6",
      "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-7.0.6.tgz",
      "integrity": "sha512-vK9P5/iUfdl95AI+JVyUuIcVtd4ofvtrOr3HNtM2yxC9bnMbEdp3x01OhQNnjb8IJYi38VlTE3mBXwcfvywuSw==",
      "dev": true,
      "dependencies": {
        "agent-base": "^7.1.2",
        "debug": "4"
      },
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/iconv-lite": {
      "version": "0.6.3",
      "resolved": "https://registry.npmjs.org/iconv-lite/-/iconv-lite-0.6.3.tgz",
      "integrity": "sha512-4fCk79wshMdzMp2rH06qWrJE4iolqLhCUH+OiuIgU++RB0+94NlDL81atO7GX55uUKueo0txHNtvEyI6D7WdMw==",
      "dev": true,
      "dependencies": {
        "safer-buffer": ">= 2.1.2 < 3.0.0"
      },
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/ini": {
      "version": "1.3.8",
      "resolved": "https://registry.npmjs.org/ini/-/ini-1.3.8.tgz",
      "integrity": "sha512-JV/yugV2uzW5iMRSiZAyDtQd+nxtUnjeLt0acNdw98kKLrvuRVyB80tsREOE7yvGVgalhZ6RNXCmEHkUKBKxew==",
      "dev": true
    },
    "node_modules/is-fullwidth-code-point": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/is-fullwidth-code-point/-/is-fullwidth-code-point-3.0.0.tgz",
      "integrity": "sha512-zymm5+u+sCsSWyD9qNaejV3DFvhCKclKdizYaJUuHA83RLjb7nSuGnddCHGv0hk+KY7BMAlsWeK4Ueg6EV6XQg==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/is-potential-custom-element-name": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/is-potential-custom-element-name/-/is-potential-custom-element-name-1.0.1.tgz",
      "integrity": "sha512-bCYeRA2rVibKZd+s2625gGnGF/t7DSqDs4dP7CrLA1m7jKWz6pps0LpYLJN8Q64HtmPKJ1hrN3nzPNKFEKOUiQ==",
      "dev": true
    },
    "node_modules/isexe": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/isexe/-/isexe-2.0.0.tgz",
      "integrity": "sha512-RHxMLp9lnKHGHRng9QFhRCMbYAcVpn69smSGcq3f36xjgVVWThj4qqLbTLlq7Ssj8B+fIQ1EuCEGI2lKsyQeIw==",
      "dev": true
    },
    "node_modules/jackspeak": {
      "version": "3.4.3",
      "resolved": "https://registry.npmjs.org/jackspeak/-/jackspeak-3.4.3.tgz",
      "integrity": "sha512-OGlZQpz2yfahA/Rd1Y8Cd9SIEsqvXkLVoSw/cgwhnhFMDbsQFeZYoJJ7bIZBS9BcamUW96asq/npPWugM+RQBw==",
      "dev": true,
      "dependencies": {
        "@isaacs/cliui": "^8.0.2"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      },
      "optionalDependencies": {
        "@pkgjs/parseargs": "^0.11.0"
      }
    },
    "node_modules/js-beautify": {
      "version": "1.15.4",
      "resolved": "https://registry.npmjs.org/js-beautify/-/js-beautify-1.15.4.tgz",
      "integrity": "sha512-9/KXeZUKKJwqCXUdBxFJ3vPh467OCckSBmYDwSK/EtV090K+iMJ7zx2S3HLVDIWFQdqMIsZWbnaGiba18aWhaA==",
      "dev": true,
      "dependencies": {
        "config-chain": "^1.1.13",
        "editorconfig": "^1.0.4",
        "glob": "^10.4.2",
        "js-cookie": "^3.0.5",
        "nopt": "^7.2.1"
      },
      "bin": {
        "css-beautify": "js/bin/css-beautify.js",
        "html-beautify": "js/bin/html-beautify.js",
        "js-beautify": "js/bin/js-beautify.js"
      },
      "engines": {
        "node": ">=14"
      }
    },
    "node_modules/js-cookie": {
      "version": "3.0.8",
      "resolved": "https://registry.npmjs.org/js-cookie/-/js-cookie-3.0.8.tgz",
      "integrity": "sha512-yeJd4aNAdYZQjaon2bpD/Gb0B/omw7HQOsynXXcOiWVCacbBcPlgn8S/d1X6blFSaHao7ozqtW7NZW19xpCtIw==",
      "dev": true
    },
    "node_modules/js-tokens": {
      "version": "9.0.1",
      "resolved": "https://registry.npmjs.org/js-tokens/-/js-tokens-9.0.1.tgz",
      "integrity": "sha512-mxa9E9ITFOt0ban3j6L5MpjwegGz6lBQmM1IJkWeBZGcMxto50+eWdjC/52xDbS2vy0k7vIMK0Fe2wfL9OQSpQ==",
      "dev": true
    },
    "node_modules/jsdom": {
      "version": "26.1.0",
      "resolved": "https://registry.npmjs.org/jsdom/-/jsdom-26.1.0.tgz",
      "integrity": "sha512-Cvc9WUhxSMEo4McES3P7oK3QaXldCfNWp7pl2NNeiIFlCoLr3kfq9kb1fxftiwk1FLV7CvpvDfonxtzUDeSOPg==",
      "dev": true,
      "dependencies": {
        "cssstyle": "^4.2.1",
        "data-urls": "^5.0.0",
        "decimal.js": "^10.5.0",
        "html-encoding-sniffer": "^4.0.0",
        "http-proxy-agent": "^7.0.2",
        "https-proxy-agent": "^7.0.6",
        "is-potential-custom-element-name": "^1.0.1",
        "nwsapi": "^2.2.16",
        "parse5": "^7.2.1",
        "rrweb-cssom": "^0.8.0",
        "saxes": "^6.0.0",
        "symbol-tree": "^3.2.4",
        "tough-cookie": "^5.1.1",
        "w3c-xmlserializer": "^5.0.0",
        "webidl-conversions": "^7.0.0",
        "whatwg-encoding": "^3.1.1",
        "whatwg-mimetype": "^4.0.0",
        "whatwg-url": "^14.1.1",
        "ws": "^8.18.0",
        "xml-name-validator": "^5.0.0"
      },
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "canvas": "^3.0.0"
      },
      "peerDependenciesMeta": {
        "canvas": {
          "optional": true
        }
      }
    },
    "node_modules/loupe": {
      "version": "3.2.1",
      "resolved": "https://registry.npmjs.org/loupe/-/loupe-3.2.1.tgz",
      "integrity": "sha512-CdzqowRJCeLU72bHvWqwRBBlLcMEtIvGrlvef74kMnV2AolS9Y8xUv1I0U/MNAWMhBlKIoyuEgoJ0t/bbwHbLQ==",
      "dev": true
    },
    "node_modules/lru-cache": {
      "version": "10.4.3",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-10.4.3.tgz",
      "integrity": "sha512-JNAzZcXrCt42VGLuYz0zfAzDfAvJWW6AfYlDBQyDV5DClI2m5sAmK+OIO7s59XfsRsWHp02jAJrRadPRGTt6SQ==",
      "dev": true
    },
    "node_modules/magic-string": {
      "version": "0.30.21",
      "resolved": "https://registry.npmjs.org/magic-string/-/magic-string-0.30.21.tgz",
      "integrity": "sha512-vd2F4YUyEXKGcLHoq+TEyCjxueSeHnFxyyjNp80yg0XV4vUhnDer/lvvlqM/arB5bXQN5K2/3oinyCRyx8T2CQ==",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.5"
      }
    },
    "node_modules/minimatch": {
      "version": "9.0.9",
      "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-9.0.9.tgz",
      "integrity": "sha512-OBwBN9AL4dqmETlpS2zasx+vTeWclWzkblfZk7KTA5j3jeOONz/tRCnZomUyvNg83wL5Zv9Ss6HMJXAgL8R2Yg==",
      "dev": true,
      "dependencies": {
        "brace-expansion": "^2.0.2"
      },
      "engines": {
        "node": ">=16 || 14 >=14.17"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/minipass": {
      "version": "7.1.3",
      "resolved": "https://registry.npmjs.org/minipass/-/minipass-7.1.3.tgz",
      "integrity": "sha512-tEBHqDnIoM/1rXME1zgka9g6Q2lcoCkxHLuc7ODJ5BxbP5d4c2Z5cGgtXAku59200Cx7diuHTOYfSBD8n6mm8A==",
      "dev": true,
      "engines": {
        "node": ">=16 || 14 >=14.17"
      }
    },
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "dev": true
    },
    "node_modules/muggle-string": {
      "version": "0.4.1",
      "resolved": "https://registry.npmjs.org/muggle-string/-/muggle-string-0.4.1.tgz",
      "integrity": "sha512-VNTrAak/KhO2i8dqqnqnAHOa3cYBwXEZe9h+D5h/1ZqFSTEFHdM65lR7RoIqq3tBBYavsOXV84NoHXZ0AkPyqQ==",
      "dev": true
    },
    "node_modules/nanoid": {
      "version": "3.3.18",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.18.tgz",
      "integrity": "sha512-DTg4MJbGMWkfi6VZFdNt2/caMbQy4Ou+Op/hJQvGEWcnVfoA1QA+xzRKAzw9jD6+GVOOeYr/mIcuDSdug6F6+w==",
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/nopt": {
      "version": "7.2.1",
      "resolved": "https://registry.npmjs.org/nopt/-/nopt-7.2.1.tgz",
      "integrity": "sha512-taM24ViiimT/XntxbPyJQzCG+p4EKOpgD3mxFwW38mGjVUrfERQOeY4EDHjdnptttfHuHQXFx+lTP08Q+mLa/w==",
      "dev": true,
      "dependencies": {
        "abbrev": "^2.0.0"
      },
      "bin": {
        "nopt": "bin/nopt.js"
      },
      "engines": {
        "node": "^14.17.0 || ^16.13.0 || >=18.0.0"
      }
    },
    "node_modules/nwsapi": {
      "version": "2.2.24",
      "resolved": "https://registry.npmjs.org/nwsapi/-/nwsapi-2.2.24.tgz",
      "integrity": "sha512-7YRhZ3jS45LwmSCT4b2sVFHt/WuovaktDU07QrtOBY2PXskss5a9jfmR9jptyumwXST+rFjrmppMY1KT/yn35A==",
      "dev": true
    },
    "node_modules/package-json-from-dist": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/package-json-from-dist/-/package-json-from-dist-1.0.1.tgz",
      "integrity": "sha512-UEZIS3/by4OC8vL3P2dTXRETpebLI2NiI5vIrjaD/5UtrkFX/tNbwjTSRAGC/+7CAo2pIcBaRgWmcBBHcsaCIw==",
      "dev": true
    },
    "node_modules/parse5": {
      "version": "7.3.0",
      "resolved": "https://registry.npmjs.org/parse5/-/parse5-7.3.0.tgz",
      "integrity": "sha512-IInvU7fabl34qmi9gY8XOVxhYyMyuH2xUNpb2q8/Y+7552KlejkRvqvD19nMoUW/uQGGbqNpA6Tufu5FL5BZgw==",
      "dev": true,
      "dependencies": {
        "entities": "^6.0.0"
      },
      "funding": {
        "url": "https://github.com/inikulin/parse5?sponsor=1"
      }
    },
    "node_modules/parse5/node_modules/entities": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/entities/-/entities-6.0.1.tgz",
      "integrity": "sha512-aN97NXWF6AWBTahfVOIrB/NShkzi5H7F9r1s9mD3cDj4Ko5f2qhhVoYMibXF7GlLveb/D2ioWay8lxI97Ven3g==",
      "dev": true,
      "engines": {
        "node": ">=0.12"
      },
      "funding": {
        "url": "https://github.com/fb55/entities?sponsor=1"
      }
    },
    "node_modules/path-browserify": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/path-browserify/-/path-browserify-1.0.1.tgz",
      "integrity": "sha512-b7uo2UCUOYZcnF/3ID0lulOJi/bafxa1xPe7ZPsammBSpjSWQkjNxlt635YGS2MiR9GjvuXCtz2emr3jbsz98g==",
      "dev": true
    },
    "node_modules/path-key": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/path-key/-/path-key-3.1.1.tgz",
      "integrity": "sha512-ojmeN0qd+y0jszEtoY48r0Peq5dwMEkIlCOu6Q5f41lfkswXuKtYrhgoTpLnyIcHm24Uhqx+5Tqm2InSwLhE6Q==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/path-scurry": {
      "version": "1.11.1",
      "resolved": "https://registry.npmjs.org/path-scurry/-/path-scurry-1.11.1.tgz",
      "integrity": "sha512-Xa4Nw17FS9ApQFJ9umLiJS4orGjm7ZzwUrwamcGQuHSzDyth9boKDaycYdDcZDuqYATXw4HFXgaqWTctW/v1HA==",
      "dev": true,
      "dependencies": {
        "lru-cache": "^10.2.0",
        "minipass": "^5.0.0 || ^6.0.2 || ^7.0.0"
      },
      "engines": {
        "node": ">=16 || 14 >=14.18"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/pathe": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/pathe/-/pathe-2.0.3.tgz",
      "integrity": "sha512-WUjGcAqP1gQacoQe+OBJsFA7Ld4DyXuUIjZ5cc75cLHvJ7dtNsTugphxIADwspS+AraAUePCKrSVtPLFj/F88w==",
      "dev": true
    },
    "node_modules/pathval": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/pathval/-/pathval-2.0.1.tgz",
      "integrity": "sha512-//nshmD55c46FuFw26xV/xFAaB5HF9Xdap7HJBBnrKdAd6/GxDBaNA1870O79+9ueg61cZLSVc+OaFlfmObYVQ==",
      "dev": true,
      "engines": {
        "node": ">= 14.16"
      }
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA=="
    },
    "node_modules/picomatch": {
      "version": "4.0.7",
      "resolved": "https://registry.npmjs.org/picomatch/-/picomatch-4.0.7.tgz",
      "integrity": "sha512-qcJu88Q2IWqJsDD529JKMdwGm/dvInW4HvQnRwiH9JtihJvzGOscDtHE3x1pBKeUOTysQ8kVmLnJ2kJu7yhcGA==",
      "dev": true,
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/sponsors/jonschlinkert"
      }
    },
    "node_modules/postcss": {
      "version": "8.5.26",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.26.tgz",
      "integrity": "sha512-u82N74LFzG8ca+dD8puPnplTXoGH4fTPpVGuIbt36G3qvNlkvfD0lEAZSxaly3KX8TS/L1A1gsCEmvKmBcVbkQ==",
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "dependencies": {
        "nanoid": "^3.3.17",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/proto-list": {
      "version": "1.2.4",
      "resolved": "https://registry.npmjs.org/proto-list/-/proto-list-1.2.4.tgz",
      "integrity": "sha512-vtK/94akxsTMhe0/cbfpR+syPuszcuwhqVjJq26CuNDgFGj682oRBXOP5MJpv2r7JtE8MsiepGIqvvOTBwn2vA==",
      "dev": true
    },
    "node_modules/punycode": {
      "version": "2.3.1",
      "resolved": "https://registry.npmjs.org/punycode/-/punycode-2.3.1.tgz",
      "integrity": "sha512-vYt7UD1U9Wg6138shLtLOvdAu+8DsC/ilFtEVHcH+wydcSpNE20AfSOduf6MkRFahL5FY7X1oU7nKVZFtfq8Fg==",
      "dev": true,
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/rollup": {
      "version": "4.63.0",
      "resolved": "https://registry.npmjs.org/rollup/-/rollup-4.63.0.tgz",
      "integrity": "sha512-T5vnZ2y4QqC3/4P+w2+JO+Q/OVdnPsv4XcSYJYMEn0R9/jjl5AgLwO9LAZMzP2lN71O6pypn91rB7lDstUkfrQ==",
      "dev": true,
      "dependencies": {
        "@types/estree": "1.0.9"
      },
      "bin": {
        "rollup": "dist/bin/rollup"
      },
      "engines": {
        "node": ">=18.0.0",
        "npm": ">=8.0.0"
      },
      "optionalDependencies": {
        "@napi-rs/lzma-linux-x64-gnu": "1.5.1",
        "@rollup/rollup-android-arm-eabi": "4.63.0",
        "@rollup/rollup-android-arm64": "4.63.0",
        "@rollup/rollup-darwin-arm64": "4.63.0",
        "@rollup/rollup-darwin-x64": "4.63.0",
        "@rollup/rollup-freebsd-arm64": "4.63.0",
        "@rollup/rollup-freebsd-x64": "4.63.0",
        "@rollup/rollup-linux-arm-gnueabihf": "4.63.0",
        "@rollup/rollup-linux-arm-musleabihf": "4.63.0",
        "@rollup/rollup-linux-arm64-gnu": "4.63.0",
        "@rollup/rollup-linux-arm64-musl": "4.63.0",
        "@rollup/rollup-linux-loong64-gnu": "4.63.0",
        "@rollup/rollup-linux-loong64-musl": "4.63.0",
        "@rollup/rollup-linux-ppc64-gnu": "4.63.0",
        "@rollup/rollup-linux-ppc64-musl": "4.63.0",
        "@rollup/rollup-linux-riscv64-gnu": "4.63.0",
        "@rollup/rollup-linux-riscv64-musl": "4.63.0",
        "@rollup/rollup-linux-s390x-gnu": "4.63.0",
        "@rollup/rollup-linux-x64-gnu": "4.63.0",
        "@rollup/rollup-linux-x64-musl": "4.63.0",
        "@rollup/rollup-openbsd-x64": "4.63.0",
        "@rollup/rollup-openharmony-arm64": "4.63.0",
        "@rollup/rollup-win32-arm64-msvc": "4.63.0",
        "@rollup/rollup-win32-ia32-msvc": "4.63.0",
        "@rollup/rollup-win32-x64-gnu": "4.63.0",
        "@rollup/rollup-win32-x64-msvc": "4.63.0",
        "fsevents": "~2.3.2"
      }
    },
    "node_modules/rrweb-cssom": {
      "version": "0.8.0",
      "resolved": "https://registry.npmjs.org/rrweb-cssom/-/rrweb-cssom-0.8.0.tgz",
      "integrity": "sha512-guoltQEx+9aMf2gDZ0s62EcV8lsXR+0w8915TC3ITdn2YueuNjdAYh/levpU9nFaoChh9RUS5ZdQMrKfVEN9tw==",
      "dev": true
    },
    "node_modules/safer-buffer": {
      "version": "2.1.2",
      "resolved": "https://registry.npmjs.org/safer-buffer/-/safer-buffer-2.1.2.tgz",
      "integrity": "sha512-YZo3K82SD7Riyi0E1EQPojLz7kpepnSQI9IyPbHHg1XXXevb5dJI7tpyN2ADxGcQbHG7vcyRHk0cbwqcQriUtg==",
      "dev": true
    },
    "node_modules/saxes": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/saxes/-/saxes-6.0.0.tgz",
      "integrity": "sha512-xAg7SOnEhrm5zI3puOOKyy1OMcMlIJZYNJY7xLBwSze0UjhPLnWfj2GF2EpT0jmzaJKIWKHLsaSSajf35bcYnA==",
      "dev": true,
      "dependencies": {
        "xmlchars": "^2.2.0"
      },
      "engines": {
        "node": ">=v12.22.7"
      }
    },
    "node_modules/semver": {
      "version": "7.8.5",
      "resolved": "https://registry.npmjs.org/semver/-/semver-7.8.5.tgz",
      "integrity": "sha512-Y7/KDsb8LjooZpwaqGyulO6DQlksgCncchHGk+sZIY4SBvUocMBEFH5Ur1fI4dV+Jvl0w6cjvucaIi40puRioA==",
      "dev": true,
      "bin": {
        "semver": "bin/semver.js"
      },
      "engines": {
        "node": ">=10"
      }
    },
    "node_modules/shebang-command": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/shebang-command/-/shebang-command-2.0.0.tgz",
      "integrity": "sha512-kHxr2zZpYtdmrN1qDjrrX/Z1rR1kG8Dx+gkpK1G4eXmvXswmcE1hTWBWYUzlraYw1/yZp6YuDY77YtvbN0dmDA==",
      "dev": true,
      "dependencies": {
        "shebang-regex": "^3.0.0"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/shebang-regex": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/shebang-regex/-/shebang-regex-3.0.0.tgz",
      "integrity": "sha512-7++dFhtcx3353uBaq8DDR4NuxBetBzC7ZQOhmTQInHEd6bSrXdiEyzCvG07Z44UYdLShWUyXt5M/yhz8ekcb1A==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/siginfo": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/siginfo/-/siginfo-2.0.0.tgz",
      "integrity": "sha512-ybx0WO1/8bSBLEWXZvEd7gMW3Sn3JFlW3TvX1nREbDLRNQNaeNN8WK0meBwPdAaOI7TtRRRJn/Es1zhrrCHu7g==",
      "dev": true
    },
    "node_modules/signal-exit": {
      "version": "4.1.0",
      "resolved": "https://registry.npmjs.org/signal-exit/-/signal-exit-4.1.0.tgz",
      "integrity": "sha512-bzyZ1e88w9O1iNJbKnOlvYTrWPDl46O1bG0D3XInv+9tkPrxrN8jUUTiFlDkkmKWgn1M6CfIA13SuGqOa9Korw==",
      "dev": true,
      "engines": {
        "node": ">=14"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/stackback": {
      "version": "0.0.2",
      "resolved": "https://registry.npmjs.org/stackback/-/stackback-0.0.2.tgz",
      "integrity": "sha512-1XMJE5fQo1jGH6Y/7ebnwPOBEkIEnT4QF32d5R1+VXdXveM0IBMJt8zfaxX1P3QhVwrYe+576+jkANtSS2mBbw==",
      "dev": true
    },
    "node_modules/std-env": {
      "version": "3.10.0",
      "resolved": "https://registry.npmjs.org/std-env/-/std-env-3.10.0.tgz",
      "integrity": "sha512-5GS12FdOZNliM5mAOxFRg7Ir0pWz8MdpYm6AY6VPkGpbA7ZzmbzNcBJQ0GPvvyWgcY7QAhCgf9Uy89I03faLkg==",
      "dev": true
    },
    "node_modules/string-width": {
      "version": "5.1.2",
      "resolved": "https://registry.npmjs.org/string-width/-/string-width-5.1.2.tgz",
      "integrity": "sha512-HnLOCR3vjcY8beoNLtcjZ5/nxn2afmME6lhrDrebokqMap+XbeW8n9TXpPDOqdGK5qcI3oT0GKTW6wC7EMiVqA==",
      "dev": true,
      "dependencies": {
        "eastasianwidth": "^0.2.0",
        "emoji-regex": "^9.2.2",
        "strip-ansi": "^7.0.1"
      },
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/string-width-cjs": {
      "name": "string-width",
      "version": "4.2.3",
      "resolved": "https://registry.npmjs.org/string-width/-/string-width-4.2.3.tgz",
      "integrity": "sha512-wKyQRQpjJ0sIp62ErSZdGsjMJWsap5oRNihHhu6G7JVO/9jIB6UyevL+tXuOqrng8j/cxKTWyWUwvSTriiZz/g==",
      "dev": true,
      "dependencies": {
        "emoji-regex": "^8.0.0",
        "is-fullwidth-code-point": "^3.0.0",
        "strip-ansi": "^6.0.1"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/string-width-cjs/node_modules/ansi-regex": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-5.0.1.tgz",
      "integrity": "sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/string-width-cjs/node_modules/emoji-regex": {
      "version": "8.0.0",
      "resolved": "https://registry.npmjs.org/emoji-regex/-/emoji-regex-8.0.0.tgz",
      "integrity": "sha512-MSjYzcWNOA0ewAHpz0MxpYFvwg6yjy1NG3xteoqz644VCo/RPgnr1/GGt+ic3iJTzQ8Eu3TdM14SawnVUmGE6A==",
      "dev": true
    },
    "node_modules/string-width-cjs/node_modules/strip-ansi": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-6.0.1.tgz",
      "integrity": "sha512-Y38VPSHcqkFrCpFnQ9vuSXmquuv5oXOKpGeT6aGrr3o3Gc9AlVa6JBfUSOCnbxGGZF+/0ooI7KrPuUSztUdU5A==",
      "dev": true,
      "dependencies": {
        "ansi-regex": "^5.0.1"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/strip-ansi": {
      "version": "7.2.0",
      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-7.2.0.tgz",
      "integrity": "sha512-yDPMNjp4WyfYBkHnjIRLfca1i6KMyGCtsVgoKe/z1+6vukgaENdgGBZt+ZmKPc4gavvEZ5OgHfHdrazhgNyG7w==",
      "dev": true,
      "dependencies": {
        "ansi-regex": "^6.2.2"
      },
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/chalk/strip-ansi?sponsor=1"
      }
    },
    "node_modules/strip-ansi-cjs": {
      "name": "strip-ansi",
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-6.0.1.tgz",
      "integrity": "sha512-Y38VPSHcqkFrCpFnQ9vuSXmquuv5oXOKpGeT6aGrr3o3Gc9AlVa6JBfUSOCnbxGGZF+/0ooI7KrPuUSztUdU5A==",
      "dev": true,
      "dependencies": {
        "ansi-regex": "^5.0.1"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/strip-ansi-cjs/node_modules/ansi-regex": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-5.0.1.tgz",
      "integrity": "sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/strip-literal": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/strip-literal/-/strip-literal-3.1.0.tgz",
      "integrity": "sha512-8r3mkIM/2+PpjHoOtiAW8Rg3jJLHaV7xPwG+YRGrv6FP0wwk/toTpATxWYOW0BKdWwl82VT2tFYi5DlROa0Mxg==",
      "dev": true,
      "dependencies": {
        "js-tokens": "^9.0.1"
      },
      "funding": {
        "url": "https://github.com/sponsors/antfu"
      }
    },
    "node_modules/symbol-tree": {
      "version": "3.2.4",
      "resolved": "https://registry.npmjs.org/symbol-tree/-/symbol-tree-3.2.4.tgz",
      "integrity": "sha512-9QNk5KwDF+Bvz+PyObkmSYjI5ksVUYtjW7AU22r2NKcfLJcXp96hkDWU3+XndOsUb+AQ9QhfzfCT2O+CNWT5Tw==",
      "dev": true
    },
    "node_modules/tinybench": {
      "version": "2.9.0",
      "resolved": "https://registry.npmjs.org/tinybench/-/tinybench-2.9.0.tgz",
      "integrity": "sha512-0+DUvqWMValLmha6lr4kD8iAMK1HzV0/aKnCtWb9v9641TnP/MFb7Pc2bxoxQjTXAErryXVgUOfv2YqNllqGeg==",
      "dev": true
    },
    "node_modules/tinyexec": {
      "version": "0.3.2",
      "resolved": "https://registry.npmjs.org/tinyexec/-/tinyexec-0.3.2.tgz",
      "integrity": "sha512-KQQR9yN7R5+OSwaK0XQoj22pwHoTlgYqmUscPYoknOoWCWfj/5/ABTMRi69FrKU5ffPVh5QcFikpWJI/P1ocHA==",
      "dev": true
    },
    "node_modules/tinyglobby": {
      "version": "0.2.17",
      "resolved": "https://registry.npmjs.org/tinyglobby/-/tinyglobby-0.2.17.tgz",
      "integrity": "sha512-wXR/dYpcqKmfWpEdZjiKJOwCNFndD0DMnrW/cYjVGttEkBfVgcLFHoNrlj47mjOVic9yyNu65alsgF4NQyTa2g==",
      "dev": true,
      "dependencies": {
        "fdir": "^6.5.0",
        "picomatch": "^4.0.4"
      },
      "engines": {
        "node": ">=12.0.0"
      },
      "funding": {
        "url": "https://github.com/sponsors/SuperchupuDev"
      }
    },
    "node_modules/tinypool": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/tinypool/-/tinypool-1.1.1.tgz",
      "integrity": "sha512-Zba82s87IFq9A9XmjiX5uZA/ARWDrB03OHlq+Vw1fSdt0I+4/Kutwy8BP4Y/y/aORMo61FQ0vIb5j44vSo5Pkg==",
      "dev": true,
      "engines": {
        "node": "^18.0.0 || >=20.0.0"
      }
    },
    "node_modules/tinyrainbow": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/tinyrainbow/-/tinyrainbow-2.0.0.tgz",
      "integrity": "sha512-op4nsTR47R6p0vMUUoYl/a+ljLFVtlfaXkLQmqfLR1qHma1h/ysYk4hEXZ880bf2CYgTskvTa/e196Vd5dDQXw==",
      "dev": true,
      "engines": {
        "node": ">=14.0.0"
      }
    },
    "node_modules/tinyspy": {
      "version": "4.0.4",
      "resolved": "https://registry.npmjs.org/tinyspy/-/tinyspy-4.0.4.tgz",
      "integrity": "sha512-azl+t0z7pw/z958Gy9svOTuzqIk6xq+NSheJzn5MMWtWTFywIacg2wUlzKFGtt3cthx0r2SxMK0yzJOR0IES7Q==",
      "dev": true,
      "engines": {
        "node": ">=14.0.0"
      }
    },
    "node_modules/tldts": {
      "version": "6.1.86",
      "resolved": "https://registry.npmjs.org/tldts/-/tldts-6.1.86.tgz",
      "integrity": "sha512-WMi/OQ2axVTf/ykqCQgXiIct+mSQDFdH2fkwhPwgEwvJ1kSzZRiinb0zF2Xb8u4+OqPChmyI6MEu4EezNJz+FQ==",
      "dev": true,
      "dependencies": {
        "tldts-core": "^6.1.86"
      },
      "bin": {
        "tldts": "bin/cli.js"
      }
    },
    "node_modules/tldts-core": {
      "version": "6.1.86",
      "resolved": "https://registry.npmjs.org/tldts-core/-/tldts-core-6.1.86.tgz",
      "integrity": "sha512-Je6p7pkk+KMzMv2XXKmAE3McmolOQFdxkKw0R8EYNr7sELW46JqnNeTX8ybPiQgvg1ymCoF8LXs5fzFaZvJPTA==",
      "dev": true
    },
    "node_modules/tough-cookie": {
      "version": "5.1.2",
      "resolved": "https://registry.npmjs.org/tough-cookie/-/tough-cookie-5.1.2.tgz",
      "integrity": "sha512-FVDYdxtnj0G6Qm/DhNPSb8Ju59ULcup3tuJxkFb5K8Bv2pUXILbf0xZWU8PX8Ov19OXljbUyveOFwRMwkXzO+A==",
      "dev": true,
      "dependencies": {
        "tldts": "^6.1.32"
      },
      "engines": {
        "node": ">=16"
      }
    },
    "node_modules/tr46": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/tr46/-/tr46-5.1.1.tgz",
      "integrity": "sha512-hdF5ZgjTqgAntKkklYw0R03MG2x/bSzTtkxmIRw/sTNV8YXsCJ1tfLAX23lhxhHJlEf3CRCOCGGWw3vI3GaSPw==",
      "dev": true,
      "dependencies": {
        "punycode": "^2.3.1"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/typescript": {
      "version": "5.9.3",
      "resolved": "https://registry.npmjs.org/typescript/-/typescript-5.9.3.tgz",
      "integrity": "sha512-jl1vZzPDinLr9eUt3J/t7V6FgNEw9QjvBPdysz9KfQDD41fQrC2Y4vKQdiaUpFT4bXlb1RHhLpp8wtm6M5TgSw==",
      "devOptional": true,
      "bin": {
        "tsc": "bin/tsc",
        "tsserver": "bin/tsserver"
      },
      "engines": {
        "node": ">=14.17"
      }
    },
    "node_modules/undici-types": {
      "version": "6.21.0",
      "resolved": "https://registry.npmjs.org/undici-types/-/undici-types-6.21.0.tgz",
      "integrity": "sha512-iwDZqg0QAGrg9Rav5H4n0M64c3mkR59cJ6wQp+7C4nI0gsmExaedaYLNO44eT4AtBBwjbTiGPMlt2Md0T9H9JQ==",
      "dev": true
    },
    "node_modules/vite": {
      "version": "6.4.3",
      "resolved": "https://registry.npmjs.org/vite/-/vite-6.4.3.tgz",
      "integrity": "sha512-NTKlcQjlAK7MlQoyb6LgaqHc8sso/pVyUJYWMws3jg21uTJw/LddqIFPcPqP6PzpgbIcZyKI85sFE4HBrQDA8A==",
      "dev": true,
      "dependencies": {
        "esbuild": "^0.25.0",
        "fdir": "^6.4.4",
        "picomatch": "^4.0.2",
        "postcss": "^8.5.3",
        "rollup": "^4.34.9",
        "tinyglobby": "^0.2.13"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^18.0.0 || ^20.0.0 || >=22.0.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^18.0.0 || ^20.0.0 || >=22.0.0",
        "jiti": ">=1.21.0",
        "less": "*",
        "lightningcss": "^1.21.0",
        "sass": "*",
        "sass-embedded": "*",
        "stylus": "*",
        "sugarss": "*",
        "terser": "^5.16.0",
        "tsx": "^4.8.1",
        "yaml": "^2.4.2"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "jiti": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "lightningcss": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        },
        "tsx": {
          "optional": true
        },
        "yaml": {
          "optional": true
        }
      }
    },
    "node_modules/vite-node": {
      "version": "3.2.4",
      "resolved": "https://registry.npmjs.org/vite-node/-/vite-node-3.2.4.tgz",
      "integrity": "sha512-EbKSKh+bh1E1IFxeO0pg1n4dvoOTt0UDiXMd/qn++r98+jPO1xtJilvXldeuQ8giIB5IkpjCgMleHMNEsGH6pg==",
      "dev": true,
      "dependencies": {
        "cac": "^6.7.14",
        "debug": "^4.4.1",
        "es-module-lexer": "^1.7.0",
        "pathe": "^2.0.3",
        "vite": "^5.0.0 || ^6.0.0 || ^7.0.0-0"
      },
      "bin": {
        "vite-node": "vite-node.mjs"
      },
      "engines": {
        "node": "^18.0.0 || ^20.0.0 || >=22.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/vitest": {
      "version": "3.2.7",
      "resolved": "https://registry.npmjs.org/vitest/-/vitest-3.2.7.tgz",
      "integrity": "sha512-KrxIJ62Fd89gfysR4WotlgZABiz2dqFPgqGzX7s+CwsqLFomRH7777ZcrOD6+WVAh7khPQP41A+BKbpcJFrdEg==",
      "dev": true,
      "dependencies": {
        "@types/chai": "^5.2.2",
        "@vitest/expect": "3.2.7",
        "@vitest/mocker": "3.2.7",
        "@vitest/pretty-format": "^3.2.7",
        "@vitest/runner": "3.2.7",
        "@vitest/snapshot": "3.2.7",
        "@vitest/spy": "3.2.7",
        "@vitest/utils": "3.2.7",
        "chai": "^5.2.0",
        "debug": "^4.4.1",
        "expect-type": "^1.2.1",
        "magic-string": "^0.30.17",
        "pathe": "^2.0.3",
        "picomatch": "^4.0.2",
        "std-env": "^3.9.0",
        "tinybench": "^2.9.0",
        "tinyexec": "^0.3.2",
        "tinyglobby": "^0.2.14",
        "tinypool": "^1.1.1",
        "tinyrainbow": "^2.0.0",
        "vite": "^5.0.0 || ^6.0.0 || ^7.0.0-0",
        "vite-node": "3.2.4",
        "why-is-node-running": "^2.3.0"
      },
      "bin": {
        "vitest": "vitest.mjs"
      },
      "engines": {
        "node": "^18.0.0 || ^20.0.0 || >=22.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "@edge-runtime/vm": "*",
        "@types/debug": "^4.1.12",
        "@types/node": "^18.0.0 || ^20.0.0 || >=22.0.0",
        "@vitest/browser": "3.2.7",
        "@vitest/ui": "3.2.7",
        "happy-dom": "*",
        "jsdom": "*"
      },
      "peerDependenciesMeta": {
        "@edge-runtime/vm": {
          "optional": true
        },
        "@types/debug": {
          "optional": true
        },
        "@types/node": {
          "optional": true
        },
        "@vitest/browser": {
          "optional": true
        },
        "@vitest/ui": {
          "optional": true
        },
        "happy-dom": {
          "optional": true
        },
        "jsdom": {
          "optional": true
        }
      }
    },
    "node_modules/vscode-uri": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/vscode-uri/-/vscode-uri-3.2.0.tgz",
      "integrity": "sha512-m2gXo3bn0G1kT9InzMf07fTbqMbGtyckj3bH5ktLO+1Ssv+yiATZ4dhwaQv9UZWxJh6E9IFGnQyjgWVDWVBDrg==",
      "dev": true
    },
    "node_modules/vue": {
      "version": "3.5.41",
      "resolved": "https://registry.npmjs.org/vue/-/vue-3.5.41.tgz",
      "integrity": "sha512-2laE0p+aK+/AOPG/XL/WepOs/GlK755LJ1XECi9kDUrz1FKNw8rb2Xzlw9JS1rqEV55nb0ttsKxVlTCcd+R5cg==",
      "dependencies": {
        "@vue/compiler-dom": "3.5.41",
        "@vue/compiler-sfc": "3.5.41",
        "@vue/runtime-dom": "3.5.41",
        "@vue/server-renderer": "3.5.41",
        "@vue/shared": "3.5.41"
      },
      "peerDependencies": {
        "typescript": "*"
      },
      "peerDependenciesMeta": {
        "typescript": {
          "optional": true
        }
      }
    },
    "node_modules/vue-component-type-helpers": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/vue-component-type-helpers/-/vue-component-type-helpers-3.3.11.tgz",
      "integrity": "sha512-LwcxzeliO9fkQcpJG0PoX8X5kmAhKmH9wkpDLxNabwzkQ9Zeib2YVHwFV4pcWmMLfXVfjr/dSV+DaJ3cIPgSNA==",
      "dev": true
    },
    "node_modules/vue-tsc": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/vue-tsc/-/vue-tsc-3.3.11.tgz",
      "integrity": "sha512-gOb0B9rtU2+f1dszwPqSH5kAieIF9ReeLhD3kSRNHv5WZZUQz/JdVXW0RTdqhNTMlQkqKzrTTviqKr/4FYZraQ==",
      "dev": true,
      "dependencies": {
        "@volar/typescript": "2.4.28",
        "@vue/language-core": "3.3.11"
      },
      "bin": {
        "vue-tsc": "bin/vue-tsc.js"
      },
      "peerDependencies": {
        "typescript": ">=5.0.0"
      }
    },
    "node_modules/w3c-xmlserializer": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/w3c-xmlserializer/-/w3c-xmlserializer-5.0.0.tgz",
      "integrity": "sha512-o8qghlI8NZHU1lLPrpi2+Uq7abh4GGPpYANlalzWxyWteJOCsr/P+oPBA49TOLu5FTZO4d3F9MnWJfiMo4BkmA==",
      "dev": true,
      "dependencies": {
        "xml-name-validator": "^5.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/webidl-conversions": {
      "version": "7.0.0",
      "resolved": "https://registry.npmjs.org/webidl-conversions/-/webidl-conversions-7.0.0.tgz",
      "integrity": "sha512-VwddBukDzu71offAQR975unBIGqfKZpM+8ZX6ySk8nYhVoo5CYaZyzt3YBvYtRtO+aoGlqxPg/B87NGVZ/fu6g==",
      "dev": true,
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/whatwg-encoding": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/whatwg-encoding/-/whatwg-encoding-3.1.1.tgz",
      "integrity": "sha512-6qN4hJdMwfYBtE3YBTTHhoeuUrDBPZmbQaxWAqSALV/MeEnR5z1xd8UKud2RAkFoPkmB+hli1TZSnyi84xz1vQ==",
      "deprecated": "Use @exodus/bytes instead for a more spec-conformant and faster implementation",
      "dev": true,
      "dependencies": {
        "iconv-lite": "0.6.3"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/whatwg-mimetype": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/whatwg-mimetype/-/whatwg-mimetype-4.0.0.tgz",
      "integrity": "sha512-QaKxh0eNIi2mE9p2vEdzfagOKHCcj1pJ56EEHGQOVxp8r9/iszLUUV7v89x9O1p/T+NlTM5W7jW6+cz4Fq1YVg==",
      "dev": true,
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/whatwg-url": {
      "version": "14.2.0",
      "resolved": "https://registry.npmjs.org/whatwg-url/-/whatwg-url-14.2.0.tgz",
      "integrity": "sha512-De72GdQZzNTUBBChsXueQUnPKDkg/5A5zp7pFDuQAj5UFoENpiACU0wlCvzpAGnTkj++ihpKwKyYewn/XNUbKw==",
      "dev": true,
      "dependencies": {
        "tr46": "^5.1.0",
        "webidl-conversions": "^7.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/which": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/which/-/which-2.0.2.tgz",
      "integrity": "sha512-BLI3Tl1TW3Pvl70l3yq3Y64i+awpwXqsGBYWkkqMtnbXgrMD+yj7rhW0kuEDxzJaYXGjEW5ogapKNMEKNMjibA==",
      "dev": true,
      "dependencies": {
        "isexe": "^2.0.0"
      },
      "bin": {
        "node-which": "bin/node-which"
      },
      "engines": {
        "node": ">= 8"
      }
    },
    "node_modules/why-is-node-running": {
      "version": "2.3.0",
      "resolved": "https://registry.npmjs.org/why-is-node-running/-/why-is-node-running-2.3.0.tgz",
      "integrity": "sha512-hUrmaWBdVDcxvYqnyh09zunKzROWjbZTiNy8dBEjkS7ehEDQibXJ7XvlmtbwuTclUiIyN+CyXQD4Vmko8fNm8w==",
      "dev": true,
      "dependencies": {
        "siginfo": "^2.0.0",
        "stackback": "0.0.2"
      },
      "bin": {
        "why-is-node-running": "cli.js"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/wrap-ansi": {
      "version": "8.1.0",
      "resolved": "https://registry.npmjs.org/wrap-ansi/-/wrap-ansi-8.1.0.tgz",
      "integrity": "sha512-si7QWI6zUMq56bESFvagtmzMdGOtoxfR+Sez11Mobfc7tm+VkUckk9bW2UeffTGVUbOksxmSw0AA2gs8g71NCQ==",
      "dev": true,
      "dependencies": {
        "ansi-styles": "^6.1.0",
        "string-width": "^5.0.1",
        "strip-ansi": "^7.0.1"
      },
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/chalk/wrap-ansi?sponsor=1"
      }
    },
    "node_modules/wrap-ansi-cjs": {
      "name": "wrap-ansi",
      "version": "7.0.0",
      "resolved": "https://registry.npmjs.org/wrap-ansi/-/wrap-ansi-7.0.0.tgz",
      "integrity": "sha512-YVGIj2kamLSTxw6NsZjoBxfSwsn0ycdesmc4p+Q21c5zPuZ1pl+NfxVdxPtdHvmNVOQ6XSYG4AUtyt/Fi7D16Q==",
      "dev": true,
      "dependencies": {
        "ansi-styles": "^4.0.0",
        "string-width": "^4.1.0",
        "strip-ansi": "^6.0.0"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/chalk/wrap-ansi?sponsor=1"
      }
    },
    "node_modules/wrap-ansi-cjs/node_modules/ansi-regex": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-5.0.1.tgz",
      "integrity": "sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==",
      "dev": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/wrap-ansi-cjs/node_modules/ansi-styles": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-4.3.0.tgz",
      "integrity": "sha512-zbB9rCJAT1rbjiVDb2hqKFHNYLxgtk8NURxZ3IZwD3F6NtxbXZQCnnSi1Lkx+IDohdPlFp222wVALIheZJQSEg==",
      "dev": true,
      "dependencies": {
        "color-convert": "^2.0.1"
      },
      "engines": {
        "node": ">=8"
      },
      "funding": {
        "url": "https://github.com/chalk/ansi-styles?sponsor=1"
      }
    },
    "node_modules/wrap-ansi-cjs/node_modules/emoji-regex": {
      "version": "8.0.0",
      "resolved": "https://registry.npmjs.org/emoji-regex/-/emoji-regex-8.0.0.tgz",
      "integrity": "sha512-MSjYzcWNOA0ewAHpz0MxpYFvwg6yjy1NG3xteoqz644VCo/RPgnr1/GGt+ic3iJTzQ8Eu3TdM14SawnVUmGE6A==",
      "dev": true
    },
    "node_modules/wrap-ansi-cjs/node_modules/string-width": {
      "version": "4.2.3",
      "resolved": "https://registry.npmjs.org/string-width/-/string-width-4.2.3.tgz",
      "integrity": "sha512-wKyQRQpjJ0sIp62ErSZdGsjMJWsap5oRNihHhu6G7JVO/9jIB6UyevL+tXuOqrng8j/cxKTWyWUwvSTriiZz/g==",
      "dev": true,
      "dependencies": {
        "emoji-regex": "^8.0.0",
        "is-fullwidth-code-point": "^3.0.0",
        "strip-ansi": "^6.0.1"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/wrap-ansi-cjs/node_modules/strip-ansi": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-6.0.1.tgz",
      "integrity": "sha512-Y38VPSHcqkFrCpFnQ9vuSXmquuv5oXOKpGeT6aGrr3o3Gc9AlVa6JBfUSOCnbxGGZF+/0ooI7KrPuUSztUdU5A==",
      "dev": true,
      "dependencies": {
        "ansi-regex": "^5.0.1"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/ws": {
      "version": "8.21.3",
      "resolved": "https://registry.npmjs.org/ws/-/ws-8.21.3.tgz",
      "integrity": "sha512-201TZ/kPWxoPr/OKWjquZR1SWKXcvxdH+e1xrx89b3YbmzLMFCLfnaG1HFIgWzJOEWZ7MvpK++odZufgYR50Rw==",
      "dev": true,
      "engines": {
        "node": ">=10.0.0"
      },
      "peerDependencies": {
        "bufferutil": "^4.0.1",
        "utf-8-validate": ">=5.0.2"
      },
      "peerDependenciesMeta": {
        "bufferutil": {
          "optional": true
        },
        "utf-8-validate": {
          "optional": true
        }
      }
    },
    "node_modules/xml-name-validator": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/xml-name-validator/-/xml-name-validator-5.0.0.tgz",
      "integrity": "sha512-EvGK8EJ3DhaHfbRlETOWAS5pO9MZITeauHKJyb8wyajUfQUenkIg2MvLDTZ4T/TgIcm3HU0TFBgWWboAZ30UHg==",
      "dev": true,
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/xmlchars": {
      "version": "2.2.0",
      "resolved": "https://registry.npmjs.org/xmlchars/-/xmlchars-2.2.0.tgz",
      "integrity": "sha512-JZnDKK8B0RCDw84FNdDAIpZK+JuJw+s7Lz8nksI7SIuU3UXJJslUthsi+uWBUYOwPFwW7W7PRLRfUKpxjtjFCw==",
      "dev": true
    }
  }
}

```
`frontend/package.json`:

```json
{
  "name": "avalo-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vue-tsc --noEmit -p tsconfig.app.json && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "vue": "^3.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "@types/node": "^22.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^26.0.0",
    "typescript": "^5.8.0",
    "vite": "^6.0.0",
    "vitest": "^3.2.0",
    "vue-tsc": "^3.0.0"
  }
}

```
`frontend/src/App.vue`:

```vue
<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getBackendHealth } from "./services/backend";

const backendStatus = ref("Prüfe Backend …");

onMounted(async () => {
  try {
    const health = await getBackendHealth();
    backendStatus.value = `${health.service}: ${health.status}`;
  } catch {
    backendStatus.value = "Backend nicht erreichbar";
  }
});
</script>

<template>
  <main class="app-shell">
    <h1>Avalo</h1>
    <p>Lokaler Companion – Grundgerüst</p>
    <p class="status" data-testid="backend-status">{{ backendStatus }}</p>
  </main>
</template>


```
`frontend/src/env.d.ts`:

```ts
/// <reference types="vite/client" />


```
`frontend/src/main.ts`:

```ts
import { createApp } from "vue";

import App from "./App.vue";
import "./styles.css";

createApp(App).mount("#app");


```
`frontend/src/services/backend.ts`:

```ts
import type { ChatResponse } from "../types/chat";

const BACKEND_BASE_URL = "http://127.0.0.1:8095";

export interface BackendHealth {
  status: "ok";
  service: string;
}

export async function getBackendHealth(): Promise<BackendHealth> {
  const response = await fetch(`${BACKEND_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed with ${response.status}`);
  }
  return response.json() as Promise<BackendHealth>;
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  void message;
  throw new Error("Text chat is not implemented yet.");
}


```
`frontend/src/styles.css`:

```css
:root {
  font-family: Inter, system-ui, sans-serif;
  color: #e8e8ea;
  background: #17181c;
}

body {
  margin: 0;
}

.app-shell {
  width: min(42rem, calc(100% - 3rem));
  margin: 15vh auto;
}

.status {
  color: #9fa8ff;
}


```
`frontend/src/types/chat.ts`:

```ts
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  message: string;
}


```
`frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals"]
  },
  "include": ["src/**/*.ts", "src/**/*.vue"]
}

```
`frontend/tsconfig.json`:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}


```
`frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}


```
`frontend/vite.config.ts`:

```ts
import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    fs: {
      allow: [".."],
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@vue/test-utils": fileURLToPath(
        new URL(
          "./node_modules/@vue/test-utils/dist/vue-test-utils.esm-bundler.mjs",
          import.meta.url,
        ),
      ),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["../tests/frontend/**/*.spec.ts"],
  },
});

```
`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "avalo-backend"
version = "0.1.0"
description = "Local backend for Avalo"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115,<1",
    "pydantic>=2.10,<3",
    "uvicorn[standard]>=0.34,<1",
    "httpx>=0.28,<1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9",
    "pytest-httpx>=0.20,<1",
    "pytest-asyncio>=0.20,<1",
]

[tool.setuptools.packages.find]
where = ["backend"]

[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests/backend", "tests/integration"]

```
`scripts/code2prompt-adrs.md`:

```md
Project Path: adrs

Source Tree:

```txt
adrs
├── 00-architecture-high-level.md
├── 01-desktop-process-architecture.md
├── 02-frontend-vue.md
├── 03-backend-fastapi.md
├── 04-local-llm-runtime.md
├── 05-loopback-http-communication.md
├── 06-native-gemma-audio.md
├── 07-tts-output.md
├── 08-incremental-repo-map-as-ai-working-index.md
└── 09-source-patching-via-prompt2code.md

```

`00-architecture-high-level.md`:

```md
# Avalo – grobe Architektur

## 1. Ziel des ersten Ausbaus

1. Runtime-Spike für Gemma 4
2. lokaler Textchat
3. Push-to-Talk mit nativem Audioinput
4. lokale Sprachausgabe

Nicht enthalten:

- persistente Chats oder Memory
- Persönlichkeit/Character
- kontinuierliche Sprachaufnahme
- Modellinstallation oder -löschung
- Linux-Paket/Installer

## 2. Komponenten

| Komponente | Technologie | Verantwortung |
|---|---|---|
| Desktop Shell | Tauri/Rust | Fenster, Anwendungsstart, Backend-Prozess |
| Frontend | Vue 3, TypeScript, Vite | Chat-UI, später Audioaufnahme/-wiedergabe |
| Backend | Python, FastAPI | Gesprächslogik, Runtime- und Audio-Orchestrierung |
| Model Runtime | noch offen | Gemma-4-Inferenz für Text und natives Audio |
| TTS | noch offen | lokale natürliche deutsche Sprachausgabe |

## 3. Kommunikation

- Backend: `127.0.0.1:8095`
- Port zentral und zunächst fest konfiguriert
- HTTP/JSON für Textchat und Status
- Antworten zunächst vollständig statt tokenweise
- Streaming später ergänzbar
- API ausschließlich an Loopback gebunden

## 4. Backend-Struktur

- `api`: HTTP-Endpunkte und Datenmodelle
- `application`: Gesprächsablauf und Anwendungsfälle
- `runtime`: austauschbare LLM-Anbindung
- `audio`: Aufnahmeformate und spätere Audioaufbereitung
- `tts`: austauschbare Sprachausgabe
- `config`: zentrale technische Konfiguration

Gesprächskontext bleibt im Arbeitsspeicher und endet mit der Anwendung.

## 5. Repository

´´´
avalo/
├── backend/
├── frontend/
├── src-tauri/
├── tests/
│   ├── backend/
│   ├── frontend/
│   └── integration/
├── docs/
│   └── adr/
├── scripts/
└── pyproject.toml
´´´

Python: `venv`, `pip`, `pyproject.toml`  
Frontend: npm mit `package-lock.json`

## 6. Runtime-Spike

Zu prüfen:

- Gemma `gemma4:e4b-it-q4_K_M` beziehungsweise kompatible Gewichte
- Textinput und deutsche Antwort
- direkter Audioinput ohne separates STT
- maximal 30 Sekunden Audio
- CUDA-Nutzung auf RTX 4060/8 GB
- RAM-/VRAM-Bedarf
- Antwortzeiten und Stabilität
- Python-Anbindung
- Lizenz und lokale Nutzbarkeit

Ergebnis: begründete Runtime-Entscheidung oder dokumentierter Blocker.

## 7. Entwicklungsreihenfolge

1. Runtime-Spike
2. Runtime-ADR
3. Backend-Grundgerüst und Health-Check
4. Textchat-Endpunkt
5. rudimentäre Vue-Chatoberfläche
6. Tauri-Integration
7. Push-to-Talk
8. TTS-Spike und Sprachausgabe

## 8. ADRs

./docs/adrs


```
`01-desktop-process-architecture.md`:

```md
# ADR 01: Desktop- und Prozessarchitektur

- Status: Angenommen
- Datum: 2026-08-26

## Kontext

Avalo ist zunächst eine lokale Linux-Desktop-Anwendung. UI, native Desktop-Funktionen und das Python-basierte KI-/Audio-Backend haben unterschiedliche technische Anforderungen.

## Entscheidung

- Tauri bildet die Desktop-Hülle.
- Das Vue-Frontend läuft im Tauri-Webview.
- Das Python-Backend läuft als eigener lokaler Prozess.
- Tauri startet, überwacht und beendet den von Avalo gestarteten Backend-Prozess.
- Eine nicht von Avalo gestartete externe Modell-Runtime wird nicht beendet.
- Zunächst wird nur der Entwicklungsstart aus dem Repository unterstützt.

## Konsequenzen

- Rust bleibt auf Desktop- und Prozessfunktionen begrenzt.
- Python-Abstürze beenden nicht zwangsläufig die Desktop-Hülle und können verständlich gemeldet werden.
- Prozessstart, Bereitschaft, Fehler und Shutdown benötigen Integrationstests.
- Packaging und Sidecar-Bündelung werden später entschieden.

## Verworfene Alternativen

- Vollständige Anwendung in Rust: unnötig hohe Hürde für Modell- und Audiointegration.
- Reine Browseranwendung: ungeeignet für den gewünschten Desktop- und Prozesslebenszyklus.


```
`02-frontend-vue.md`:

```md
# ADR 02: Frontend mit Vue 3

- Status: Angenommen
- Datum: 2026-08-26

## Kontext

Das Frontend soll klein, wartbar und für die Umsetzung mit Aider und `qwen2.5-coder:14b-instruct` gut beherrschbar sein.

## Entscheidung

- Vue 3 mit Composition API und Single-File Components
- TypeScript mit strikter Typprüfung
- Vite als Build- und Entwicklungswerkzeug
- npm als Paketmanager; `package-lock.json` wird versioniert
- Komponenten bleiben klein und fachlich zugeschnitten.

## Konsequenzen

- Template, Logik und komponentenbezogene Styles bleiben übersichtlich zusammen.
- TypeScript-Verträge machen die Kommunikation mit dem Backend prüfbarer.
- Framework-spezifische Abstraktionen werden nur bei erkennbarem Nutzen ergänzt.

## Verworfene Alternativen

- Angular: für Umfang und Lernziel unnötig schwergewichtig.
- React: mehr Boilerplate und typische Hook-Komplexität ohne erkennbaren Vorteil.
- Svelte 5: kompakt, aber das jüngere Runes-Modell ist für das lokale Codingmodell weniger konservativ.

## Quellen

- [Vue: Composition API FAQ](https://vuejs.org/guide/extras/composition-api-faq)
- [Vue mit TypeScript](https://vuejs.org/guide/typescript/overview)


```
`03-backend-fastapi.md`:

```md
# ADR 03: Python-Backend mit FastAPI

- Status: Angenommen
- Datum: 2026-08-26

## Kontext

Modell-, Audio- und TTS-Bibliotheken sind überwiegend gut aus Python nutzbar. Die Desktop-Hülle soll von diesen Details entkoppelt bleiben.

## Entscheidung

- Python bildet das lokale Anwendungs-Backend.
- FastAPI stellt die interne HTTP-API bereit.
- Abhängigkeiten stehen in `pyproject.toml`.
- Die Entwicklungsumgebung verwendet Standard-`venv` und `pip`, zunächst ohne zusätzliches Lock-Werkzeug.
- Das Backend wird mindestens in `api`, `application`, `runtime`, `audio`, `tts` und `config` gegliedert.
- Gesprächszustand bleibt im ersten Ausbau ausschließlich im Arbeitsspeicher.

## Konsequenzen

- KI-Komponenten können hinter Python-Protokollen ausgetauscht und isoliert getestet werden.
- API-Schemas bilden eine klare Grenze zum Frontend.
- Persistenz, Memory und Benutzerverwaltung sind ausdrücklich nicht enthalten.
- Vor einer Distribution muss ein reproduzierbares Lock- und Packaging-Konzept entschieden werden.

## Verworfene Alternativen

- Modelllogik direkt in Tauri/Rust: schlechtere Bibliotheksauswahl und höhere Implementierungshürde.
- Node.js-Backend: kein ausreichender Vorteil gegenüber dem stärkeren Python-Ökosystem für lokale KI.


```
`04-local-llm-runtime.md`:

```md
# ADR 04: Lokale LLM-Runtime für Avalo

- Status: Vorgeschlagen; durch Runtime-Spike zu bestätigen
- Datum: 2026-08-26

## Kontext

Avalos primäres Chatmodell ist Gemma 4 E4B. Text und nativer Audioinput sollen nach Möglichkeit über dieselbe lokale Runtime laufen. Ollama unterstützt den Textbetrieb, weist den gewählten Modell-Tag derzeit jedoch nicht verlässlich als Audioeingabe aus. Die Aider-Runtime ist von dieser Entscheidung unabhängig.

## Entscheidung

- Bevorzugter Kandidat für Avalo ist aktuelles `llama.cpp` mit CUDA, `llama-server`, Gemma-4-E4B-GGUF und zugehörigem multimodalem Projektor.
- Die Python-Anwendung greift über einen `ModelRuntime`-Adapter zu und kennt keine `llama.cpp`-Details.
- Die Entscheidung wird erst nach einem reproduzierbaren Spike auf der RTX 4060 Laptop GPU mit 8 GB VRAM endgültig angenommen.
- Ollama bleibt für Aider mit `qwen2.5-coder:14b-instruct` nutzbar, ist aber nicht Avalos zunächst vorgesehene Bot-Runtime.

## Erfolgskriterien des Spikes

- deutscher Textdialog;
- direkter Audioinput ohne separates STT;
- stabile Python-/HTTP-Anbindung;
- nachweisbare CUDA-Nutzung;
- dokumentierter RAM-/VRAM-Bedarf und Antwortzeiten;
- reproduzierbarer Start mit festgehaltenen Modell- und Runtime-Versionen.

## Konsequenzen

- GGUF und CPU/GPU-Offloading sind für 8 GB VRAM grundsätzlich erprobbar, aber noch nicht als ausreichend nachgewiesen.
- Die experimentelle Audio-Unterstützung ist das größte technische Risiko.
- Bei Scheitern wird eine alternative lokale Runtime geprüft; die Anwendungslogik bleibt durch den Adapter erhalten.

## Quellen

- [`llama.cpp`: Multimodal-Unterstützung](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- [Google: Gemma 4 Audio Understanding](https://ai.google.dev/gemma/docs/capabilities/audio)


```
`05-loopback-http-communication.md`:

```md
# ADR 05: Lokale Kommunikation über Loopback-HTTP

- Status: Angenommen
- Datum: 2026-08-26

## Kontext

Vue/Tauri und das Python-Backend laufen in getrennten Prozessen. Die Schnittstelle soll einfach testbar, transparent und später um Streaming sowie Audio erweiterbar sein.

## Entscheidung

- Das Backend bindet ausschließlich an `127.0.0.1:8095`.
- Port `8095` steht als fester zentraler Wert in der Python-Konfiguration.
- Eine Portkollision führt zu einem verständlichen Startfehler; es gibt kein automatisches Ausweichen.
- Der erste Textchat verwendet HTTP mit JSON und liefert vollständige Antworten.
- Ein Health-Endpunkt signalisiert die Bereitschaft des Backends.
- Streaming und Audiotransport werden später auf Basis konkreter Anforderungen ergänzt.

## Konsequenzen

- Backend-Endpunkte lassen sich unabhängig von Tauri testen.
- Der bekannte Port vereinfacht Entwicklungsstart und Frontend-Konfiguration.
- Loopback begrenzt den Netzwerkzugriff, ist aber keine Authentifizierung.
- Bevor Avalo zustandsändernde Werkzeuge erhält, muss der Schutz der lokalen API neu bewertet werden.

## Verworfene Alternativen

- Dynamischer Port: erfordert zusätzliche Portübergabe und Discovery.
- Tauri-Commands für sämtliche Backend-Aufrufe: stärkere Kopplung an Rust und schlechtere isolierte Testbarkeit.
- WebSocket von Beginn an: für vollständige Textantworten unnötige Komplexität.


```
`06-native-gemma-audio.md`:

```md
# ADR 06: Nativer Audioinput mit Gemma 4

- Status: Angenommen als Ziel; technische Machbarkeit durch Spike zu bestätigen
- Datum: 2026-08-26

## Kontext

Avalo soll Sprache möglichst direkt durch Gemma 4 verarbeiten. Ein separates Speech-to-Text-Modell würde zusätzliche Latenz, Ressourcen und eine weitere Fehlerquelle einführen.

## Entscheidung

- Gemma 4 erhält Audio direkt über die ausgewählte lokale Runtime.
- Ein separates STT-System gehört zunächst nicht zur Produktpipeline.
- Der erste Audioschritt verwendet explizites Push-to-Talk.
- Eine Aufnahme ist auf 30 Sekunden begrenzt.
- Längere Aufnahmen werden nicht automatisch in verdeckte Teilstücke zerlegt.
- Deutsch ist die initial vorgegebene Sprache.
- Eine sichtbare Restzeit-/Fortschrittsanzeige ist vorgesehen, aber nicht Teil des ersten Audio-Schnitts.
- Ob Nutzeraudio zusätzlich als Transkript erscheint, bleibt offen, bis der Spike die Ausgabe von Gemma 4 untersucht hat.

## Konsequenzen

- Bedeutung und Tonmerkmale können gemeinsam verarbeitet werden, sofern Runtime und Quantisierung die Modellfähigkeit erhalten.
- Audioformat, Resampling und Monokonvertierung werden an Gemmas Eingabeanforderungen angepasst.
- Ohne separates STT existiert kein garantiertes wörtliches Transkript.
- Fällt die native Verarbeitung qualitativ oder technisch durch, wird diese Entscheidung neu bewertet.

## Grenze

Google dokumentiert für Gemma 4 maximal 30 Sekunden Audio pro Eingabe sowie 16 kHz, Mono und normalisierte 32-Bit-Fließkomma-Samples als Modellformat.

## Quelle

- [Google: Gemma 4 Audio Understanding](https://ai.google.dev/gemma/docs/capabilities/audio)


```
`07-tts-output.md`:

```md
# ADR 07: Lokale Sprachausgabe mit Chatterbox Multilingual

- Status: Vorgeschlagen; durch TTS-Spike zu bestätigen
- Priorität: Nach Textchat und nativem Audioinput
- Datum: 2026-08-26

## Kontext

Avalo benötigt später eine lokale, möglichst natürliche deutsche Stimme. Niedrigste Latenz ist weniger wichtig als Natürlichkeit. Eine Stimme soll grundsätzlich auswählbar sein; eine Laufzeit-Stimmenverwaltung ist zunächst nicht erforderlich.

## Entscheidung

- Bevorzugter TTS-Kandidat ist **Chatterbox Multilingual V3** von Resemble AI.
- TTS wird über einen austauschbaren Python-Adapter angebunden.
- Die erste Konfiguration verwendet genau eine ausgewählte deutsche Referenzstimme.
- Referenzaudio darf nur mit den erforderlichen Nutzungsrechten verwendet werden.
- Ausgabe bleibt lokal; es wird kein Cloud-TTS-Dienst benötigt.
- Ein Spike entscheidet vor der Integration über Qualität, Latenz und Ressourcenstrategie.

## Begründung

- Deutsch wird offiziell unterstützt.
- Das Modell zielt auf natürliche, dialogartige und expressive Sprache.
- Lokale Python-Nutzung und Zero-Shot-Stimmkonditionierung werden unterstützt.
- Code und Modelle stehen laut Anbieter unter MIT-Lizenz.
- Die 500M-Architektur ist wesentlich kleiner als Avalos LLM, konkurriert aber dennoch um GPU-Speicher.

## Erfolgskriterien des Spikes

- natürliche deutsche Aussprache und Satzmelodie anhand festgelegter Hörbeispiele;
- konsistente Stimme über mehrere Antworten;
- keine auffälligen Auslassungen, Wiederholungen oder Halluzinationen;
- gemessene Start- und Synthesezeit;
- dokumentierter RAM-/VRAM-Bedarf im Zusammenspiel mit der LLM-Runtime;
- geprüfte Lizenz der konkreten Modellversion und Rechte am Referenzaudio.

## Konsequenzen

- LLM und TTS müssen auf 8 GB VRAM voraussichtlich koordiniert oder teilweise über CPU/RAM betrieben werden; die genaue Strategie bleibt Ergebnis des Spikes.
- Spätere Stimmwahl verändert nur Konfiguration und Referenzaudio, nicht die Gesprächslogik.
- Chatterbox versieht erzeugte Audiodaten mit einem nicht hörbaren Herkunftswasserzeichen.

## Alternativen

- Piper: deutlich ressourcenschonender und als Fallback geeignet, aber nicht erste Wahl bei priorisierter Natürlichkeit.
- XTTS-v2: unterstützt Deutsch, besitzt jedoch eine restriktivere Modelllizenz.

## Quellen

- [Chatterbox GitHub-Repository](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Multilingual](https://www.resemble.ai/learn/models/chatterbox-multilingual)
- [Piper](https://github.com/cdwiegand/piper-tts)
- [XTTS-v2 Model Card](https://huggingface.co/coqui/XTTS-v2)

```
`08-incremental-repo-map-as-ai-working-index.md`:

```md
# ADR 08: Incremental RepoMap as AI Working Index

## Status

Accepted

## Context

The Avalo development workflow deliberately separates refinement, implementation planning,
code modification, execution, and review.

For small and medium-sized work packages, Frieda may prepare implementation changes without
having persistent access to the complete repository.

Repeatedly scanning or transferring the complete repository would create unnecessary context
and token overhead. At the same time, implementation planning requires enough repository
knowledge to identify relevant files and dependencies before requesting their actual contents.

A persistent RepoMap is therefore maintained as a compact working index of the repository.

The RepoMap is explicitly **not repository documentation and not a representation of the full
repository**.

Its sole consumer is Frieda. Its purpose is to provide enough structural and semantic context
for Frieda to:

- identify likely files affected by a change,
- understand relevant dependencies and relationships,
- create an initial implementation plan,
- request the specific source files required for implementation,
- recognize when the available repository context is insufficient.

The RepoMap may contain files, classes, functions, methods, signatures, dependencies,
responsibilities, behavioral notes, or other information useful for these purposes.

Its level of detail is intentionally adaptive:

> As little information as possible, as much as Frieda needs for reliable repository navigation
> and implementation planning.

## Decision

Avalo maintains a human-readable RepoMap as a persistent AI working index.

The concrete serialization format (Markdown, YAML, JSON, or similar) is chosen based on what
works best for Frieda. Human readability is required primarily for transparency and operational
recoverability, not because humans are intended consumers of its contents.

The RepoMap SHALL remain substantially smaller and more abstract than the repository itself.

It SHALL NOT attempt to contain complete implementation details or become a parallel
documentation model of the source code.

### Human-in-the-loop

Human-in-the-loop validation of RepoMap contents is explicitly **not required**.

The RepoMap is written by Frieda for Frieda and is not intended to provide reliable
documentation for Flo or other human developers.

Consequently:

- Flo is not responsible for reviewing its completeness or semantic quality.
- Flo is not responsible for maintaining its internal structure.
- Entries do not need to be optimized for human comprehension.
- Frieda is responsible for determining which information she requires and for recognizing
  when the RepoMap is insufficient or stale.

Human readability remains useful for debugging the workflow, manual recovery, and avoiding
opaque or proprietary state.

### Incremental maintenance

The RepoMap is updated only after an implementation has reached its final accepted state.

The update MUST be derived from the final accepted diff or equivalent final code state, not
from the original implementation plan or intermediate patches.

As part of the final review, Frieda produces the corresponding RepoMap change together with,
or immediately after, approval of the implementation.

This allows the RepoMap to evolve incrementally without requiring a complete repository scan
after every change.

### Re-analysis

Incremental maintenance is not assumed to remain correct indefinitely.

A broader repository re-analysis SHOULD be performed periodically and SHOULD also be triggered
when there is evidence that the RepoMap has become unreliable.

Possible triggers include:

- significant refactoring,
- new modules or architectural layers,
- substantial dependency restructuring,
- repeated incorrect file selection,
- missing dependencies discovered during implementation,
- noticeable divergence between RepoMap assumptions and actual source code,
- several accumulated implementation iterations where a refresh is considered prudent.

The re-analysis reconciles the RepoMap with the actual repository.

## Workflow

For suitable work packages, the intended workflow is:

1. Flo and Frieda refine the change.
2. Frieda uses the RepoMap to create an initial implementation plan.
3. Frieda explicitly requests the source files required for implementation.
4. Flo provides the requested current source snapshot.
5. Frieda creates deterministic replace/diff operations.
6. Flo applies the changes and executes the requested tests and verification.
7. Frieda reviews the resulting diff and test results.
8. The review/fix loop continues until the change is accepted.
9. Frieda derives and provides the final incremental RepoMap update from the accepted change.

The RepoMap therefore supports repository discovery but never replaces inspection of the actual
source files involved in a change.

## Escalation to repository-aware coding agents

Not every work package is suitable for this workflow.

During refinement, a work package may deliberately be escalated to Codex or another
repository-aware coding agent when broad repository exploration, extensive cross-cutting
changes, interactive debugging, or greater implementation autonomy is expected to provide
material benefit.

The objective is not to avoid frontier coding-agent usage entirely. The objective is to use
its more constrained token budget selectively where repository integration and agentic
capabilities provide meaningful leverage.

Regardless of the implementation path, the final implementation review remains with Frieda.

After acceptance, Frieda also determines the required RepoMap update.

## Consequences

### Positive

- Full repository scans are avoided for routine changes.
- Context and token consumption are concentrated on relevant source files.
- Repository knowledge persists across individual feature conversations and implementation
  iterations.
- Frieda can perform initial impact analysis before requesting source code.
- The workflow remains usable without permanent repository access.
- RepoMap maintenance naturally follows accepted repository changes.
- Expensive repository-aware coding agents can be reserved for work packages where their
  capabilities provide meaningful benefit.

### Negative / Risks

- The RepoMap can become stale or incomplete.
- Incorrect RepoMap information can cause incorrect file selection or incomplete impact
  analysis.
- Incremental updates can accumulate errors over time.
- The appropriate level of abstraction cannot be fully specified upfront and must be learned
  empirically.
- Frieda must recognize uncertainty rather than treating the RepoMap as authoritative.

These risks are accepted because the actual source code remains the authoritative source for
implementation and final review, and periodic or trigger-based re-analysis provides a recovery
mechanism.

## Principle

> The RepoMap is not a map for humans to understand Avalo.
> It is Frieda's compact working memory for knowing where to look next.

If it fails at that job, Frieda owns the virtual nose-pulling.
```
`09-source-patching-via-prompt2code.md`:

```md
# ADR 09: Deterministic Source Patching via prompt2code

**Status:** Accepted

## Context

Small and well-localized Avalo changes are planned and reviewed by Frieda without requiring a repository-aware coding agent.

To apply such changes safely, Avalo uses `prompt2code.py` (P2C) as a deliberately simple patch executor.

P2C contains no code intelligence. Frieda is responsible for understanding the code and generating the patch; P2C is responsible only for deterministic validation and application.

## Decision

P2C consumes a YAML patch file and applies ordered changes relative to a target repository directory.

Supported operations:

- `string-replace` — replace one exact string
- `string-remove` — remove one exact string
- `create` — create a new file
- `delete` — delete an existing file

For `string-replace` and `string-remove`, the `old` text MUST occur **exactly once**. Zero or multiple matches abort the complete patch.

Changes are simulated sequentially in memory. Later changes therefore see the result of earlier changes.

Only after **all changes in all files have validated successfully** are filesystem changes written.

P2C intentionally provides:

- no fuzzy matching
- no automatic code interpretation
- no intelligent conflict resolution
- no regex patching initially
- no partial writes after semantic validation failure

The source code remains authoritative.

## Workflow

1. Flo and Frieda refine the change.
2. Frieda identifies the required source files.
3. Flo provides their current content.
4. Frieda generates the YAML patch.
5. Flo applies it with P2C.
6. Flo runs the required tests and verification.
7. Frieda reviews the resulting `git diff` and test results.
8. If necessary, repeat with another incremental patch.

Complex or poorly localized changes may instead be escalated to a repository-aware coding agent.

## How-To

Apply a patch:

    python prompt2code.py \
      --input-script patch.yaml \
      --target-dir ~/dev/avalo

Typical patch:

    files:
      - path: backend/app/example.py
        changes:
          - mode: string-replace
            old: |2-
              return "old"
            new: |2-
              return "new"

          - mode: string-remove
            old: |2-
              # obsolete comment

      - path: backend/app/new_file.py
        changes:
          - mode: create
            content: |2
              def hello():
                  return "hello"

### Important

- Always generate patches against the **current source state**.
- Keep patches small and purpose-specific.
- Multiple changes to one file belong in one file entry and execute top-to-bottom.
- Prefer `|2-` for exact snippets where a trailing newline must not be part of the match.
- Use `|2` for complete file content when the final newline should be preserved.
- Never weaken an exact-match failure just to make a patch apply. Re-read the current source and regenerate the patch.
- After every patch, run the relevant tests and inspect `git diff`.
- A successfully applied patch is **not** evidence of correct behavior; tests and Frieda's final review remain required.

## Consequences

P2C trades coding-agent flexibility for predictability and low coordination overhead.

This works well for bounded changes whose affected code can be identified beforehand. It is intentionally unsuitable for changes requiring repository exploration, broad refactoring, or iterative debugging.

> Frieda decides what to change. P2C only proves that the requested textual transformation can be applied exactly.

```
```
`scripts/code2prompt-adrs.sh`:

```sh
code2prompt ~/dev/avalo/docs/adrs \
  -O ./code2prompt-adrs.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**"

#code2prompt ./avalo/ -O ./avalo.md -F markdown


```
`scripts/code2prompt-code.sh`:

```sh
#!/bin/bash

code2prompt ~/dev/avalo/ \
  -O ./code2prompt-code.md \
  -F markdown \
  --exclude="**/node_modules/**" \
  --exclude="**/__pycache__/**" \
  --exclude="docs/**"



```
`scripts/frieda-dump.md`:

```md
Project Path: avalo

Source Tree:

```txt
avalo
├── backend
│   └── app
│       └── config.py
├── frontend
│   ├── package.json
│   └── src
│       ├── App.vue
│       └── main.ts
└── scripts
    └── start-backend.sh

```

`backend/app/config.py`:

```py
"""Central backend configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Static settings for the initial local development setup."""

    app_name: str = "Avalo Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8095
    frontend_dev_origin: str = "http://127.0.0.1:5173"
    default_language: str = "de"
    audio_max_seconds: int = 30
    ollama_host: str = "127.0.0.1:11434"
    ollama_model: str = "gemma4:e4b-it-q4_K_M"


settings = Settings()

```
`frontend/package.json`:

```json
{
  "name": "avalo-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vue-tsc --noEmit -p tsconfig.app.json && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "vue": "^3.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.0",
    "@types/node": "^22.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^26.0.0",
    "typescript": "^5.8.0",
    "vite": "^6.0.0",
    "vitest": "^3.2.0",
    "vue-tsc": "^3.0.0"
  }
}

```
`frontend/src/App.vue`:

```vue
<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getBackendHealth } from "./services/backend";

const backendStatus = ref("Prüfe Backend …");

onMounted(async () => {
  try {
    const health = await getBackendHealth();
    backendStatus.value = `${health.service}: ${health.status}`;
  } catch {
    backendStatus.value = "Backend nicht erreichbar";
  }
});
</script>

<template>
  <main class="app-shell">
    <h1>Avalo</h1>
    <p>Lokaler Companion – Grundgerüst</p>
    <p class="status" data-testid="backend-status">{{ backendStatus }}</p>
  </main>
</template>


```
`frontend/src/main.ts`:

```ts
import { createApp } from "vue";

import App from "./App.vue";
import "./styles.css";

createApp(App).mount("#app");


```
`scripts/start-backend.sh`:

```sh
#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${project_root}/.venv/bin/python" -m uvicorn avalo_backend.main:app \
  --app-dir "${project_root}/backend" \
  --host 127.0.0.1 \
  --port 8095 \
  --reload


```
```
`scripts/frieda-dump.sh`:

```sh
#!/bin/bash

# read -p "Paste file list: " file_list
echo "Paste file list (complete with ENTER CTRL+d):"

file_list=$(cat)

file_list=$(echo "$file_list" | paste -sd, -)
#echo $file_list

code2prompt ~/dev/avalo \
  --include="$file_list" \
  -F markdown \
  --output-file=./frieda-dump.md

```
`scripts/prompt2code-patch.yaml`:

```yaml
files:
  - path: backend/app/runtime/ollama.py
    changes:
      - mode: string-replace
        old: |2-
          from pathlib import Path
          import base64
          import httpx
          from app.config import settings
          from app.runtime.base import ModelRuntime
        new: |2-
          """Ollama runtime adapter."""

          import base64
          from pathlib import Path

          import httpx

          from app.config import settings
          from app.runtime.base import ModelRuntime

      - mode: string-replace
        old: |2-
                          data = response.json()
                          choices = data.get("choices")
                          if choices and len(choices) > 0:
                              message = choices[0].get("message")
                              if message:
                                  content = message.get("content")
                                  if content:
                                      text = content
                          else:
                              raise ValueError("Invalid Ollama response")

                          if not isinstance(text, str) or not text.strip():
                              raise ValueError("Invalid Ollama response")
        new: |2-
                          data = response.json()
                          text = data.get("response")

                          if not isinstance(text, str) or not text.strip():
                              raise ValueError("Invalid Ollama response")

      - mode: string-replace
        old: |2-
                          response = await client.post(
                              f"http://{settings.ollama_host}/v1/chat/completions",
                              json={
                                  "model": settings.ollama_model,
                                  "messages": [
                                      {
                                          "role": "user",
                                          "content": [
                                              {
                                                  "type": "text",
                                                  "text": "Transcribe and respond in German:",
                                              },
                                              {
                                                  "type": "input_audio",
                                                  "input_audio": {
                                                      "data": audio_base64,
                                                      "format": "wav",
                                                  },
                                              },
                                          ],
                                      },
                                  ],
                              },
                          )
                          response.raise_for_status()

                          data = response.json()
                          text = data.get("response")

                          if not isinstance(text, str) or not text.strip():
                              raise ValueError("Invalid Ollama response")

                          return text
        new: |2-
                          response = await client.post(
                              f"http://{settings.ollama_host}/v1/chat/completions",
                              json={
                                  "model": settings.ollama_model,
                                  "messages": [
                                      {
                                          "role": "user",
                                          "content": [
                                              {
                                                  "type": "text",
                                                  "text": "Transcribe and respond in German:",
                                              },
                                              {
                                                  "type": "input_audio",
                                                  "input_audio": {
                                                      "data": audio_base64,
                                                      "format": "wav",
                                                  },
                                              },
                                          ],
                                      },
                                  ],
                              },
                          )
                          response.raise_for_status()

                          data = response.json()
                          choices = data.get("choices")

                          if not isinstance(choices, list) or not choices:
                              raise ValueError("Invalid Ollama response")

                          message = choices[0].get("message")
                          if not isinstance(message, dict):
                              raise ValueError("Invalid Ollama response")

                          text = message.get("content")
                          if not isinstance(text, str) or not text.strip():
                              raise ValueError("Invalid Ollama response")

                          return text
  - path: backend/app/config.py
    changes:
      - mode: string-replace
        old: |2-
          from dataclasses import dataclass

          @dataclass(frozen=True, slots=True)
        new: |2-
          """Central backend configuration."""

          from dataclasses import dataclass


          @dataclass(frozen=True, slots=True)

      - mode: string-replace
        old: |2-
              ollama_host: str = "127.0.0.1:11434"  # Default Ollama host and port
              ollama_model: str = "gemma4:e4b-it-q4_K_M"  # Default Ollama model
        new: |2-
              ollama_host: str = "127.0.0.1:11434"
              ollama_model: str = "gemma4:e4b-it-q4_K_M"

  - path: tests/backend/test_ollama_runtime.py
    changes:
      - mode: string-replace
        old: |2-
          """Tests for the Ollama runtime adapter."""

          import pytest
          from httpx import ConnectError
          from pytest_httpx import HTTPXMock
          from app.config import settings
          from app.runtime.ollama import OllamaRuntime
          import base64
          from pathlib import Path
        new: |2-
          """Tests for the Ollama runtime adapter."""

          import base64
          from pathlib import Path

          import pytest
          from httpx import ConnectError
          from pytest_httpx import HTTPXMock

          from app.config import settings
          from app.runtime.ollama import OllamaRuntime

      - mode: string-replace
        old: |2-
              httpx_mock.add_response(
                  method="POST",
                  url=f"http://{settings.ollama_host}/api/generate",
                  json={
                      "choices": [
                          {
                              "message": {
                                  "content": "",
                              },
                          },
                      ],
                  },
              )
        new: |2-
              httpx_mock.add_response(
                  method="POST",
                  url=f"http://{settings.ollama_host}/api/generate",
                  json={"response": ""},
              )

      - mode: string-replace
        old: |2-
          @pytest.mark.asyncio
          async def test_generate_from_audio_raises_runtime_error_for_invalid_response(
              httpx_mock: HTTPXMock,
          ) -> None:
              with open("tests/data/german-transcription.wav", "rb") as f:
                  audio_data = f.read()
              audio_base64 = base64.b64encode(audio_data).decode("utf-8")

              httpx_mock.add_response(
        new: |2-
          @pytest.mark.asyncio
          async def test_generate_from_audio_raises_runtime_error_for_invalid_response(
              httpx_mock: HTTPXMock,
          ) -> None:
              httpx_mock.add_response(
      - mode: string-replace
        old: |2-
              httpx_mock.add_response(
                  method="POST",
                  url=f"http://{settings.ollama_host}/v1/chat/completions",
                  json={"response": ""},
              )
        new: |2-
              httpx_mock.add_response(
                  method="POST",
                  url=f"http://{settings.ollama_host}/v1/chat/completions",
                  json={
                      "choices": [
                          {
                              "message": {
                                  "content": "",
                              },
                          },
                      ],
                  },
              )

```
`scripts/prompt2code.sh`:

```sh
cd ~/dev/avalo

source .venv/bin/activate

cd ~/dev

python ~/scripts/dev/prompt2code.py \
  --input-script ~/dev/prompt2code-patch.yaml \
  --target-dir ~/dev/avalo


```
`scripts/start-backend.sh`:

```sh
#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${project_root}/.venv/bin/python" -m uvicorn avalo_backend.main:app \
  --app-dir "${project_root}/backend" \
  --host 127.0.0.1 \
  --port 8095 \
  --reload


```
`scripts/start-frontend.sh`:

```sh
#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_root}/frontend"
exec npm run dev


```
`tests/backend/test_chat_contract.py`:

```py
import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def post_chat(message: str):
    async def request_chat():
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/chat", json={"message": message})

    return asyncio.run(request_chat())


def test_chat_endpoint_explicitly_reports_stub() -> None:
    response = post_chat("Hallo")

    assert response.status_code == 501
    assert response.json() == {
        "detail": "Text chat is not implemented yet.",
    }


def test_chat_rejects_empty_message() -> None:
    response = post_chat("")

    assert response.status_code == 422

```
`tests/backend/test_config.py`:

```py
from app.config import settings


def test_local_api_address_is_fixed() -> None:
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8095


def test_gemma_audio_limit_is_recorded() -> None:
    assert settings.audio_max_seconds == 30


def test_ollama_runtime_settings_are_recorded() -> None:
    assert settings.ollama_host == "127.0.0.1:11434"
    assert settings.ollama_model == "gemma4:e4b-it-q4_K_M"

```
`tests/backend/test_health.py`:

```py
import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


def test_health_reports_ready_backend() -> None:
    async def request_health():
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Avalo Backend",
    }

```
`tests/backend/test_ollama_runtime.py`:

```py
"""Tests for the Ollama runtime adapter."""

import base64
from pathlib import Path

import pytest
from httpx import ConnectError
from pytest_httpx import HTTPXMock

from app.config import settings
from app.runtime.ollama import OllamaRuntime

@pytest.mark.asyncio
async def test_health_returns_true_when_model_is_available(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        match_json={"model": settings.ollama_model},
        url=f"http://{settings.ollama_host}/api/show",
        json={"details": {"format": "gguf"}},
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is True


@pytest.mark.asyncio
async def test_health_returns_false_when_model_is_missing(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/show",
        match_json={"model": settings.ollama_model},
        status_code=404,
        json={"error": "model not found"},
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is False


@pytest.mark.asyncio
async def test_health_returns_false_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/show",
    )

    runtime = OllamaRuntime()

    assert await runtime.health() is False


@pytest.mark.asyncio
async def test_generate_text_returns_response(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        match_json={
            "model": settings.ollama_model,
            "prompt": "Hallo",
            "stream": False,
        },
        json={"response": "Hallo Flo"},
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_text("Hallo")

    assert result == "Hallo Flo"


@pytest.mark.asyncio
async def test_generate_text_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_text("Hallo")


@pytest.mark.asyncio
async def test_generate_text_raises_runtime_error_for_invalid_response(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/api/generate",
        json={"response": ""},
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_text("Hallo")


@pytest.mark.asyncio
async def test_generate_from_audio_returns_response(
    httpx_mock: HTTPXMock,
) -> None:
    with open("tests/data/german-transcription.wav", "rb") as f:
        audio_data = f.read()
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        match_json={
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe and respond in German:",
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
        },
        json={
            "choices": [
                {
                    "message": {
                        "content": "Die Hauptstadt von Deutschland ist Berlin.",
                    },
                },
            ],
        },
    )

    runtime = OllamaRuntime()

    result = await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))

    assert result == "Die Hauptstadt von Deutschland ist Berlin."


@pytest.mark.asyncio
async def test_generate_from_audio_raises_runtime_error_when_ollama_is_unreachable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_exception(
        ConnectError("connection failed"),
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))


@pytest.mark.asyncio
async def test_generate_from_audio_raises_runtime_error_for_invalid_response(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"http://{settings.ollama_host}/v1/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "content": "",
                    },
                },
            ],
        },
    )

    runtime = OllamaRuntime()

    with pytest.raises(RuntimeError, match="Ollama error"):
        await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))

```
`tests/backend/test_runtime_blueprint.py`:

```py
import pytest

from app.runtime.llama_cpp import LlamaCppRuntime


@pytest.mark.anyio
async def test_llama_cpp_runtime_blueprint_is_not_implemented():
    runtime = LlamaCppRuntime()

    with pytest.raises(NotImplementedError):
        await runtime.generate_text("Hallo")

```
`tests/backend/test_tts_blueprint.py`:

```py
import pytest

from app.tts.chatterbox import ChatterboxTextToSpeech


@pytest.mark.anyio
async def test_chatterbox_tts_blueprint_is_not_implemented():
    tts = ChatterboxTextToSpeech()

    with pytest.raises(NotImplementedError):
        await tts.synthesize("Hallo")

```
`tests/frontend/App.spec.ts`:

```ts
import { flushPromises, mount } from "@vue/test-utils";

import App from "../../frontend/src/App.vue";

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the backend health status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", service: "Avalo Backend" }),
      }),
    );

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="backend-status"]').text()).toBe(
      "Avalo Backend: ok",
    );
  });

  it.todo("sends a text message and renders the complete response");
  it.todo("records and submits a push-to-talk audio clip");
  it.todo("plays synthesized speech for an assistant response");
});

```
`tests/integration/test_ollama_integration.py`:

```py
import pytest
from app.runtime.ollama import OllamaRuntime
from pathlib import Path

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_runtime_integration():
    runtime = OllamaRuntime()

    # Check health
    assert await runtime.health(), "Ollama is not reachable or the model is not available."

    # Generate text
    prompt = "Was ist die Hauptstadt von Deutschland?"
    response = await runtime.generate_text(prompt)
    assert response.strip(), "The response from Ollama is empty or only contains whitespace."

    # Generate from audio
    response = await runtime.generate_from_audio(Path("tests/data/german-transcription.wav"))
    assert "diagnostizierte" in response, "The response from Ollama does not contain the expected transcript content."

```
`tests/integration/test_text_chat_blueprint.py`:

```py
import pytest


@pytest.mark.skip(reason="Requires the local Gemma runtime selected by the spike.")
def test_text_chat_from_http_request_to_model_response() -> None:
    pass


```