# Avalon – Letter of Intent

## Absicht

Avalon soll eine lokal betriebene Companion- und Assistant-Anwendung werden, deren Kern ein lokales Large Language Model bildet. Ziel ist eine deutlich natürlichere und persönlichere Interaktion als bei einem klassischen textbasierten Chatbot, bei zugleich weitgehender Unabhängigkeit von Cloud-Diensten.

Der Projektname **Avalon** leitete sich ursprünglich von „Avatar Local“ ab. Heute "Augmented Virtual Assistant, Local/Offline", wird aber nicht Capital Case.

## Produktvision

Avalon verbindet langfristig mehrere Formen der Interaktion zu einem zusammenhängenden lokalen Erlebnis:

- klassischen Text-Chat;
- kontinuierliche beziehungsweise möglichst natürliche Sprachinteraktion;
- nativen Audio-Input für geeignete multimodale Modelle, sofern dies technisch sinnvoll ist;
- Text-to-Speech für die Sprachausgabe;
- persistenten Gesprächskontext und ein später erweiterbares Memory;
- visuelle Companions oder Characters;
- vorbereitete Bilder, GIFs oder kurze Videos zur Darstellung von Emotionen;
- Auswahl der Character-Darstellung anhand strukturierter Emotion-Tags aus dem Gespräch;
- perspektivisch proaktives Verhalten des Companions.

Die visuelle Darstellung soll langfristig auch als weitgehend rahmenloser Character direkt auf dem Desktop möglich sein.

## Grundsätze

Avalon wird nach folgenden Leitgedanken entwickelt:

1. **Local First:** Verarbeitung und Modelle sollen nach Möglichkeit lokal betrieben werden.
2. **Natürliche Interaktion:** Sprache, Text und visuelle Reaktionen sollen sich zu einer möglichst flüssigen Kommunikation ergänzen.
3. **Schrittweise Entwicklung:** Komplexe Fähigkeiten werden nicht vorweggenommen, sondern iterativ auf einer funktionierenden Basis aufgebaut.
4. **Technische Offenheit:** Vorgesehene Werkzeuge sind Ausgangspunkte und werden anhand praktischer Erfahrungen bewertet.

## Erster Entwicklungsschritt

Der erste Schritt bleibt bewusst klein: Es entsteht ein funktionierender lokaler Chat mit Text- und Audio-Kommunikation.

Memory, Agentenfunktionen, proaktives Verhalten und aufwendigere Character-Funktionen sind nicht Bestandteil dieses ersten Schritts. Sie sollen später auf Grundlage der gewonnenen Erfahrungen ergänzt werden.

## Technischer Ausgangspunkt

Als lokale LLM-Laufzeit ist zunächst Ollama vorgesehen. Ein bereits lokal vorhandenes Gemma-4-Modell dient als Ausgangspunkt. Für die Desktop-Oberfläche wird Tauri als möglicher Kandidat betrachtet, insbesondere wegen der Verbindung von Web-Technologien mit nativen Desktop-Fähigkeiten.

Diese Festlegungen beschreiben den aktuellen Ausgangspunkt, aber noch keine abschließende Architekturentscheidung. Engineering-Workflow, Architektur, Design, MVP-Abgrenzung und konkrete Funktionalitäten werden separat erarbeitet und dokumentiert.
