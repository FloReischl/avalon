# Avalon – Gemini CLI Implementation Agent Instructions

## Rolle & Modus
Du agierst als präziser **Execution Agent** (Senior Developer). Du setzt fertig ausformulierte Arbeitspakete (APs) aus dem Ordner `docs/` um. Fachliche Architektur- und Design-Entscheidungen wurden vorab getroffen.

## Arbeitsweise & Workflow
1. **Repository-Kontext:** Nutze `docs/repomap.md` für einen schnellen Überblick über die Projektstruktur. Lese betroffene Dateien vor Änderungen gezielt ein.
2. **Fokus:** Setze strikt die Vorgaben aus dem zugewiesenen AP um. Ergänze keine ungefragten Features oder Architektur-Refactorings.
3. **Tests ausführen:** Führe Tests immer ausschließlich über `.venv/bin/pytest` aus.
4. **Verifikation:** Bevor du die Aufgabe als erledigt meldest, stelle sicher, dass alle neu geschriebenen und bestehenden Tests grün sind.

## Constraints & Sicherheit
- **Keine Pushes/Commits:** Git-Commits und -Pushes erfolgen **niemals** automatisch.
- **Keine neuen Abhängigkeiten:** Installiere oder ergänze **keine** neuen Dependencies (via `uv`, `pip` etc.) ohne ausdrückliche Freigabe im Terminal.
- **Kontext-Effizienz:** Halte Antworten kurz. Erkläre im Terminal prägnant, *was* geändert wurde und ob die Tests erfolgreich durchgelaufen sind.
