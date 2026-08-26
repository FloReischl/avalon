# ADR 007: Lokale Sprachausgabe mit Chatterbox Multilingual

- Status: Vorgeschlagen; durch TTS-Spike zu bestätigen
- Priorität: Nach Textchat und nativem Audioinput
- Datum: 2026-08-26

## Kontext

Avalo benötigt später eine lokale, möglichst natürliche deutsche Stimme. Niedrigste Latenz ist weniger wichtig als Natürlichkeit. Eine Stimme soll grundsätzlich auswählbar sein; eine Laufzeit-Stimmenverwaltung ist zunächst nicht erforderlich.

## Entscheidung

- Bevorzugter TTS-Kandidat ist **Chatterbox Multilingual V3** von Resemble AI.
- TTS wird über einen austauschbaren Python-Adapter angebunden.
- Die erste Konfiguration verwendet genau eine ausgewählte deutsche Referenzstimme.
- Referenzaudio darf nur mit den erforderlichen Nutzungsrechten verwendet werden.
- Ausgabe bleibt lokal; es wird kein Cloud-TTS-Dienst benötigt.
- Ein Spike entscheidet vor der Integration über Qualität, Latenz und Ressourcenstrategie.

## Begründung

- Deutsch wird offiziell unterstützt.
- Das Modell zielt auf natürliche, dialogartige und expressive Sprache.
- Lokale Python-Nutzung und Zero-Shot-Stimmkonditionierung werden unterstützt.
- Code und Modelle stehen laut Anbieter unter MIT-Lizenz.
- Die 500M-Architektur ist wesentlich kleiner als Avalos LLM, konkurriert aber dennoch um GPU-Speicher.

## Erfolgskriterien des Spikes

- natürliche deutsche Aussprache und Satzmelodie anhand festgelegter Hörbeispiele;
- konsistente Stimme über mehrere Antworten;
- keine auffälligen Auslassungen, Wiederholungen oder Halluzinationen;
- gemessene Start- und Synthesezeit;
- dokumentierter RAM-/VRAM-Bedarf im Zusammenspiel mit der LLM-Runtime;
- geprüfte Lizenz der konkreten Modellversion und Rechte am Referenzaudio.

## Konsequenzen

- LLM und TTS müssen auf 8 GB VRAM voraussichtlich koordiniert oder teilweise über CPU/RAM betrieben werden; die genaue Strategie bleibt Ergebnis des Spikes.
- Spätere Stimmwahl verändert nur Konfiguration und Referenzaudio, nicht die Gesprächslogik.
- Chatterbox versieht erzeugte Audiodaten mit einem nicht hörbaren Herkunftswasserzeichen.

## Alternativen

- Piper: deutlich ressourcenschonender und als Fallback geeignet, aber nicht erste Wahl bei priorisierter Natürlichkeit.
- XTTS-v2: unterstützt Deutsch, besitzt jedoch eine restriktivere Modelllizenz.

## Quellen

- [Chatterbox GitHub-Repository](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Multilingual](https://www.resemble.ai/learn/models/chatterbox-multilingual)
- [Piper](https://github.com/cdwiegand/piper-tts)
- [XTTS-v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
