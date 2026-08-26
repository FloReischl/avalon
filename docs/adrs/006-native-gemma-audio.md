# ADR 006: Nativer Audioinput mit Gemma 4

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

