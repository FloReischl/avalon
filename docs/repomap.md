# Avalon RepoMap

Arbeitsindex für Frieda: Impact-Analyse, Implementierungsplanung, Abhängigkeitsnavigation und Auswahl der vor einer Änderung zu prüfenden Dateien. Keine autoritative Dokumentation: Vor jeder Umsetzung Quellcode prüfen. Nur aus akzeptiertem Endstand inkrementell aktualisieren; bei strukturellem Drift Repository neu analysieren.

## System

- **Ziel:** lokaler Desktop-Companion mit Text-Chat, lokalem Speech-to-Text und lokalem TTS.
- **Desktop:** Tauri; transparente Avatar-Shell plus normale Chat-Window; Vue in Tauri-Webviews, Python-Backend als eigener, von Tauri gestarteter/überwachter/beendeter Prozess.
- **Frontend:** Vue 3, TypeScript, Vite in `frontend`; Roots: Avatar `frontend/src/App.vue`, Chat `frontend/src/ChatWindow.vue`; HTTP zum Backend.
- **Backend:** Python, FastAPI, MCP Python SDK v2 in `backend/app`; API, MCP, Application, SQLite-Persistenz, Runtime-Adapter, Audio, TTS, Konfiguration.
- **Transport:** loopback-only `127.0.0.1:8095`, JSON, SSE mit JSON-`data`; API `/api/v1`, MCP `/mcp`. Fachliche API- und MCP-Requests tragen einen lokalen, unsigned Bearer-Token zur Principal-Identifikation; `/health`, UI-Bootstrap, globale Invalidation-SSEs sowie direkt geladene Avatar-/Attachment-Ressourcen sind explizit tokenfrei.
- **MCP-Fähigkeiten:** `music.play_tracks`, `web.search`, `web.get-content`, `workflow.execute`, `content.create-audio`.
- **Authorization:** Principals + `principal_permissions` begrenzen mögliche Rechte; konkrete Grants werden persistent gespeichert. Capability-Aufrufe laufen über `PermissionGuard`; fehlende Grants können einen Human-in-the-loop-Request erzeugen, ohne Authorization-Details dem LLM offenzulegen.

### Desktop- und Fensterverhalten

- `main`: Avatar, always-on-top, transparent, ohne Dekoration; Schließen beendet die App.
- `chat`: initial verborgen, resizable, mit Dekoration; Schließen versteckt Webview-State nur.
- `permissions`: globale Permission-Inbox; zeigt pending Authorization-Requests mit auswählbaren Items und ggf. Grant-Dauer. Pending-State wird per SSE invalidiert; bei Event kurzzeitig per HTTP nachgeladen.
- Avatar-Doppelklick zeigt/fokussiert vorhandenes Chatfenster. Geometrie-Persistenz nicht implementiert.
- Chat-Laufzeitstatus geht über Tauri-Events an Avatar-Webview.
- X11: native SHAPE-Inputregionen aus PNG-Alpha; beide Fenster erhalten das Avalon-Icon. Cinnamon/X11-Identität über Desktop-Entry mit `StartupWMClass=Avalon`.

## Gespräche und Kontext

- SQLite `~/.avalon/avalon.sqlite`, Alembic, SSE-Antworten.
- Start immer mit transientem New Chat; Persistenz beim ersten Senden. Persistierte Chats listen/öffnen vollständige Historie. `Message` ist die gemeinsame chronologische Basis für `TextMessage` und `ProgressMessage`; normale User-/Assistant-Inhalte liegen ausschließlich in `TextMessage`, Workflow-Fortschritt ausschließlich in `ProgressMessage`. Progress-Updates verändern die ursprüngliche Position der Message nicht.
- Aktiver Kontext: Avatar-Systeminstruktionen + komprimierte Historie + Textnachrichten nach `compressed_through_seq`; `ProgressMessage` wird nicht in den LLM-/Kompressionskontext übernommen. Audio mit persistierter `chat_id` rekonstruiert denselben Kontext serverseitig.
- Nach vollständigen Text- und Audioturns best-effort asynchrone Komprimierung. Terminales `chat_context_compression_failed` blockiert Text/Audioturns mit HTTP 409.
- Aktueller Zeitpunkt/Lokation sowie Persona/Instruktionen des effektiven Standardavatars sind eine Systemmessage für Assistenten-Text, nie für STT oder automatische Titel.
- Assistant-Text nur komplett erfolgreich persistieren; Abbruch/Fehler-Teilausgabe nie. Nach exakt zwei kompletten Textrunden ein Titelversuch; manuelle Titel unterdrücken ihn dauerhaft.
- Chats: Pin, Umbenennen, physisch löschen, Markdown exportieren. Reihenfolge im Backend nach Aktivität; UI separiert angeheftete Chats. Löschen des sichtbaren Chats => leeres New Chat.
- Attachments sind unabhängige, unveränderliche File-Artefakte in `~/.avalon/attachments/`; die n:m-Relation zu Messages hat keine weiteren Fachfelder. Sie werden per Copy-in einzeln für bestehende Messages erstellt, beim Löschen einer Message nicht entfernt und niemals automatisch in LLM-Kontext übernommen.
- Audio-UI: Placeholder `🎤 Sprachnachricht` bleibt transient; erst das vollständige STT-Ergebnis wird normale persistierte User-Nachricht und Kontext. STT-Fehler/Timeout/leeres Ergebnis starten kein LLM und hinterlassen keine partielle User-Nachricht. Assistant-Generierung startet danach über den normalen Text-LLM-Pfad.
- Mehrere persistierte Chats können parallele Textstreams haben; Stop betrifft nur den sichtbaren laufenden Chat.
- Ein persistierter Chat kann per `/agent invite <key|name-prefix> [-force]` einem konfigurierten Agenten zugeordnet und per `/agent unload` wieder auf den Default-Chat-Principal zurückgesetzt werden. Der aktive Agent bestimmt Persona/Instructions sowie den effektiven Authorization-Principal des Chats; Kontextkompression verwendet dieselbe Identität. Agent-Keys sind case-insensitiv eindeutig.

## Kernflüsse

### Backendstart und Health

- Entry `backend/app/main.py:create_app`: User-Konfiguration laden/validieren, dann Alembic bis Head; Fehler lassen Start fehlschlagen und Traceback auf stderr. CORS für Browser `GET, POST, PATCH, DELETE`; Router installieren.
- `GET /health` → `backend/app/api/routes/health.py:health`, Schema `HealthResponse`; nur HTTP-Readiness.

### Text-Chat

- `POST /api/v1/chat` → `routes/chat.py:create_chat_response` → `ChatService` → `ModelRuntime.generate_text_stream`.
- Request `{"message":"<prompt>"}` oder `{"chat_id":<id>,"message":"<prompt>"}`; unbekannte Chat-ID vor `StreamingResponse` mit 404 ablehnen.
- SSE: `chat {"id":"<chat-id>"}`, `chunk {"text":"<chunk>"}`, `done {}`, `error {}`. Reihenfolge: `chat`, 0+ `chunk`, `done`; `done` vor optionaler Titel-Finalisierung, EOF erst danach. Laufzeitfehler: `error`, kein `done`; technische Details nicht öffentlich. Cancellation propagiert ohne `error`.

### Authorization und Tool-Calls

- Neue Chats erhalten `chat.principal_key` aus `config.yaml`; `chat.permissions` ist für dessen Principal-Permissions autoritativ und wird beim App-Start analog zu Agent-Permissions transactional reconciliiert. Chat/Agent-Identität bestimmt den effektiven Permission-Träger.
- `ToolRunner` ist capability-agnostisch: principal-spezifische Tooldefinitionen werden über MCP `tools/list` bezogen und statisch gecacht; LLM-Tool-Calls werden generisch über MCP `tools/call` ausgeführt. Identische Calls werden innerhalb eines Tool-Loops über stabile Call-Keys nur einmal ausgeführt und das Ergebnis wiederverwendet.
- MCP bildet die Authorization-Grenze. Toolnamen `<context>.<key>` werden über `(context, key)` dynamisch gegen `permission_catalog` aufgelöst. `tools/list` exponiert nur Tools mit passender `principal_permission`; Grants beeinflussen Discovery nicht. `tools/call` verwendet dieselbe Permission-Auflösung und führt den Call über `PermissionGuard` aus.
- `PermissionGuard`: aufgelöste `principal_permission` → vorhandenen Grant für den gesamten Call prüfen → sonst Authorization-Request erzeugen und Capability-Call bis Entscheidung suspendieren. Konkrete Permission-Implementierung interpretiert Scope/Items und formatiert Items für die UI.
- Grant-Typen: `permanent`, `duration`, `range`; `range` speichert konkrete freigegebene Items und ist zeitlich begrenzt. UI darf die Items des aktuellen Calls einschränken, nie erweitern; Confirm mit leerer Auswahl ist erfolgreicher Call mit leerer Itemliste.
- Grants können zusätzlich proaktiv über das Permissions-Window eines Chats verwaltet werden. Maßgeblich ist der effektive Principal des Chats. `permanent` und `duration` können erteilt, geändert oder durch Abwählen entfernt werden; abgelaufene Duration-Grants gelten als nicht vorhanden. Neue Duration-Grants verwenden `default_expiry` der `principal_permission` zur Initialisierung der konkreten Ablaufzeit. `range` kann ohne Capability-Request nicht proaktiv erzeugt werden; bestehende aktive Range-Grants werden nur read-only angezeigt.
- Kein `principal_permission` → `PermissionDenied` ohne Dialog. Benutzer-Abbruch → `AbortException`; Timeout → `AuthorizationTimeout`. Abort beendet die aktuelle Agent-/Tool-Operation.
- `GET /api/v1/authorization-requests` liefert die globale Pending-Inbox; Confirm/Abort entscheiden Requests. `/authorization-requests/events` sendet SSE-Invalidierungen. Permission-Window lädt initial und nach Event; bei noch nicht sichtbarem Request pollt es höchstens 5 s in 500-ms-Abständen und stoppt sobald ein Request sichtbar ist.
- Das Permissions-Window unterstützt zwei Modi: reaktiv für offene Authorization-Requests und proaktiv für die Grants eines konkreten Chats. Das Chat-Kontextmenü öffnet den proaktiven Modus über `Permissions`.

### Audio

- Capture Python-Backend via `PipeWireRecorder`/`pw-record`; PTT und Dialog teilen Recorder und laufen nicht parallel. Kein hartes Aufnahmelimit.
- PTT: Chatfenster gedrückt → `POST /audio/recording/start` → release `POST /audio/recording/stop` mit Client-Kontext/optional `chat_id`; Capture startet sofort, Whisper-Warm-up parallel.
- Dialog: Avatar Call besitzt den kontinuierlichen Modus; Chat Call delegiert mit selektierter `chat_id`. `POST /audio/dialog/turn`; wartet vor Sprache unbegrenzt, RMS startet den Turn, konfigurierter Stillezeitraum beendet ihn.
- STT ist unabhängig vom `ModelRuntime`: `faster-whisper` `small`, CPU-only/int8, fest `de`, `beam_size=5`. PCM wird während Capture in 10-s-Fenstern mit 2-s-Overlap/8-s-Step transkribiert; nur ein Whisper-Inference gleichzeitig. Finaler Tail nur für noch nicht vollständig abgedecktes Audio; Transkripte deterministisch über exakten normalisierten Wort-Overlap zusammenführen.
- Nach Recording-Ende dürfen ausstehende STT-Arbeiten maximal 30 s den Turn aufhalten. STT-Fehler, Timeout oder leeres Endtranskript beenden den Turn ohne LLM-Aufruf. Bereits laufende blockierende Whisper-Inference darf im Worker auslaufen und hält bis dahin Single-Flight, ohne den fehlgeschlagenen Turn weiter zu blockieren.
- Erfolgsfluss: Capture → vollständiges STT → finale User-Nachricht persistieren → normalen Textkontext aufbauen → `ModelRuntime.generate_text_stream` → Assistant persistieren/TTS. Kein Audio wird an den LLM-Runtime-Adapter gesendet.
- Whisper lazy-load; Idle-Unload nach 10 min ohne STT-Nutzung, solange kein Audio-Call aktiv ist. Aktiver Audio-Call hält Whisper resident. Call-Readiness verlangt LLM- und Whisper-Warm-up; erst danach `greeting_audio`.
- Avatar-Call ohne Chat bindet beim ersten erfolgreichen Sprachturn einen Chat; Bindung bleibt bis Call-Ende. Nach Read-Aloud startet Listener erneut, Ende nur explizit am Avatar.
- Während Modell/TTS keine Audio-Barge-in. Stop von Antwort-Audio bricht Modell nicht ab; Stop vor TTS überspringt TTS. Call-State umfasst Aufnahme, Modellverarbeitung und Playback als aktiven Turn; Textantworten im gebundenen Call-Chat werden für Avatar-TTS eingereiht.
- Capture-Vorgaben: `audio_wait_exceed_seconds`, RMS `0.015`, 16 kHz mono S16. MediaRecorder wurde nach WebKitGTK-Nullchunks verworfen.

### TTS

- Contract `backend/app/tts/base.py:TextToSpeech`; Factory `create_tts_engine`; Lifecycle `TtsService`.
- Endpoints: `POST /api/v1/tts`, `POST /api/v1/tts/playback-ended`; vollständiges WAV, eine Synthese gleichzeitig, keine Queue. Playback-ID steuert Idle-Lifecycle, stale ended ignorieren, Unload nach 300 s ohne Synthese/aktives Playback.
- Frontend wandelt fertiges Markdown in Plaintext.
- Kokoro (Default): `KokoroTextToSpeech`, Kikiri German Victoria/Kokoro-82M, 24 kHz, CUDA bevorzugt dann CPU; lokale Artefakte, kein Runtime-Download.
- Chatterbox: `ChatterboxTextToSpeech`, Multilingual V2, 4-bit bitsandbytes; satzorientierte Chunks. V3 gewann Qualitätsvergleich, verfügbarer Adapter bleibt V2.
- Gemma bleibt GPU-resident; Kokoro ist wegen Ressourcen/Interaktion Default, Chatterbox bei gerechtfertigtem Qualitätsgewinn.

### MCP-Fähigkeiten

- MCP Streamable HTTP `/mcp` ist die einheitliche Capability-Grenze; Discovery und Aufruf erfolgen über `tools/list` bzw. `tools/call`. Toolnamen folgen `<context>.<key>` und werden über `permission_catalog` an das Permission-System gebunden.
- `music.play_tracks` (`backend/app/mcp/music.py:register_music_tools`) ist als MCP-Capability registriert; Sichtbarkeit für einen Principal entsteht erst durch eine entsprechende `principal_permission`.
- `track_ids: list[int]` wird vollständig geloggt; `MusicService` löst `tracks.id → file_path` aus externer Musik-SQLite auf. Reihenfolge/Duplikate erhalten, unbekannte IDs auslassen; Playlist `/tmp/avalon_music.m3u`, Celluloid starten.
- `web.search(query)` (`backend/app/mcp/web.py:register_web_tools`) delegiert an `WebSearchService`; vollständige Query vor Ausführung loggen.
- `WebSearchService` nutzt `ddgs`/DuckDuckGo außerhalb des asyncio-Event-Loops: Region `de-de`, SafeSearch off, max. 5 Treffer, 10-s Timeout, keine Retries. Ergebnis `title`, `url`, `snippet`; keine Treffer `[]`, Provider-/Formatfehler propagieren.
- `web.get-content(url)` lädt HTTP/HTTPS-Inhalte mit Redirect-Validierung, 10-s Timeout und ohne Retries. Nur finale 2xx-Antworten mit `text/html` oder `text/plain`; HTML wird als LLM-tauglicher Hauptinhalt extrahiert. Ergebnis `url`, `content`, `truncated`; Content maximal 20.000 Zeichen. Private/Loopback-/Link-local-Ziele sind erlaubt.
- `workflow.execute(workflow_key, payload)` (`backend/app/mcp/workflow.py`) startet ausschließlich registrierte Workflows. `workflows.yaml` wird beim Backendstart geladen/validiert und löst den logischen Workflow-Key serverseitig auf einen Python-Dateipfad auf. Der interne MCP-Client transportiert `chat_id` und eine pro LLM-/Tool-Cycle erzeugte `invocation_id` serverseitig über Request-`_meta`; diese Runtime-Metadaten sind keine LLM-generierten Tool-Argumente. `WorkflowService` verlangt den effektiven Principal des aufrufenden Chats, prüft dessen Chat-Zuordnung, erzeugt für die Invocation eine chronologisch positionierte `ProgressMessage` und eine persistierte `WorkflowExecution`, startet den Workflow out-of-process mit `sys.executable` und übergibt per stdin einen JSON-Envelope aus Avalon-Runtime-Kontext und workflow-spezifischem Payload. Der `avalon`-Header enthält `workflow_execution_id`, Backend-URL und den lokalen Bearer-Token des Parent-Principals sowie einen Snapshot des Modellkontexts zum Startzeitpunkt: effektive Persona und Instructions des aufrufenden Chats, den aktiven Gesprächskontext unter Berücksichtigung von `compressed_context`/`compressed_through_seq` sowie aktuellen Europe/Berlin-Zeit- und München-Ortskontext. Der Workflow besitzt keinen eigenen Principal und verwendet den Parent-Principal-Token für seine Avalon-HTTP-Aufrufe; der fachliche `payload` bleibt davon getrennt und unverändert.
- `WorkflowExecution` ist die autoritative Lifecycle-Entität mit `running|pending|completed|failed|aborted`; terminale Executions sind unveränderlich. Exit 0 setzt eine noch nicht terminale Execution auf `completed`, Non-zero Exit auf `failed` und ergänzt sichtbaren technischen Progress; ein Prozess-Startfehler wird ebenfalls als `failed` mit verständlicher Progress-Meldung persistiert. Runtime-Updates werden über den Bearer-Principal identifiziert und nur akzeptiert, wenn die Execution zu einem Chat dieses Principals gehört; ein separater execution-spezifischer Runtime-Token existiert nicht mehr.
- Workflow-Progress wird über die Runtime-API persistent als vollständiger Message-Stack der zugehörigen `ProgressMessage` aktualisiert. Tatsächliche Änderungen erzeugen eine SSE-Invalidierung; identische Updates sind idempotent und erzeugen kein Event. Das Frontend lädt nach Invalidation den persistenten Chat neu; die DB bleibt die autoritative Wahrheit.
- `workflow.execute` ist kein generischer Python-Executor: `WorkflowExecutePermission` verlangt exakt einen Workflow-Key und dessen explizite Aufnahme in den `principal_permission.scope`; leere Items, leerer/nicht passender Scope oder unbekannte Workflow-Keys erlauben keinen Prozessstart.
- `content.create-audio(content, output_file)` erzeugt über die bestehende Kokoro-TTS eine MP3-Datei. `output_file` muss `.mp3` sein; Parent-Verzeichnisse werden angelegt, bestehende Ziele ersetzt. Die Capability erzeugt zunächst WAV und konvertiert per `ffmpeg` über eine temporäre MP3; das finale Ziel wird erst nach erfolgreicher Konvertierung ersetzt. `ContentCreateAudioPermission` begrenzt Zielpfade über `principal_permission.scope`.

## Module

### Backend: Komposition, API und Konfiguration

- `backend/app/config.py`: eingefrorene `LlmConfig(key, model)`, `Settings`-Singleton. Relevante Felder: Netz/DB/CORS/Sprache, Audio-Silence, Kontextkompressions-Parameter, Ollama, `llm_models`, TTS-Engine/Device/Revision/Idle. Für Start, Health, Runtime, Audio, TTS.
- `backend/app/state.py`: prozesslokaler Avatar, aktives LLM, Inferenzzähler, Switch-Guard; Standard-LLM beim Start, nicht persistent; Modellwechsel während Inferenz blockieren.
- `backend/app/commands`: async `/ <group> <command> [payload]`; `/avatar set <key>`, `/llm set <key>`, `/agent invite <key-or-name-prefix> [-force]`, `/agent unload`. Agent-Invite löst zuerst exakte Keys, dann eindeutige Namenspräfixe auf; `-force` ersetzt einen bereits zugeordneten Agenten. Invite/Unload wechseln die persistierte Chat/Agent-Autorisierungsidentität; der bestehende Chatverlauf bleibt erhalten. LLM: unbekannt/nicht verfügbar ablehnen, gleiches Modell No-op, altes unloaden, Ziel aufwärmen, erst dann publizieren; bei Warm-up-Fehler altes wiederherstellen, bei Fehlschlag terminieren.
- `backend/app/main.py`: `create_app() -> FastAPI`, `StderrExceptionMiddleware`, Principal-ASGI-Grenze, `app`; validiert Konfiguration, initialisiert State, verlangt Standard-LLM in Ollama, warnt bei anderen, Alembic + MCP-Session-Lifespan, mountet `/mcp`. Fachliche API-/MCP-Requests lösen den lokalen unsigned Bearer-Token zentral zur `principal_id` auf; API-Requests erhalten sie im ASGI-Scope, MCP über request-lokalen Principal-Kontext.
- `backend/app/mcp/security.py`: gemeinsames lokales Bearer-Tokenformat zur Principal-Identifikation; erzeugt Tokens aus `principal_id` und löst sie wieder auf. Der Token ist innerhalb Avalons Local-Only/Linux-User-Security-Grenze ein Identitätstransport, kein externes Security-Credential; keine Signatur oder Expiry.
- `backend/app/api/router.py`: Health root; UI, Assets, Runtime, Chat, Chatmanagement, Authorization, Audio/Call, TTS unter `/api/v1`.
- `backend/app/authorization`: `PermissionGuard`, konkrete Permission-Checks/Formatter, Authorization-Request-Manager, Typen/Exceptions und Runtime-Wiring.
- `backend/app/persistence/authorization_repository.py`: Principals, Permission-Katalog/-Rahmen und Grants; Alembic `0005_add_authorization_schema.py`.
- Agent-Permissions aus `agents.yaml` sowie Default-Chat-Permissions aus `config.yaml:chat.permissions` werden beim App-Start validiert und transactional in die Authorization-DB reconciliiert. Fehlende Principals/Agents und Permission-Catalog-Einträge werden angelegt; Principal-Permissions werden angelegt, aktualisiert, reaktiviert oder via `is_active=false` deaktiviert. `scope` bleibt semantisch opaque und wird als kanonisches JSON persistiert. Der Reconcile ist atomar und idempotent; die jeweilige Konfiguration ist für die Permissions des Principals führend.
- `backend/app/services/tool_runner.py`: capability-agnostischer LLM-Tool-Loop; bezieht principal-spezifische Tooldefinitionen über MCP, cached sie statisch und dispatcht Tool-Calls generisch über MCP. Der interne MCP-Client ergänzt serverseitigen Invocation-Kontext (`chat_id`, `invocation_id`) als Request-`_meta`, ohne ihn dem LLM als Tool-Argument zu exponieren. Turn-lokaler Result-Cache verhindert wiederholte Ausführung identischer Tool-Calls.
- `backend/app/api/routes/authorization.py`: Pending-Requests, Confirm/Abort und SSE-Invalidierungen für die globale Permission-Inbox.
- `backend/app/api/routes/runtime.py` — runtime control endpoints (warm-up).
- `backend/app/api/routes/llm.py` — stateless LLM inference; `POST /api/v1/llm/text` accepts caller-supplied `system`/`user`/`assistant` messages and returns non-streaming text without chat context, persistence, or tool calling.
- `backend/app/api/schemas.py`: öffentliche Verträge. `ChatRequest(chat_id?: positive int, message: non-empty)`, `ConversationMessage(role user|assistant, content)`, `AudioResponseRequest(messages, chat_id?)`, `HealthResponse`, Chat summary/detail (inkl. `pinned`, `compression_error_code`, Message-Attachments), Rename (max. 200), Pin, TTS, Playback-ended, UI-Konfiguration/Avatar/Sprite-Regionen.
- `routes/health.py`: `health() -> HealthResponse`.
- `routes/runtime.py`: `POST /api/v1/runtime/warm-up`, stateless best-effort, Inhalt verwerfen.
- `routes/chat.py`: request-scoped ChatService mit Ollama/Persistenz und ToolRunner; `format_sse_event`, Chat-/Authorization-SSE und Fehlerabbildung; Cancellation unverändert.
- `routes/chats.py`: `GET /chats`, `GET /chats/{id}`, `PATCH /chats/{id}`, `PATCH /chats/{id}/pinned`, `DELETE /chats/{id}`.
- `routes/attachments.py`: `POST /messages/{message_id}/attachments` (Multipart-Copy-in) und `GET /attachments/{id}/download`.
- `routes/audio.py`: Call status/start/end/turn-complete/speech-consume; recording start/abort/stop; dialog turn. Nutzt `AudioChatService`, `AudioCallState`, `ChatRepository`.
- `routes/tts.py`: Synthese und Playback-Lifecycle; `TtsService`, Factory.
- `routes/ui.py`: `GET /ui/config`, nur frontend-sichere effektive Standardavatar-Daten; fertige absolute Asset-URLs mit Prozess-Cache-Token, keine Persona/Instruktionen/Pfade/TTS.
- `routes/assets.py`: Bilder `GET /assets/avatar/images/{key}`, Greeting `GET /assets/avatar/greeting`; nur validierter effektiver Avatar, keine Client-Pfade; fehlendes Greeting protokollieren/404.
- `backend/app/user_config.py`: `~/.avalon/config.yaml` einmal laden, immutable; unbekannte Felder ablehnen. Relative Artefakte relativ zum Projekt; aktive Kokoro-Artefakte beim Start prüfen, inaktives Chatterbox-Referenzaudio nicht.
- `backend/app/avatars_config.py`: `~/.avalon/avatars.yaml` einmal laden, immutable; eindeutige Avatar-Keys/Standardavatar/Animationen/Sprite-Regionen, Asset-Pfadgrenzen und Bilddateien validieren. Persona/Instructions pro Avatar; Greeting lazy/fehlend erlaubt.
- `agents.yaml`: autoritative Agent-Konfiguration einschließlich Permission-Catalog-Referenzen und Principal-Permissions; Permission-Scopes dürfen strukturierte YAML-Werte enthalten und werden ohne Capability-spezifische Interpretation persistiert.

### Backend: Dienste und Persistenz

- `services/chat.py:ChatService`: `start_turn`, `stream_response`, `finalize_turn`; atomarer Chat+erste Usermessage, Commands, Kontextaufbau, Systemmessage, vollständige Assistant-Persistenz, einmaliger Auto-Titel. Abstrakt vom Runtime-Adapter; Langzeitgedächtnis fehlt.
- `services/context_compression.py`: `ContextCompressionService`, `CompressedContext`, `build_active_context`; char-basierte Schätzung, aktuelle Runden schützen, falls nötig einbeziehen, konkretes Outputbudget bei jedem Versuch neu berechnen, geringwertige Summaries deterministisch entfernen, versioniertes CAS, terminaler Fehler nur wenn Stars allein nicht passen.
- `persistence/chat_repository.py`: atomarer Erstturn, monoton steigende Nachrichten-`seq`, Aktivitätsliste, CRUD/Pin/Auto-Titel-Claim, atomarer Kompressionszustand per erwarteter Version; Textkontext liest ausschließlich `TextMessage`, während Chat-Details Text- und Progress-Messages chronologisch projizieren.
- `persistence/models.py`: SQLAlchemy `Chat` (Titel, manuell, Pin, komprimierter Kontext, Seq/Version/Fehler); `Message` als gemeinsame chronologische Basis mit konkreten `TextMessage`- und `ProgressMessage`-Daten; `WorkflowExecution` hält Workflow-Key und Lifecycle-State und ist mit seiner ProgressMessage verbunden; immutable `Attachment` und `MessageAttachment`. Ein separater Workflow-Runtime-Token wird nicht persistiert.
- Workflow-Persistenz korreliert Progress über `(chat_id, invocation_id)`. Eine neue Invocation erzeugt eine neue `ProgressMessage`; deren Inhalt darf später aktualisiert werden, ohne ihre chronologische Position zu verändern. `WorkflowExecution` und `ProgressMessage` bleiben getrennte Verantwortlichkeiten: Execution = technische Lifecycle-Wahrheit, ProgressMessage = sichtbarer Conversation-Container.
- `persistence/attachment_repository.py`, `services/attachments.py`: transaktionelles Persistieren/Verknüpfen und Copy-in-Storage mit UUID-Dateinamen, inhaltsbasierter MIME-Ermittlung via lokalem `file`-Tool (Fallback `application/octet-stream`) und 50-MB-Limit.
- `services/audio_text_chat.py:AudioTextChatService`: orchestriert PTT/Dialog als STT-first-Pipeline; Streaming-Chunks seriell transkribieren/mergen, finalen Usertext vor normalem Text-LLM persistieren, Post-Recording-STT-Timeout/Fehler/Empty behandeln, temporäre Audioartefakte bereinigen. PTT startet Capture vor parallelem Whisper-Warm-up.
- `services/audio_call.py:AudioCallState`: genau ein globaler Call, gebundene Chat-ID, `turn_active`, eine pending Assistant-Speech; Ende leert Assoziation/Pending.
- `services/tts.py`: `TtsBusyError`, `TtsResult(playback_id,audio)`, single-flight inkl. Cancellation, Playback-ID, Idle-Unload.
- `services/audio_creation.py`: `AudioCreationService` erzeugt über die bestehende TTS-Abstraktion WAV und konvertiert per externem `ffmpeg` zu MP3; temporäre Artefakte werden bei Erfolg und Fehler bereinigt, das Ziel erst nach erfolgreicher Konvertierung ersetzt.
- `mcp/server.py`: MCP Streamable-HTTP-Komposition, Tool-Registrierung und zentrale Authorization-Grenze; principal-spezifische Discovery über `permission_catalog`/`principal_permissions`, Capability-Aufrufe über dieselbe Permission-Auflösung und `PermissionGuard`. `mcp/music.py`: Musik-Grenze über `MusicService`; `mcp/web.py`: reine Websuch-Grenze über `WebSearchService`; `mcp/workflow.py`: registrierte Workflow-Ausführung über `WorkflowService`; `mcp/content.py`: Audio-Content-Erzeugung über `AudioCreationService`.
- `workflows_config.py`, `services/workflows.py`: statische Workflow-Registry aus `workflows.yaml`; Workflow-Key → serverseitiger Python-Pfad. `WorkflowService` persistiert ProgressMessage/WorkflowExecution vor dem Prozessstart, übergibt Runtime-Envelope + Payload via stdin an den separaten Prozess und überwacht dessen Exit asynchron. Der normale Produktionspfad verwendet die beim App-Start injizierte langlebige DB-/Repository-Infrastruktur.

### Backend: Runtime, Audio und TTS-Adapter

- `backend/app/runtime/base.py:ModelRuntime` Protocol ist text-only: async `health`, `warm_up`, `generate_text`; `generate_text_stream(messages)` für Chatantworten. STT gehört nicht zum Runtime-Vertrag.
- `backend/app/runtime/ollama.py:OllamaRuntime`: Prozess-State-LLM je Inferenz lazy auflösen; aktive Text-/Titel-Inferenz zählen und LLM-Switch während Inferenz blockieren. `/api/show` Modell/Health, natives `/api/chat` für Warm-up sowie komplette, streamende und Tool-Generierung; Tool-Turns können Content und native Tool-Calls streamen, non-streaming Tool-Generierung bleibt separat verfügbar. Qwen2.5-Coder-Tool-Calls, die Ollama als eindeutiges JSON im Assistant-Content statt als `tool_calls` liefert, werden vor Ausgabe gepuffert und eng auf Ollamas natives Tool-Call-Format normalisiert. `/api/generate` nur für Unload; kein Base64-/Native-Audio-Pfad.

- `backend/app/runtime/base.py:ModelRuntime` Protocol ist text-only: async `health`, `warm_up`, `generate_text`, `generate_text_messages(messages)`; `generate_text_stream(messages)` für Chatantworten. STT gehört nicht zum Runtime-Vertrag.
- `backend/app/runtime/ollama.py:OllamaRuntime`: Prozess-State-LLM je Inferenz lazy auflösen; aktive Text-/Titel-Inferenz zählen und LLM-Switch während Inferenz blockieren. `/api/show` Modell/Health, natives `/api/chat` für Warm-up sowie komplette, message-basierte non-streaming, streamende und Tool-Generierung; `generate_text_messages(messages)` führt stateless non-streaming Inferenz gegen das aktive Modell aus. Tool-Turns können Content und native Tool-Calls streamen, non-streaming Tool-Generierung bleibt separat verfügbar. Qwen2.5-Coder-Tool-Calls, die Ollama als eindeutiges JSON im Assistant-Content statt als `tool_calls` liefert, werden vor Ausgabe gepuffert und eng auf Ollamas natives Tool-Call-Format normalisiert. `/api/generate` nur für Unload; kein Base64-/Native-Audio-Pfad.


- `backend/app/runtime/llama_cpp.py:LlamaCppRuntime`: geplanter text-only Stub.
- `backend/app/stt/whisper.py`: `FasterWhisperSttService`, `StreamingPcmChunker`, `AudioChunk`, `merge_transcripts`; Whisper `small` strikt CPU/int8, `de`, beam 5; 10/2-Chunking, serialisierte blockierende Inferenz außerhalb des asyncio-Event-Loops, Lazy-/Idle-Lifecycle und Call-Residency.
- `backend/app/audio/capture.py`: `CaptureError`, `CapturedAudio`, `_DialogTurnBuffer`, `PipeWireRecorder`; PTT/Dialog über 16-kHz-mono-S16-PCM, laufende volle STT-Fenster an Sink liefern, finalen Tail beim Stop erzeugen; Dialog ignoriert Stille vor Sprache und endet über konfigurierte Nachsprechstille; kein Duration-Limit; Abort/Cleanup und SIGINT→kill.
- `backend/app/tts/base.py:TextToSpeech.synthesize(text)->bytes`, `unload()`; `tts/factory.py:create_tts_engine(engine_name?)` wählt Kokoro/Chatterbox oder lehnt ab.
- `backend/app/tts/kokoro.py`: lazy Modell/Pipeline/Victoria, prüft lokale Artefakte, 24-kHz-WAV, unload gibt CUDA-Cache frei.
- `backend/app/tts/chatterbox.py`: gepinnter Snapshot lazy, konfiguriertes Referenzaudio/deutsch, CPU-Chunks zusammenführen, unload/CUDA-Cache.

### Frontend

- `frontend/src/main.ts`: Root nach Tauri-Window-Label (`chat` → ChatWindow, sonst App); Titel `Chat Window`; Browser-Entwicklung ohne Tauri; Bootstrap-Fehler loggen.
- `App.vue`: Backend-Readiness/UI-Config, Avatar/Sprites (`standard/listening/thinking/speaking`, 1 s je Sprite), unabhängiger Pending-Ballon; CORS-lesbare Bilder, Alpha-Shapes, Drag-Schwelle, Doppelklick, Skalierung 50–150 %; serialisierte native Resize/Shape-Neuberechnung. Globaler Call: Warm-up, Greeting, Listener/Processing/TTS-Schleife, Event-Recovery statt Idle-Polling, TTS-Queue aus gebundenem Textchat, Exit. Abhängigkeiten: `uiConfig`, Lifecycle, InputShape, ChatWindow, AvatarState, AudioCallEvents, RuntimeWarmup, WindowDrag/Title.
- `ChatWindow.vue`: New Chat + Sidebar (Pinned separat); CRUD/Export/Dialogs, Streaming, Markdown/Milkdown, Sidebar-Splitter, Nachrichtenaktionen/-zeiten, Workflow-Progress-Decorator, Read aloud, PTT mit Countdown/Quick-release, Call-Delegation und Event-Recovery. Export bietet Markdown als Datei-Download oder denselben Markdown-Inhalt per Clipboard; das Export-Submenu darf die Sidebar-Grenze überragen. ProgressMessages bleiben an ihrer ursprünglichen chronologischen Position; Workflow-SSE invalidiert den Zustand und löst Reload aus Persistenz aus. Send/Recording bei sichtbarer Generation blockiert, Composer bleibt editierbar; Text im aktiven Call außer laufendem gebundenem Turn möglich; Audio-Placeholder bis Transkript.
- `services/backend.ts`: fachliche HTTP-Aufrufe verwenden zentral den beim UI-Bootstrap erhaltenen lokalen Principal-Bearer; persistierte Chat-CRUD, Text/Audio/Dialog-SSE, Workflow-Invalidation-SSE, TTS, Playback-Ende. Parsed `chat/processing/chunk/transcript_chunk/transcript_error/done/error`; `done` getrennt vom EOF, `AbortSignal`, unvollständige Streams ablehnen. Workflow-Invalidierung führt zum Reload aus Persistenz statt zu einer zweiten Client-State-Wahrheit. Vor Änderung von API/Transport immer prüfen.
- `composables/useTransientChat.ts`: sichtbarer/transienter und persistierter Zustand, parallele Chatstreams, same-chat-Sperre, EOF-Finalisierung, Rollback, Audio-Placeholder/Transkript/Kontext, Dialog-Pending-Übergang, stale Callbacks. Fehler mit Kontext nach `console.error`, erwartete Abbrüche ruhig.
- `types/chat.ts`: Chat-Conversation unterscheidet persistierte Text-/Audio-Darstellung und Workflow-Progress; Progress enthält Workflow-/Lifecycle-Daten und den sichtbaren Message-Stack. Mit Hook/ChatWindow prüfen.
- `uiConfig.ts`: tokenfreier Bootstrap über `GET /ui/config`, In-flight-Sharing und Webview-Cache; Transportfehler und HTTP-5xx werden nach dem Initialversuch bis zu 10-mal im Abstand von 500 ms retried, andere HTTP-Fehler unmittelbar propagiert. Liefert neben Avatarname/Greeting/Bildern/Animationen/Sprites den lokalen Bearer-Token des Default-Chat-Principals für nachfolgende fachliche Frontend-Requests.
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
- `data/blueprints/desktop/avalon.desktop`: Launcher/Icon via `AVALON_ROOT`, Dev-Tauri, `StartupWMClass`; `deploy/install-desktop-entry.sh` substituiert/installiert nach `~/.local/share/applications`.
- `src-tauri/icons/icon.png`: App- und Window-Icon.

## Tests und Fixtures

- Chat: `tests/backend/test_chat_contract.py`, `test_chat_service.py`; Persistenz `test_chat_repository.py`, `test_chats_contract.py`; Kontext `test_context_compression_service.py`.
- Runtime/LLM: `test_runtime_blueprint.py`, `test_ollama_runtime.py`, `test_llm_command.py`; reale Ollama-Integration `tests/integration/test_ollama_integration.py` (Marker, aktive lokale Gemma; Cancel bewusst nicht real).
- Audio/STT: `test_audio_capture.py`, `test_audio_chat_contract.py`, `test_audio_dialog.py`, `test_audio_text_chat.py`, `test_whisper_stt.py`; reale faster-whisper-Transkription von `tests/data/german-transcription.wav` läuft im normalen Pytest-Lauf; Mikrofonintegration `tests/integration/test_audio_capture_integration.py` mit `AVALON_TEST_MICROPHONE=1`.
- TTS: `test_tts_contract.py`, `test_tts_service.py`, `test_tts_factory.py`, `test_tts_kokoro.py`, `test_tts_blueprint.py`; Kokoro-Integration `tests/integration/test_kokoro_tts_integration.py` mit `AVALON_RUN_TTS_INTEGRATION=1` und Marker.
- UI/User-Konfiguration: `test_ui_config_contract.py`, `test_user_config.py`, `test_config.py`, `test_health.py`.
- Commands/MCP/Musik/Web/Workflow/Content: `test_commands.py`, `test_mcp_music.py`, `test_mcp_web.py`, `test_mcp_content.py`, `test_audio_creation_service.py`, Workflow-MCP-/Service-/Runtime-Contract-Tests, `test_web_search_service.py`, `test_music_service.py`, `test_music_repository.py`, `test_music_adapters.py`; Principal-/MCP-/ToolRunner-Tests prüfen Bearer→Principal-Auflösung, principal-spezifische Discovery, zentrale Authorization, generischen Dispatch, Request-`_meta`-Kontext, Caching und Call-Deduplizierung. Content-Tests prüfen Zielpfad-Scope, MP3-Erzeugung, Overwrite-/Fehlersemantik und dass Permission-Denial die Fachlogik nicht erreicht. Workflow-Tests decken Progress-/Execution-Persistenz, Parent-Principal/Ownership, Lifecycle/Process-Exit sowie idempotente SSE-Invalidierung ab. Integrationen: `tests/integration/test_music_mcp.py`; opt-in MCP/Ollama-Spike `test_mcp_ollama_tool_calling_spike.py` mit bewusst volatiler lokaler Modellmatrix.
- Frontend: `tests/frontend/App.spec.ts`, `ChatWindow.spec.ts`, `useTransientChat.spec.ts`; bei konkreten Flows ggf. auch `backend.spec.ts`, `backend.dialog.spec.ts`, `useTransientChat.dialog.spec.ts`, `MarkdownMessage.spec.ts`, `externalLinks.spec.ts` prüfen.
- Fixture `tests/data/german-transcription.wav`: kleine reale faster-whisper-Integration für den CPU/int8-Produktions-STT-Pfad.

## Änderungsnavigation

| Änderung | Zuerst prüfen |
| --- | --- |
| Öffentlicher Chatvertrag | `api/schemas.py`, `routes/chat.py`, `services/chat.py`, `frontend/src/types/chat.ts`, `services/backend.ts`, `useTransientChat.ts`, Chat-Backend/Frontend-Tests |
| Chatpersistenz | `main.py`, Chat-Schemas/Route/Service, `persistence/database.py`, `models.py`, Alembic `0001`–`0004`, Frontend Backend/Hook/Window und Tests |
| Attachments | `models.py`, `attachment_repository.py`, `services/attachments.py`, Alembic `0007`, Attachment-Route/Schemas, Chat-Detail-Route, `backend.ts`/Hook/ChatWindow und Backend-/Frontend-Tests |
| Kontextkompression | `services/context_compression.py`, Chat/Audio-Service, Modelle/Repository/Config, Chat/Audio-Routen und -Schemas, ChatWindow/Hook/backend/types, Kompressions-/Chat-/Audio-Tests |
| Runtime-Vertrag | `runtime/base.py`, `ollama.py`, `llama_cpp.py`, `services/chat.py`, Runtime/Ollama/Integrationstests; Runtime bleibt text-only |
| Ollama oder LLM-Auswahl | `ollama.py`, `config.py`, `state.py`, Commands Factory/Registry/`llm_set.py`, Chat/Main und LLM/State/Ollama/Main-Tests |
| Audio-Chat/Dialog/STT | `audio/capture.py`, `stt/whisper.py`, `services/audio_text_chat.py`, Audio-Call/State, Audio-Route/Router/Schemas, ChatWindow/Hook/backend/types, Audio-/STT-/Dialog-/Frontendtests; bei LLM-Grenze `runtime/base.py`/`ollama.py` |
| Avatar-Feedback | Audio-Service/Route, Frontend Backend/Hook/ChatWindow/AvatarState/CallEvents/Warmup/App/Styles/UIConfig, Audio- und Dialog-/App-Tests |
| TTS | `tts/base.py`, Factory, Kokoro/Chatterbox, TtsService/Route, Config und TTS-Tests; optional reale Integrationen |
| Netzwerk/CORS | `config.py`, `main.py`, Startscript, Frontend `backend.ts`, Config/Health-Tests |
| Principal-Identifikation/HTTP | `main.py`, `mcp/security.py`, API-Principal-Dependency/Wiring, `mcp/server.py`, `services/tool_runner.py`, Workflow-Service/-Runtime-Route, `routes/ui.py`, `frontend/src/uiConfig.ts`, `services/backend.ts`, Principal-/UI-/API-/MCP-/Workflow-Tests |
| Frontend-Chat | ChatWindow, Hook, Backend, Types, Markdown-Komponenten, Links, ChatWindow-Service/Main, Frontendtests, Chat-Schemas/Route |
| Desktop-Shell | Tauri Main/Backend/Config/Icon, Desktop Entry/Installer, Frontend Main/App/ChatWindow/Window-Services/Styles, App-Tests |
| Native Inputregionen | `input_shape.rs`, Tauri Main, Frontend InputShape/App/Styles, App-Tests; Alpha-Regionen/CORS und post-resize Geometrie erhalten |
| MCP/Capabilities | `main.py`, `mcp/server.py`, `mcp/music.py`, `mcp/web.py`, `mcp/workflow.py`, `mcp/content.py`, `services/tool_runner.py`, `authorization`, `persistence/authorization_repository.py`, `services/web_search.py`, `services/workflows.py`, `services/audio_creation.py`, `workflows_config.py`, MusicService/Repository/Playlist/Player, TTS-Adapter, `pyproject.toml`, MCP-/ToolRunner-/Authorization-/Web-/Musik-/Workflow-/Content-Tests, optionale Integrationen/Spikes |
| Workflow-Lifecycle/Progress | `mcp/workflow.py`, `services/tool_runner.py`, `services/workflows.py`, Workflow-Runtime-Route/Schemas, `persistence/models.py`, Chat-/Workflow-Repositories, Alembic-Migration, Chat-Detail-Projektion, `frontend/src/types/chat.ts`, `services/backend.ts`, `ChatWindow.vue`/Workflow-Decorator sowie Workflow-Runtime-/Service-/MCP-/Frontend-Tests |
| Agenten im Chat | `agents_config.py`, `state.py`, `commands/agent.py`, Command-Registry/-Factory, `services/chat.py`, `services/context_compression.py`, `persistence/chat_repository.py`, Agent-/Chat-/Command-/Kompressions-/Authorization-Tests |

## Architekturgrenzen und Status

- Anwendung hängt an `ModelRuntime`, nicht an konkreten Runtimes — `docs/adrs/04-local-llm-runtime.md`.
- Modell, Audio und TTS bleiben im Python-Backend — `docs/adrs/03-backend-fastapi.md`.
- Feste Loopback-Bindung — `docs/adrs/05-loopback-http-communication.md`.
- Nativer Gemma-Audiopfad ist abgelöst: Audio wird lokal mit faster-whisper transkribiert und danach ausschließlich über den text-only `ModelRuntime` verarbeitet. `docs/adrs/06-native-gemma-audio.md` beschreibt damit eine überholte frühere Entscheidung.
- TTS hinter austauschbarem Python-Adapter — `docs/adrs/07-tts-output.md`.
- Dieser Index ist kompakt, nicht autoritativ — `docs/adrs/08-incremental-repo-map-as-ai-working-index.md`.
- Kleine lokale Patches erst nach genauer Quellprüfung, dann Finaldiff/Testreview — `docs/adrs/09-prompt2code-source-patching.md`.
- MCP ist die einheitliche Capability-Grenze; Capability-Verträge, principal-spezifische Discovery und Authorization gelten transportunabhängig. Inter-Process-MCP bleibt erforderlich, ein späterer In-Process-Pfad darf nur eine semantisch und sicherheitsseitig äquivalente Optimierung sein — `docs/adrs/10-mcp-as-unified-capability-interface.md`.
- Implementiert: FastAPI/Health/Streaming-Chat, persistierte Chats/Kompression, abstrakte Conversation-Messages mit Text-/Workflow-Progress-Darstellung, WorkflowExecution-Lifecycle mit Runtime-API/SSE-Invalidierung, text-only Ollama-Runtime, Tauri-Shell/Backend-Lifecycle/Avatar-Interaktion/X11-Input-Shape, Chat-UI/Markdown, PTT/Dialog/Call mit CPU-faster-whisper-STT, MCP-Musik/Websuche/Web-Content/Workflow-Ausführung/Audio-Content-Erzeugung, lokales TTS inkl. Avatar Call read-aloud.
- Verträge/Stubs: llama.cpp-Runtime. Nicht vorhanden: Memory, Production Packaging.
- Offen: finale lokale LLM-Runtime und Chatterbox Ressourcen/Qualität.
