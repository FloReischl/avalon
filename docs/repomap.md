# Avalo RepoMap

Arbeitsindex für Frieda: Impact-Analyse, Implementierungsplanung, Abhängigkeitsnavigation und Auswahl der vor einer Änderung zu prüfenden Dateien. Keine autoritative Dokumentation: Vor jeder Umsetzung Quellcode prüfen. Nur aus akzeptiertem Endstand inkrementell aktualisieren; bei strukturellem Drift Repository neu analysieren.

## System

- **Ziel:** lokaler Desktop-Companion mit Text-Chat, nativem Gemma-Audioeingang und lokalem TTS.
- **Desktop:** Tauri; transparente Avatar-Shell plus normale Chat-Window; Vue in Tauri-Webviews, Python-Backend als eigener, von Tauri gestarteter/überwachter/beendeter Prozess.
- **Frontend:** Vue 3, TypeScript, Vite in `frontend`; Roots: Avatar `frontend/src/App.vue`, Chat `frontend/src/ChatWindow.vue`; HTTP zum Backend.
- **Backend:** Python, FastAPI, MCP Python SDK v2 in `backend/app`; API, MCP, Application, SQLite-Persistenz, Runtime-Adapter, Audio, TTS, Konfiguration.
- **Transport:** loopback-only `127.0.0.1:8095`, JSON, SSE mit JSON-`data`, keine Authentisierung; API `/api/v1`, MCP `/mcp`.
- **MCP-Fähigkeit:** `music.play_tracks`.

### Desktop- und Fensterverhalten

- `main`: Avatar, always-on-top, transparent, ohne Dekoration; Schließen beendet die App.
- `chat`: initial verborgen, resizable, mit Dekoration; Schließen versteckt Webview-State nur.
- Avatar-Doppelklick zeigt/fokussiert vorhandenes Chatfenster. Geometrie-Persistenz nicht implementiert.
- Chat-Laufzeitstatus geht über Tauri-Events an Avatar-Webview.
- X11: native SHAPE-Inputregionen aus PNG-Alpha; beide Fenster erhalten das Avalo-Icon. Cinnamon/X11-Identität über Desktop-Entry mit `StartupWMClass=Avalo`.

## Gespräche und Kontext

- SQLite `~/.avalo/avalo.sqlite`, Alembic, SSE-Antworten.
- Start immer mit transientem New Chat; Persistenz beim ersten Senden. Persistierte Chats listen/öffnen vollständige Historie.
- Aktiver Kontext: Avatar-Systeminstruktionen + komprimierte Historie + Nachrichten nach `compressed_through_seq`; Audio mit persistierter `chat_id` rekonstruiert denselben Kontext serverseitig.
- Nach vollständigen Text- und Audioturns best-effort asynchrone Komprimierung. Terminales `chat_context_compression_failed` blockiert Text/Audioturns mit HTTP 409.
- Persona/Instruktionen des effektiven Standardavatars sind eine Systemmessage für Assistenten-Text und -Audio, nie für Transkription oder automatische Titel.
- Assistant-Text nur komplett erfolgreich persistieren; Abbruch/Fehler-Teilausgabe nie. Nach exakt zwei kompletten Textrunden ein Titelversuch; manuelle Titel unterdrücken ihn dauerhaft.
- Chats: Pin, Umbenennen, physisch löschen, Markdown exportieren. Reihenfolge im Backend nach Aktivität; UI separiert angeheftete Chats. Löschen des sichtbaren Chats => leeres New Chat.
- Audio-UI: Placeholder `🎤 Sprachnachricht`; erfolgreiche Transkription ersetzt ihn, wird normale User-Nachricht und Kontext; Fehler/Abbruch behält Placeholder. Assistant und Transkript streamen/persistieren unabhängig. WAV löschen erst nach Abschluss/Abbruch beider Verbraucher.
- Mehrere persistierte Chats können parallele Textstreams haben; Stop betrifft nur den sichtbaren laufenden Chat.

## Kernflüsse

### Backendstart und Health

- Entry `backend/app/main.py:create_app`: User-Konfiguration laden/validieren, dann Alembic bis Head; Fehler lassen Start fehlschlagen und Traceback auf stderr. CORS für Browser `GET, POST, PATCH, DELETE`; Router installieren.
- `GET /health` → `backend/app/api/routes/health.py:health`, Schema `HealthResponse`; nur HTTP-Readiness.

### Text-Chat

- `POST /api/v1/chat` → `routes/chat.py:create_chat_response` → `ChatService` → `ModelRuntime.generate_text_stream`.
- Request `{"message":"<prompt>"}` oder `{"chat_id":<id>,"message":"<prompt>"}`; unbekannte Chat-ID vor `StreamingResponse` mit 404 ablehnen.
- SSE: `chat {"id":"<chat-id>"}`, `chunk {"text":"<chunk>"}`, `done {}`, `error {}`. Reihenfolge: `chat`, 0+ `chunk`, `done`; `done` vor optionaler Titel-Finalisierung, EOF erst danach. Laufzeitfehler: `error`, kein `done`; technische Details nicht öffentlich. Cancellation propagiert ohne `error`.

### Audio

- Capture Python-Backend via `PipeWireRecorder`/`pw-record`; PTT und Dialog teilen Recorder und laufen nicht parallel.
- PTT: Chatfenster gedrückt → `POST /audio/recording/start` → release `POST /audio/recording/stop` mit Client-Kontext/optional `chat_id`; 30-Sekunden-Limit verwirft Fragment.
- Dialog: Avatar Call besitzt den kontinuierlichen Modus; Chat Call delegiert mit selektierter `chat_id`. `POST /audio/dialog/turn`; wartet vor Sprache unbegrenzt, RMS startet Aufnahme, konfigurierter Stillezeitraum oder 30 s ab Sprechbeginn beendet. Danach SSE `processing` vor Modellverbrauchern.
- Avatar-Call ohne Chat bindet beim ersten Sprachturn einen neu erstellten Chat; Bindung bleibt bis Call-Ende. Nach Read-Aloud startet Listener erneut, Ende nur explizit am Avatar.
- Statisches `greeting_audio`: nach Runtime-Readiness einmal je Call, nie Historie/Persistenz/LLM-Kontext; Fehler nur loggen.
- Eine WAV für Assistant-Generierung (Kontext) und Transkription (Audio allein); beide parallel, unabhängig. Während Modell/TTS keine Audio-Barge-in. Stop von Antwort-Audio bricht Modell nicht ab; Stop vor TTS überspringt TTS.
- Call-State umfasst Aufnahme, Modellverarbeitung und Playback als aktiven Turn. Textantworten im gebundenen Call-Chat werden für Avatar-TTS eingereiht.
- Vorgaben: max. 30 s, `audio_wait_exceed_seconds`, RMS `0.015`, 16 kHz mono, initial `de`, kein separates STT. MediaRecorder wurde nach WebKitGTK-Nullchunks verworfen.

### TTS

- Contract `backend/app/tts/base.py:TextToSpeech`; Factory `create_tts_engine`; Lifecycle `TtsService`.
- Endpoints: `POST /api/v1/tts`, `POST /api/v1/tts/playback-ended`; vollständiges WAV, eine Synthese gleichzeitig, keine Queue. Playback-ID steuert Idle-Lifecycle, stale ended ignorieren, Unload nach 300 s ohne Synthese/aktives Playback.
- Frontend wandelt fertiges Markdown in Plaintext.
- Kokoro (Default): `KokoroTextToSpeech`, Kikiri German Victoria/Kokoro-82M, 24 kHz, CUDA bevorzugt dann CPU; lokale Artefakte, kein Runtime-Download.
- Chatterbox: `ChatterboxTextToSpeech`, Multilingual V2, 4-bit bitsandbytes; satzorientierte Chunks. V3 gewann Qualitätsvergleich, verfügbarer Adapter bleibt V2.
- Gemma bleibt GPU-resident; Kokoro ist wegen Ressourcen/Interaktion Default, Chatterbox bei gerechtfertigtem Qualitätsgewinn.

### Musik

- `music.play_tracks` (`backend/app/mcp/music.py:register_music_tools`) über MCP Streamable HTTP `/mcp`.
- `track_ids: list[int]` wird vollständig geloggt; `MusicService` löst `tracks.id → file_path` aus externer Musik-SQLite auf. Reihenfolge/Duplikate erhalten, unbekannte IDs auslassen; Playlist `/tmp/avalo_music.m3u`, Celluloid starten.

## Module

### Backend: Komposition, API und Konfiguration

- `backend/app/config.py`: eingefrorene `LlmConfig(key, model)`, `Settings`-Singleton. Relevante Felder: Netz/DB/CORS/Sprache, Audio-Limits, Kontextkompressions-Parameter, Ollama, `llm_models`, TTS-Engine/Device/Revision/Idle. Für Start, Health, Runtime, Audio, TTS.
- `backend/app/state.py`: prozesslokaler Avatar, aktives LLM, Inferenzzähler, Switch-Guard; Standard-LLM beim Start, nicht persistent; Modellwechsel während Inferenz blockieren.
- `backend/app/commands`: async `/ <group> <command> [payload]`; `/avatar set <key>`, `/llm set <key>`. LLM: unbekannt/nicht verfügbar ablehnen, gleiches Modell No-op, altes unloaden, Ziel aufwärmen, erst dann publizieren; bei Warm-up-Fehler altes wiederherstellen, bei Fehlschlag terminieren.
- `backend/app/main.py`: `create_app() -> FastAPI`, `StderrExceptionMiddleware`, `app`; validiert Konfiguration, initialisiert State, verlangt Standard-LLM in Ollama, warnt bei anderen, Alembic + MCP-Session-Lifespan, mountet `/mcp`.
- `backend/app/api/router.py`: Health root; UI, Assets, Runtime, Chat, Chatmanagement, Audio/Call, TTS unter `/api/v1`.
- `backend/app/api/schemas.py`: öffentliche Verträge. `ChatRequest(chat_id?: positive int, message: non-empty)`, `ConversationMessage(role user|assistant, content)`, `AudioResponseRequest(messages, chat_id?)`, `HealthResponse`, Chat summary/detail (inkl. `pinned`, `compression_error_code`), Rename (max. 200), Pin, TTS, Playback-ended, UI-Konfiguration/Avatar/Sprite-Regionen.
- `routes/health.py`: `health() -> HealthResponse`.
- `routes/runtime.py`: `POST /api/v1/runtime/warm-up`, stateless best-effort, Inhalt verwerfen.
- `routes/chat.py`: request-scoped ChatService mit Ollama/Persistenz, `format_sse_event`, Eventtypen `chat/chunk/done/error`; Cancellation unverändert.
- `routes/chats.py`: `GET /chats`, `GET /chats/{id}`, `PATCH /chats/{id}`, `PATCH /chats/{id}/pinned`, `DELETE /chats/{id}`.
- `routes/audio.py`: Call status/start/end/turn-complete/speech-consume; recording start/abort/stop; dialog turn. Nutzt `AudioChatService`, `AudioCallState`, `ChatRepository`.
- `routes/tts.py`: Synthese und Playback-Lifecycle; `TtsService`, Factory.
- `routes/ui.py`: `GET /ui/config`, nur frontend-sichere effektive Standardavatar-Daten; fertige absolute Asset-URLs mit Prozess-Cache-Token, keine Persona/Instruktionen/Pfade/TTS.
- `routes/assets.py`: Bilder `GET /assets/avatar/images/{key}`, Greeting `GET /assets/avatar/greeting`; nur validierter effektiver Avatar, keine Client-Pfade; fehlendes Greeting protokollieren/404.
- `backend/app/user_config.py`: `~/.avalo/config.yaml` einmal laden, immutable; unbekannte Felder ablehnen, eindeutige Avatar-Keys/Standardavatar/Animationen/Sprite-Regionen, Asset-Pfadgrenzen und Bilddateien validieren. Persona/Instruktionen pro Avatar; Greeting lazy/fehlend erlaubt. Relative Artefakte relativ zum Projekt; aktive Kokoro-Artefakte beim Start prüfen, inaktives Chatterbox-Referenzaudio nicht.

### Backend: Dienste und Persistenz

- `services/chat.py:ChatService`: `start_turn`, `stream_response`, `finalize_turn`; atomarer Chat+erste Usermessage, Commands, Kontextaufbau, Systemmessage, vollständige Assistant-Persistenz, einmaliger Auto-Titel. Abstrakt vom Runtime-Adapter; Langzeitgedächtnis fehlt.
- `services/context_compression.py`: `ContextCompressionService`, `CompressedContext`, `build_active_context`; char-basierte Schätzung, aktuelle Runden schützen, falls nötig einbeziehen, konkretes Outputbudget bei jedem Versuch neu berechnen, geringwertige Summaries deterministisch entfernen, versioniertes CAS, terminaler Fehler nur wenn Stars allein nicht passen.
- `persistence/chat_repository.py`: atomarer Erstturn, monoton steigende Nachrichten-`seq`, Aktivitätsliste, CRUD/Pin/Auto-Titel-Claim, atomarer Kompressionszustand per erwarteter Version.
- `persistence/models.py`: SQLAlchemy `Chat` (Titel, manuell, Pin, komprimierter Kontext, Seq/Version/Fehler) und `Message` (Chat, Rolle, Inhalt, Seq, Zeit).
- `services/audio_chat.py:AudioChatService`: PTT/Dialog, WAV dual nutzen, `processing`, unabhängige Streams/Persistenz/Fehler, Avatar lazy, Placeholder erst bei Transkript/Assistant-Ausgabe sichtbar, Cleanup nach beiden Konsumenten.
- `services/audio_call.py:AudioCallState`: genau ein globaler Call, gebundene Chat-ID, `turn_active`, eine pending Assistant-Speech; Ende leert Assoziation/Pending.
- `services/tts.py`: `TtsBusyError`, `TtsResult(playback_id,audio)`, single-flight inkl. Cancellation, Playback-ID, Idle-Unload.
- `mcp/server.py`: MCP Streamable-HTTP-Komposition; `mcp/music.py`: Musik-Grenze über `MusicService`.

### Backend: Runtime, Audio und TTS-Adapter

- `runtime/base.py:ModelRuntime` Protocol: async `health`, `warm_up`, `generate_text`, `generate_from_audio`; async Generatoren `generate_text_stream(messages)`, `generate_from_audio_stream(audio_file,messages)`, `transcribe_audio_stream(audio_file)`.
- `runtime/ollama.py:OllamaRuntime`: Prozess-State-LLM je Inferenz lazy auflösen; aktive Text/Audio/Transkript/Titel-Inferenz zählen, während Switch blockieren, Zähler bei Erfolg/Fehler/Cancel freigeben. `/api/show` Modell/Health, `/api/generate` unload/warm-up/kompletter Text (120 s), `/v1/chat/completions` Streaming und Audio (Base64-WAV, 120 s). Streaming gibt nichtleere `choices[0].delta.content`; Audio komplett `choices[0].message.content`, Transkription Audio allein. Remote/ungültige Antwort `RuntimeError`, lokale Dateifehler/Cancel propagieren. Implementierter Spike, Architektur bleibt austauschbar.
- `runtime/llama_cpp.py:LlamaCppRuntime`: geplanter Stub; bevorzugter ADR-Zielruntime, Gemma-4-native-Audio-Spike offen.
- `audio/capture.py`: `CaptureError`, `CapturedAudio(path,duration,sample_rate,channels)`, `_DialogTurnBuffer`, `PipeWireRecorder`, `inspect_wav`. PTT-WAV, Dialog PCM stdout (16k mono S16); Stille vor Sprache ignorieren, 3 s Nachsprechstille entfernen, Limit exakt; Abort löscht; Shutdown SIGINT→kill nach 2 s.
- `audio/input.py`: Contract `PreparedAudio`, `AudioInputPreparer.prepare(source)`, noch contract-only; erwartbar max. 30 s/16 kHz/mono.
- `tts/base.py:TextToSpeech.synthesize(text)->bytes`, `unload()`; `tts/factory.py:create_tts_engine(engine_name?)` wählt Kokoro/Chatterbox oder lehnt ab.
- `tts/kokoro.py`: lazy Modell/Pipeline/Victoria, prüft lokale Artefakte, 24-kHz-WAV, unload gibt CUDA-Cache frei.
- `tts/chatterbox.py`: gepinnter Snapshot lazy, konfiguriertes Referenzaudio/deutsch, CPU-Chunks zusammenführen, unload/CUDA-Cache.

### Frontend

- `frontend/src/main.ts`: Root nach Tauri-Window-Label (`chat` → ChatWindow, sonst App); Titel `Chat Window`; Browser-Entwicklung ohne Tauri; Bootstrap-Fehler loggen.
- `App.vue`: Backend-Readiness/UI-Config, Avatar/Sprites (`standard/listening/thinking/speaking`, 1 s je Sprite), unabhängiger Pending-Ballon; CORS-lesbare Bilder, Alpha-Shapes, Drag-Schwelle, Doppelklick, Skalierung 50–150 %; serialisierte native Resize/Shape-Neuberechnung. Globaler Call: Warm-up, Greeting, Listener/Processing/TTS-Schleife, Event-Recovery statt Idle-Polling, TTS-Queue aus gebundenem Textchat, Exit. Abhängigkeiten: `uiConfig`, Lifecycle, InputShape, ChatWindow, AvatarState, AudioCallEvents, RuntimeWarmup, WindowDrag/Title.
- `ChatWindow.vue`: New Chat + Sidebar (Pinned separat); CRUD/Export/Dialogs, Streaming, Markdown/Milkdown, Sidebar-Splitter, Nachrichtenaktionen/-zeiten, Read aloud, PTT mit Countdown/Quick-release, Call-Delegation und Event-Recovery. Send/Recording bei sichtbarer Generation blockiert, Composer bleibt editierbar; Text im aktiven Call außer laufendem gebundenem Turn möglich; Audio-Placeholder bis Transkript.
- `services/backend.ts`: alle HTTP-Aufrufe, persistierte Chat-CRUD, Text/Audio/Dialog-SSE, TTS, Playback-Ende. Parsed `chat/processing/chunk/transcript_chunk/transcript_error/done/error`; `done` getrennt vom EOF, `AbortSignal`, unvollständige Streams ablehnen. Vor Änderung von API/Transport immer prüfen.
- `composables/useTransientChat.ts`: sichtbarer/transienter und persistierter Zustand, parallele Chatstreams, same-chat-Sperre, EOF-Finalisierung, Rollback, Audio-Placeholder/Transkript/Kontext, Dialog-Pending-Übergang, stale Callbacks. Fehler mit Kontext nach `console.error`, erwartete Abbrüche ruhig.
- `types/chat.ts:ChatMessage`: Rolle, Inhalt, optional `kind text|audio`, `created_at`; mit Hook/ChatWindow prüfen.
- `uiConfig.ts`: `GET /ui/config`, In-flight-Sharing und Webview-Cache, Retry nach Fehler; Avatarname/Greeting/Bilder/Animationen/Sprites.
- `services/chatExport.ts`: Detail neu laden, gespeichertes Markdown chronologisch, `User`/Avatarname-H1, `---` nur zwischen Nachrichten, Dateiname säubern, Tauri Save/FS; Cancel No-op.
- `services/avatarState.ts`: Tauri-Ereignis `AvatarVisualState` + `backendPending`, visueller Zustand getrennt von Pending.
- `services/audioCallEvents.ts`: leichtgewichtiges Invalidation-Event, keine replizierte Daten; Empfänger laden Backend-Status neu.
- `services/runtimeWarmup.ts`: Webview-single-flight, 60-s-Erfolgsthrottle, Fehler loggen/`false` ohne Chatfehler.
- `services/messageTime.ts`: heute `HH:mm`, sonst `YYYY-MM-DD HH:mm`, persistierte Zeit oder pro transientem Objekt gecacht.
- `services/appLifecycle.ts`, `chatWindow.ts`, `windowDrag.ts`, `inputShape.ts`, `windowTitle.ts`: Tauri-Grenzen zu `src-tauri/src/main.rs` bzw. `input_shape.rs`.
- `components/MarkdownComposer.vue`: MilkdownProvider, v-model, Keyboard/Toolbar; `MarkdownComposerEditor.vue`: CommonMark/GFM, kanonische Markdown-Synchronisierung, Formatbefehle/Toolbar. `MarkdownMessage.vue`: Markdown ohne Raw HTML, Tabellen/Listen/Links, highlight.js, Code-Copy, HTML/Plaintext für Copy/TTS, Links via `externalLinks.ts`; `externalLinks.ts` erlaubt nur http/https/mailto/tel, Tauri opener oder Browser-Tab.
- `services/backendLifecycle.ts`: Snapshot/Status/Logs aus `src-tauri/src/backend.rs`.

### Tauri und Desktop-Dateien

- `src-tauri/src/main.rs`: Backend-Lifecycle, Icon, Snapshot/Input-shape/Resize/Chat-fokus/Exit Commands; Avatar-close Exit, Chat-close hide, Backend beim Exit stoppen.
- `src-tauri/src/backend.rs`: `scripts/others/start-backend.sh`, kein Uvicorn-Reload, stdout/stderr, Health-Poll, Status/Logs puffern, technische Fehler stderr, compensated Retries ruhig, Prozess stoppen.
- `src-tauri/src/input_shape.rs`: X11 SHAPE, Frontend-Rechtecke, native Window-ID; Alpha-Masken, Controls künftig unionieren.
- `src-tauri/tauri.conf.json`: Window-Definitionen, Chat min `700x500`, initial `1100x800`.
- `data/blueprints/desktop/avalo.desktop`: Launcher/Icon via `AVALO_ROOT`, Dev-Tauri, `StartupWMClass`; `deploy/install-desktop-entry.sh` substituiert/installiert nach `~/.local/share/applications`.
- `src-tauri/icons/icon.png`: App- und Window-Icon.

## Tests und Fixtures

- Chat: `tests/backend/test_chat_contract.py`, `test_chat_service.py`; Persistenz `test_chat_repository.py`, `test_chats_contract.py`; Kontext `test_context_compression_service.py`.
- Runtime/LLM: `test_runtime_blueprint.py`, `test_ollama_runtime.py`, `test_llm_command.py`; reale Ollama-Integration `tests/integration/test_ollama_integration.py` (Marker, aktive lokale Gemma; Cancel bewusst nicht real).
- Audio: `test_audio_capture.py`, `test_audio_chat_contract.py`, `test_audio_dialog.py`; Mikrofonintegration `tests/integration/test_audio_capture_integration.py` mit `AVALO_TEST_MICROPHONE=1`.
- TTS: `test_tts_contract.py`, `test_tts_service.py`, `test_tts_factory.py`, `test_tts_kokoro.py`, `test_tts_blueprint.py`; Kokoro-Integration `tests/integration/test_kokoro_tts_integration.py` mit `AVALO_RUN_TTS_INTEGRATION=1` und Marker.
- UI/User-Konfiguration: `test_ui_config_contract.py`, `test_user_config.py`, `test_config.py`, `test_health.py`.
- Commands/MCP/Musik: `test_commands.py`, `test_mcp_music.py`, `test_music_service.py`, `test_music_repository.py`, `test_music_adapters.py`, Integration `tests/integration/test_music_mcp.py`.
- Frontend: `tests/frontend/App.spec.ts`, `ChatWindow.spec.ts`, `useTransientChat.spec.ts`; bei konkreten Flows ggf. auch `backend.spec.ts`, `backend.dialog.spec.ts`, `useTransientChat.dialog.spec.ts`, `MarkdownMessage.spec.ts`, `externalLinks.spec.ts` prüfen.
- Fixture `tests/data/german-transcription.wav`: reale Native-Audio-Integration; erwartete Antwort enthält derzeit `diagnostizierte`.

## Änderungsnavigation

| Änderung | Zuerst prüfen |
| --- | --- |
| Öffentlicher Chatvertrag | `api/schemas.py`, `routes/chat.py`, `services/chat.py`, `frontend/src/types/chat.ts`, `services/backend.ts`, `useTransientChat.ts`, Chat-Backend/Frontend-Tests |
| Chatpersistenz | `main.py`, Chat-Schemas/Route/Service, `persistence/database.py`, `models.py`, Alembic `0001`–`0004`, Frontend Backend/Hook/Window und Tests |
| Kontextkompression | `services/context_compression.py`, Chat/Audio-Service, Modelle/Repository/Config, Chat/Audio-Routen und -Schemas, ChatWindow/Hook/backend/types, Kompressions-/Chat-/Audio-Tests |
| Runtime-Vertrag | `runtime/base.py`, `ollama.py`, `llama_cpp.py`, `services/chat.py`, Runtime/Ollama/Integrationstests |
| Ollama oder LLM-Auswahl | `ollama.py`, `config.py`, `state.py`, Commands Factory/Registry/`llm_set.py`, Chat/Main und LLM/State/Ollama/Main-Tests |
| Audio-Chat/Dialog | Capture, Audio-Chat/Call/State, Runtime, Audio-Route/Router/Schemas, ChatWindow/Hook/backend/types, Audio-/Ollama-/Dialog-/Frontendtests |
| Avatar-Feedback | Audio-Service/Route, Frontend Backend/Hook/ChatWindow/AvatarState/CallEvents/Warmup/App/Styles/UIConfig, Audio- und Dialog-/App-Tests |
| TTS | `tts/base.py`, Factory, Kokoro/Chatterbox, TtsService/Route, Config und TTS-Tests; optional reale Integrationen |
| Netzwerk/CORS | `config.py`, `main.py`, Startscript, Frontend `backend.ts`, Config/Health-Tests |
| Frontend-Chat | ChatWindow, Hook, Backend, Types, Markdown-Komponenten, Links, ChatWindow-Service/Main, Frontendtests, Chat-Schemas/Route |
| Desktop-Shell | Tauri Main/Backend/Config/Icon, Desktop Entry/Installer, Frontend Main/App/ChatWindow/Window-Services/Styles, App-Tests |
| Native Inputregionen | `input_shape.rs`, Tauri Main, Frontend InputShape/App/Styles, App-Tests; Alpha-Regionen/CORS und post-resize Geometrie erhalten |
| MCP/Musik | `main.py`, MCP Server/Musik, MusicService/Repository/Playlist/Player, MCP/Musik-Tests, optional Config/Integration |

## Architekturgrenzen und Status

- Anwendung hängt an `ModelRuntime`, nicht an konkreten Runtimes — `docs/adrs/04-local-llm-runtime.md`.
- Modell, Audio und TTS bleiben im Python-Backend — `docs/adrs/03-backend-fastapi.md`.
- Feste Loopback-Bindung — `docs/adrs/05-loopback-http-communication.md`.
- Initial native Gemma-Audio ohne separates STT; PTT maximal 30 s — `docs/adrs/06-native-gemma-audio.md`.
- TTS hinter austauschbarem Python-Adapter — `docs/adrs/07-tts-output.md`.
- Dieser Index ist kompakt, nicht autoritativ — `docs/adrs/08-incremental-repo-map-as-ai-working-index.md`.
- Kleine lokale Patches erst nach genauer Quellprüfung, dann Finaldiff/Testreview — `docs/adrs/09-prompt2code-source-patching.md`.
- Implementiert: FastAPI/Health/Streaming-Chat, persistierte Chats/Kompression, Ollama-Spikes, Tauri-Shell/Backend-Lifecycle/Avatar-Interaktion/X11-Input-Shape, Chat-UI/Markdown, PTT/Dialog/Call, MCP-Musik, lokales TTS inkl. Avatar Call read-aloud.
- Verträge/Stubs: `AudioInputPreparer`, llama.cpp-Runtime. Nicht vorhanden: Memory, Production Packaging.
- Offen: finale lokale LLM-Runtime und Gemma-4-Audiofeasibility, Chatterbox Ressourcen/Qualität, Audio-Chunking/inkrementelle Ollama-Verarbeitung.
