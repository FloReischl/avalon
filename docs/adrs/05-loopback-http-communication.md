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
- Bevor Avalon zustandsändernde Werkzeuge erhält, muss der Schutz der lokalen API neu bewertet werden.

## Verworfene Alternativen

- Dynamischer Port: erfordert zusätzliche Portübergabe und Discovery.
- Tauri-Commands für sämtliche Backend-Aufrufe: stärkere Kopplung an Rust und schlechtere isolierte Testbarkeit.
- WebSocket von Beginn an: für vollständige Textantworten unnötige Komplexität.

