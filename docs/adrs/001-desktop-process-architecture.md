# ADR 001: Desktop- und Prozessarchitektur

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

