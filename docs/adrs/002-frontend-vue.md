# ADR 002: Frontend mit Vue 3

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

