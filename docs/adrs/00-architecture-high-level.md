# Avalon – grobe Architektur

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
avalon/
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

