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
./scripts/xstart-backend.sh
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
