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

