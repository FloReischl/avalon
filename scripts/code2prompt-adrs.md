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