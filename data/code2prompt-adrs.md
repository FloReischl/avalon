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
└── 09-prompt2code-source-patching.md

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
# ADR 07: Lokale Sprachausgabe mit austauschbaren TTS-Engines

- Status: Akzeptiert; Kokoro und Chatterbox produktnah validiert
- Priorität: Nach Textchat und nativem Audioinput
- Datum: 2026-08-26
- Aktualisiert: 2026-09-09

## Kontext

Avalo benötigt eine lokale, möglichst natürliche deutsche Sprachausgabe. Niedrigste Latenz ist weniger wichtig als Natürlichkeit. Die erste produktnahe Nutzung ist das explizite Vorlesen einer abgeschlossenen Assistant-Nachricht; automatische Sprachausgabe im Dialog kann später denselben TTS-Pfad verwenden.

Der TTS-Spike verglich unter anderem Piper, Kikiri/Kokoro und Chatterbox Multilingual. Chatterbox Multilingual V3 lieferte dabei die bevorzugte Sprachqualität. Die integrierte 4-Bit-V2-Variante konnte diese Qualität mit geringerem Speicherbedarf verfügbar machen, blieb im praktischen Read-Aloud-Betrieb jedoch deutlich schwergewichtiger und langsamer als Kokoro.

Avalos primäre Funktion bleibt das lokale LLM. Auf der Zielhardware mit 8 GB VRAM soll Gemma vollständig auf der GPU resident bleiben. TTS soll deshalb möglichst wenig zusätzliche Ressourcen binden und darf keine LLM-Unload- oder reduzierte LLM-Offload-Strategie voraussetzen. Da Sprachqualität und Interaktionsgeschwindigkeit je nach Anwendungsfall unterschiedlich gewichtet werden können, bleibt die konkrete TTS-Engine konfigurierbar.

## Entscheidung

- TTS bleibt hinter dem austauschbaren Python-Contract `TextToSpeech`.
- Die konkrete Engine wird beim Backend-Start über Konfiguration und eine kleine Factory ausgewählt. Unbekannte Engine-Namen sind Konfigurationsfehler und verhindern den Backend-Start; es gibt keinen stillen Fallback.
- **Kikiri/Kokoro mit der deutschen Victoria-Stimme ist die Default-Engine.**
- Kokoro verwendet lokale Modell-, Voice- und Config-Artefakte und lädt sie nicht automatisch aus dem Netz nach.
- Bei `tts_device = "auto"` verwendet Kokoro CUDA, sofern verfügbar, andernfalls CPU.
- **Chatterbox Multilingual V2 mit 4-Bit-BitsAndBytes-Quantisierung bleibt als alternative Engine vollständig verfügbar.**
- Die Quantisierungsunterstützung stammt aus einem gepinnten Chatterbox-Fork auf Commit `28dd1e642739c556e9d8728609055ea06bfb99cc`; `bitsandbytes` ist auf `0.50.2` gepinnt.
- Die ausgewählte Engine wird lazy beim ersten TTS-Aufruf geladen und nach fünf Minuten TTS-Inaktivität wieder entladen. Die Inaktivitätszeit beginnt erst nach Ende der Audiowiedergabe.
- Chatterbox verwendet die konfigurierte lokale deutsche Referenzstimme; Kokoro verwendet die konfigurierte Victoria-Stimme.
- Referenzaudio darf nur mit den erforderlichen Nutzungsrechten verwendet werden.
- Ausgabe und Verarbeitung bleiben vollständig lokal; es wird kein Cloud-TTS-Dienst verwendet.
- Read Aloud überträgt Plaintext an das Backend und erhält eine vollständige WAV-Antwort zurück.
- Es gibt keine parallelen TTS-Jobs und keine Queue. Ein neuer Read-Aloud-Vorgang ersetzt eine laufende Wiedergabe.
- Längere Texte werden im Chatterbox-Adapter primär an Satzgrenzen partitioniert. Ein einzelner Satz über ungefähr 300 Zeichen wird bevorzugt an Satzteilgrenzen und anschließend nötigenfalls an Whitespace geteilt. Wörter werden nicht künstlich getrennt.
- Die erzeugten Audio-Chunks werden wieder zu einer vollständigen WAV-Antwort zusammengesetzt.

## Begründung

Chatterbox lieferte im Hörvergleich die für Avalo bevorzugte natürliche deutsche Stimme. Die zunächst bevorzugte V3-Variante benötigt in der verfügbaren Vollpräzisionsimplementierung zusammen mit dem vollständig auf der GPU residenten Gemma jedoch zu viel VRAM. Die verfügbare 4-Bit-Quantisierung auf Basis von Multilingual V2 reduzierte den Speicherbedarf ausreichend, blieb aber vergleichsweise rechenintensiv. CPU-Synthese war für die gewünschte Interaktion deutlich zu langsam.

Kokoro erreicht nicht die bevorzugte Chatterbox-Sprachqualität, benötigt mit dem 82M-Basismodell aber erheblich weniger Ressourcen. Die reale Integration mit der deutschen Victoria-Stimme läuft auf der Zielhardware über CUDA wesentlich flüssiger als Chatterbox und kann neben dem vollständig GPU-residenten Gemma betrieben werden. Für häufige interaktive Sprachausgabe wie Read Aloud überwiegt dieser Laufzeitvorteil den Qualitätsvorsprung von Chatterbox.

Chatterbox bleibt bewusst verfügbar, weil seine höhere Sprachqualität für spätere Anwendungsfälle weiterhin relevant sein kann. Die Engine-Abstraktion erlaubt diese Wahl, ohne `TtsService`, HTTP-Contract oder Frontend an eine konkrete TTS-Implementierung zu koppeln.

Bei längeren monolithischen Chatterbox-Aufrufen trat trotz Quantisierung GPU-Out-of-Memory auf. Die bestehende satzorientierte Partitionierung bleibt deshalb eine Eigenschaft des Chatterbox-Adapters.

## Validierung

Spike, Integrationstests und manuelle Read-Aloud-Nutzung haben bestätigt:

- Chatterbox Multilingual besitzt für Avalo die bevorzugte deutsche Sprachqualität;
- Chatterbox V2 mit 4-Bit-Quantisierung kann neben dem vollständig GPU-residenten Gemma betrieben werden;
- längere Chatterbox-Texte funktionieren mit satzorientiertem Chunking ohne den zuvor beobachteten VRAM-Fehler;
- Kokoro Victoria erzeugt lokal gültige WAV-Ausgabe mit 24 kHz;
- `auto` wählt auf der Zielhardware erfolgreich CUDA;
- Kokoro kann lazy geladen, vollständig entladen und anschließend erneut geladen und verwendet werden;
- Kokoro Read Aloud funktioniert im realen Avalo-UI wesentlich flüssiger als Chatterbox;
- reale TTS-Modelltests bleiben explizit aktivierte Integrationstests; reguläre Unit-Tests laden keine großen Modelle.

## Konsequenzen

- Das LLM bleibt bei Ressourcenentscheidungen gegenüber TTS priorisiert.
- Kokoro Victoria ist die aktuelle Default-Engine und optimiert den normalen interaktiven TTS-Pfad auf geringe Laufzeitkosten.
- Chatterbox V2 bleibt als ressourcenintensivere Alternative mit bevorzugter Sprachqualität verfügbar.
- Der Chatterbox-Quantisierungs-Fork ist eine experimentelle, nicht upstream integrierte Dependency und bleibt deshalb auf einen konkreten Commit gepinnt.
- Engine-Auswahl ist Backend-Konfiguration; ein Runtime- oder UI-Umschalter ist derzeit nicht vorgesehen.
- Kokoro-Modellartefakte liegen lokal außerhalb des Git-Repositories und müssen vor Nutzung vorhanden sein.
- Satzpartitionierung bleibt eine technische Eigenschaft des Chatterbox-Adapters und ist nicht Bestandteil der Chat- oder Frontend-Logik.
- Spätere Engines oder Stimmen verändern primär Adapter und Konfiguration, nicht `TtsService`, Gesprächslogik oder HTTP-Contract.
- Chatterbox versieht erzeugte Audiodaten mit einem nicht hörbaren Herkunftswasserzeichen.

## Alternativen

- Chatterbox Multilingual V2 4-Bit als Default: bessere Sprachqualität, im praktischen Read-Aloud-Betrieb aber deutlich schwergewichtiger und langsamer als Kokoro.
- Chatterbox Multilingual V3: qualitativ bevorzugt, aber in der derzeit verfügbaren unquantisierten Variante auf der Zielhardware nicht parallel zum vollständig residenten LLM betreibbar.
- Piper: deutlich ressourcenschonender, im Hörvergleich jedoch qualitativ klar unter Kokoro und Chatterbox.
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
`09-prompt2code-source-patching.md`:

```md
# ADR 09: Deterministic Source Patching via Prompt2Code

**Status:** Accepted  
**Date:** 2026-09-01

## Context

Avalo uses frontier-model-assisted planning and local implementation workflows.

For some implementation tasks, the generated source changes are sufficiently small and deterministic that a coding agent is unnecessary. In these cases, the required operation is primarily the reliable transport of explicitly specified source changes into the local repository.

Prompt2Code (`prompt2code.py`) provides this transport layer.

An earlier version used YAML patch files. Source snippets were embedded as YAML block scalars and then applied through deterministic operations.

While functional, YAML introduced unnecessary complexity for exact source transport:

- YAML indentation and source-code indentation interacted.
- Block scalar semantics affected trailing newlines.
- Exact source snippets required YAML-specific formatting such as `|2-`.
- LLM-generated patches therefore had to satisfy both YAML syntax and source-code whitespace requirements.

Prompt2Code does not require a general-purpose serialization format. Its patch format only needs to express a small set of deterministic source operations.

## Decision

Prompt2Code uses a minimal custom text format designed specifically for exact source transport.

It intentionally provides no general-purpose syntax, quoting, escaping, comments, indentation handling, fuzzy matching, or code intelligence.

### Patch Structure

A patch contains one or more sequential changes.

Each change starts with exactly two header lines:

```text
<relative-file-path>
<mode>
```

Supported modes are:

```text
string-replace
string-remove
file-create
file-delete
```

Mode names are case-sensitive and whitespace-exact.

Changes are separated by the exact marker line:

```text
p2c-next-change
```

The separator must occur between two complete changes. It is invalid at the beginning or end of a patch, and consecutive separators are invalid.

### string-replace

```text
backend/app/main.py
string-replace
p2c-old
<exact old payload>
p2c-new
<exact new payload>
```

Both payloads are required and must be non-empty.

By default, the `p2c-old` payload must occur exactly once in the current simulated file content.

For repeated identical matches, an optional selector may be specified directly after `string-replace` and before `p2c-old`:

```text
p2c-position: N
```

selects exactly the N-th occurrence, using 1-based indexing.

Alternatively:

```text
p2c-count: N
```

requires exactly N occurrences and replaces all of them.

`p2c-position` and `p2c-count` are mutually exclusive. Both values must be positive integers.

If neither selector is present, the existing exactly-once behavior applies.

Any selector or match-count validation failure aborts the complete patch before any filesystem changes are made.

### string-remove

```text
backend/app/main.py
string-remove
p2c-old
<exact old payload>
```

The payload is required and must be non-empty.

By default, the payload must occur exactly once in the current simulated file content.

The same optional selectors as for `string-replace` are supported directly after `string-remove` and before `p2c-old`:

- `p2c-position: N` removes exactly the N-th occurrence, using 1-based indexing.
- `p2c-count: N` requires exactly N occurrences and removes all of them.

`p2c-position` and `p2c-count` are mutually exclusive. Both values must be positive integers.

If neither selector is present, the existing exactly-once behavior applies.

### file-create

```text
backend/app/new_module.py
file-create
p2c-new
<complete file content>
```

The payload is required and must be non-empty.

The target file must not already exist in the current simulated state.

Missing parent directories are created during the write phase.

### file-delete

```text
backend/app/obsolete.py
file-delete
```

The target must exist as a regular file in the current simulated state.

`file-delete` has no payload.

### Payload Semantics

Payload is transported without interpretation.

Indentation, blank lines, and other whitespace are significant.

The newline immediately separating a payload from a following marker is structural and is not part of the payload. Additional newlines before the marker are payload.

At EOF, all remaining content after the payload marker belongs to the payload, including a final newline when present.

For example:

```text
p2c-new
def foo():
    return 2
p2c-next-change
```

does not include a newline after `return 2`.

To include one:

```text
p2c-new
def foo():
    return 2

p2c-next-change
```

The patch format uses UTF-8 and LF (`\n`) line endings.

### Reserved Marker Lines

The following exact lines have structural meaning:

```text
p2c-old
p2c-new
p2c-next-change
```

There is intentionally no escaping or quoting mechanism for representing conflicting marker lines inside payload.

If such a collision becomes a real use case, the format can be extended then.

### Path Safety

All patch paths are interpreted relative to `--target-dir`.

Paths are resolved using `pathlib`, including symlink resolution.

The resolved target must remain inside the resolved `--target-dir`.

Any path escaping the target directory aborts the patch.

This applies to direct traversal such as:

```text
../outside.py
```

and to paths escaping through symlinks.

Prompt2Code operates only on regular files. `file-delete` never deletes directories.

### Simulation and Write Model

Changes are processed sequentially.

Multiple changes may target the same file. Each change sees the simulated result of all preceding changes.

Prompt2Code performs two phases:

1. Parse, validate, and simulate the complete patch in memory.
2. Write the final state of each affected file to disk.

No filesystem changes, including creation of parent directories, occur before the complete patch has successfully passed simulation.

Each affected file is written at most once using its final simulated state.

This provides deterministic pre-write validation without implementing a transactional filesystem.

If an I/O error occurs after the write phase has started, Prompt2Code aborts but does not attempt rollback or compensation. Already written changes remain.

### Diagnostics

Errors identify the relative path and global change number:

```text
❌ Patch aborted: [backend/app/main.py] change #3: <reason>
```

For failed exact-match validation, the complete `p2c-old` payload is included unchanged:

```text
❌ Patch aborted: [frontend/src/App.vue] change #1: string-remove expected p2c-old to occur exactly once, found 7

p2c-old:
<span
```

Successful execution reports the final result once per affected file using relative paths:

```text
✅ Modified: frontend/src/App.vue
✅ Created: backend/app/foo.py
✅ Deleted: backend/app/obsolete.py

🎉 Done! 3 file(s) processed successfully.
```

## Guardrails

Prompt2Code deliberately does not provide:

- fuzzy source matching,
- automatic indentation adjustment,
- code or AST interpretation,
- implicit mode correction,
- case-insensitive syntax,
- comments in the patch structure,
- partial application after validation failure,
- filesystem rollback after write failure,
- marker escaping,
- binary-file support.

Invalid or ambiguous input fails instead of being interpreted heuristically.

## Verification

The implementation is covered by a small regression suite for the behavior that is critical to the transport layer:

- multiline `string-replace`,
- `string-remove`,
- positional selection of repeated matches,
- exact-count replacement/removal of repeated matches,
- rejection of combined `p2c-position` and `p2c-count`,
- preservation of default exactly-once behavior,
- `file-create` including parent-directory creation,
- `file-delete`,
- sequential changes to the same file,
- no writes when a later change fails validation,
- target-directory escape protection.

The suite is intentionally small. Prompt2Code is a development helper, not an operational application component.

## Consequences

### Positive

- Source indentation and whitespace no longer interact with YAML syntax.
- Patch generation requires very little formatting knowledge from an LLM.
- Exact source changes remain deterministic and fail fast.
- Sequential changes allow later operations to depend on earlier simulated changes.
- Complete pre-write simulation prevents partially applied patches caused by validation failures.
- `--target-dir` forms a filesystem safety boundary.
- The implementation has no YAML dependency.

### Negative

- The format is intentionally specialized and not compatible with generic YAML/JSON tooling.
- Exact reserved marker lines cannot currently be represented inside payload.
- Exact-match operations remain sensitive to stale source context.
- Filesystem errors during the write phase can leave a partially written patch because rollback is intentionally not implemented.

## Rationale

Prompt2Code is not intended to understand or edit source code intelligently.

Its responsibility is narrower:

> Transport explicitly specified source changes into a repository as deterministically and transparently as possible.

Keeping the patch language minimal reduces both implementation complexity and the probability that an LLM-generated patch fails because of transport-format details unrelated to the source change itself.

Additional syntax or intelligence should only be introduced in response to demonstrated requirements.

```