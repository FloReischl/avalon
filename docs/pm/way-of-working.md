# Way of Working: AI Augmented Engineering

## 1. Zweck

Avalon verfolgt zwei gleichwertige Ziele:

1. Entwicklung einer nutzbaren Anwendung.
2. Praktischer Kompetenzaufbau in AI Augmented Engineering.

Avalon wird genutzt, um einen AI-unterstützten Engineering-Prozess praktisch zu erproben und weiterzuentwickeln. Requirements Engineering, Architektur, Testkonzept, Implementierung und Review werden dabei bewusst getrennt und je nach Arbeitspaket mit dem dafür geeigneten Werkzeug unterstützt.

## 2. Verantwortung und Rollen

Flo und ein Frontier Modell tragen die fachliche und technische Verantwortung für Anforderungen und Architektur gemeinsam. Das Frontier liefert keine unfehlbaren Vorgaben, sondern begründete Empfehlungen, Alternativen, Risiken und erkennbare Unsicherheiten. Flo entscheidet final.

Frontier und Flo legen vor der Umsetzung Ziel, relevante Architekturentscheidungen, Fehlerverhalten, Akzeptanzkriterien und Testbedarf fest. Fehlende oder widersprüchliche Vorgaben werden vor der Umsetzung geklärt.

## 3. Ablauf

### 3.1 Requirements Engineering

Neue Funktionalitäten werden zuerst fachlich besprochen. Frontier klärt insbesondere Ziel, Nutzerwirkung, Abgrenzung, relevante Fehlerfälle und Akzeptanzkriterien.

Wenn wesentliche Informationen fehlen, erfolgt ein kurzes Interview:

- immer nur eine Frage gleichzeitig;
- so wenige Fragen wie sinnvoll;
- so viele Fragen wie aufgrund von Komplexität oder Risiko notwendig;
- Annahmen werden ausdrücklich kenntlich gemacht.

Ergebnis ist ein gemeinsames, implementierbares Verständnis der Funktionalität.

### 3.2 Architektur

Frontier und Flo diskutieren geeignete Lösungsoptionen und deren Konsequenzen. Berücksichtigt werden nur für die Entscheidung relevante Aspekte, beispielsweise Komplexität, Wartbarkeit, Testbarkeit, Datenhaltung, Abhängigkeiten und spätere Erweiterbarkeit.

Eine langfristig bedeutsame oder schwer rückgängig zu machende Entscheidung kann in einem Architecture Decision Record dokumentiert werden. Ein ADR wird nicht für triviale Implementierungsdetails angelegt.

### 3.3 Testkonzept

Vor der Implementierung werden prüfbare Akzeptanzkriterien und sinnvolle Tests festgelegt:

- Unit-Tests für isolierte Fachlogik und relevante Randfälle;
- Integrationstests für das Zusammenspiel von Komponenten und externe Grenzen;
- bei Bedarf manuelle Prüfschritte für Verhalten, das nicht wirtschaftlich automatisierbar ist.

Die Tests sollen Risiken abdecken und nicht lediglich Implementierungsdetails spiegeln.

### 3.4 Arbeitspakete und Implementierung

Nach Abschluss von Requirements Engineering, Architektur und Testkonzept zerlegt Frontier die Umsetzung in kleine, klar prüfbare Arbeitspakete. Ein Paket soll möglichst genau ein kohärentes Ergebnis erzeugen.

Für kleine und deterministische Änderungen kann Frontier auf Basis der aktuellen relevanten Quelldateien einen Prompt2Code-Patch erzeugen. Flo wendet den Patch an und führt die vereinbarte Verifikation aus.

Benötigt ein Arbeitspaket breite Repository-Exploration, umfangreiche oder stark verteilte Änderungen, interaktives Debugging oder größere Implementierungsautonomie, kann es gezielt an einen repository-aware Coding-Agenten übergeben werden.

Der Implementierungsweg ändert nichts an der Entscheidungsgrenze: Produkt- und relevante Architekturentscheidungen werden vor der Umsetzung geklärt. Bei fehlenden oder widersprüchlichen Grundlagen wird nicht geraten.

### 3.5 Review und Freigabe

Nach jedem Paket werden mindestens folgende Punkte geprueft:

- Diff und Umfang entsprechen dem Auftrag;
- Akzeptanzkriterien sind erfüllt;
- vereinbarte Tests existieren und laufen erfolgreich;
- keine unbeabsichtigten Architektur- oder Abhängigkeitsänderungen wurden eingeführt;
- Annahmen, verbleibende Risiken und ungetestete Aspekte sind sichtbar.

Erst danach folgt das nächste Paket. Commits oder externe Änderungen erfolgen nur auf ausdrücklichen Auftrag von Flo.

## 4. Technischer Ausgangspunkt

- Betriebssystem: Linux
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU mit 8 GB VRAM
- Arbeitsspeicher: 32 GB RAM
- deterministischer Patch-Transport für geeignete Änderungen: Prompt2Code
- repository-aware Coding-Agenten werden bei Bedarf gezielt eingesetzt

Diese Werte beschreiben den aktuellen Ausgangspunkt und können nach gemessenen Erfahrungen angepasst werden.
