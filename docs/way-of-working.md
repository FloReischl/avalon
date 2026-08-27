# Way of Working: AI Augmented Engineering

## 1. Zweck

Avalo verfolgt zwei gleichwertige Ziele:

1. Entwicklung einer nutzbaren Anwendung.
2. Praktischer Kompetenzaufbau in AI Augmented Engineering.

Nach Projekterfahrung mit GHC und Codex wird Avalo genutzt, um Aider als Command-Line-Agent mit einem lokal betriebenen Coding-LLM zu erproben. Als Implementierungsmodell dient zunächst `qwen2.5-coder:14b-instruct` über Ollama.

## 2. Verantwortung und Rollen

Flo und Codex tragen die fachliche und technische Verantwortung für Anforderungen und Architektur gemeinsam. Codex liefert keine unfehlbaren Vorgaben, sondern begründete Empfehlungen, Alternativen, Risiken und erkennbare Unsicherheiten. Flo entscheidet final.

Aider mit Qwen ist der ausführende Implementierungsagent. Das Modell trifft keine eigenständigen Produkt- oder Grundsatzentscheidungen. Fehlende oder widersprüchliche Vorgaben werden vor der Umsetzung geklärt.

## 3. Ablauf

### 3.1 Requirements Engineering

Neue Funktionalitäten werden zuerst fachlich besprochen. Codex klärt insbesondere Ziel, Nutzerwirkung, Abgrenzung, relevante Fehlerfälle und Akzeptanzkriterien.

Wenn wesentliche Informationen fehlen, erfolgt ein kurzes Interview:

- immer nur eine Frage gleichzeitig;
- so wenige Fragen wie sinnvoll;
- so viele Fragen wie aufgrund von Komplexität oder Risiko notwendig;
- Annahmen werden ausdrücklich kenntlich gemacht.

Ergebnis ist ein gemeinsames, implementierbares Verständnis der Funktionalität.

### 3.2 Architektur

Codex und Flo diskutieren geeignete Lösungsoptionen und deren Konsequenzen. Berücksichtigt werden nur für die Entscheidung relevante Aspekte, beispielsweise Komplexität, Wartbarkeit, Testbarkeit, Datenhaltung, Abhängigkeiten und spätere Erweiterbarkeit.

Eine langfristig bedeutsame oder schwer rückgängig zu machende Entscheidung kann in einem Architecture Decision Record dokumentiert werden. Ein ADR wird nicht für triviale Implementierungsdetails angelegt.

### 3.3 Testkonzept

Vor der Implementierung werden prüfbare Akzeptanzkriterien und sinnvolle Tests festgelegt:

- Unit-Tests für isolierte Fachlogik und relevante Randfälle;
- Integrationstests für das Zusammenspiel von Komponenten und externe Grenzen;
- bei Bedarf manuelle Prüfschritte für Verhalten, das nicht wirtschaftlich automatisierbar ist.

Die Tests sollen Risiken abdecken und nicht lediglich Implementierungsdetails spiegeln.

### 3.4 Arbeitspakete für Aider

Nach Abschluss von Requirements Engineering, Architektur und Testkonzept zerlegt Codex die Umsetzung in kleine, für `qwen2.5-coder:14b-instruct` beherrschbare Pakete. Ein Paket soll möglichst genau ein klar prüfbares Ergebnis erzeugen.

Jeder kopierfertige Aider-Prompt enthält:

1. notwendigen Projektkontext;
2. konkretes Ziel;
3. erlaubten und ausgeschlossenen Umfang;
4. relevante Dateien oder zuerst zu untersuchende Bereiche;
5. erforderliche Unit- oder Integrationstests;
6. auszuführende Verifikation;
7. eindeutige Fertig-Kriterien;
8. die Aufforderung, bei widersprüchlichen oder fehlenden Grundlagen nicht zu raten.

Aider erhält eigene, paketbezogene Anweisungen. Die Codex-Regeln aus `AGENTS.md` werden nicht ungeprüft als Aider-Prompt wiederverwendet.

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
- lokales Modell: `qwen2.5-coder:14b-instruct`
- Modellserver: Ollama
- Implementierungsagent: Aider 0.86.2
- vorgesehene Kontextgröße: 16.384 Tokens

Diese Werte beschreiben den aktuellen Ausgangspunkt und können nach gemessenen Erfahrungen angepasst werden.
