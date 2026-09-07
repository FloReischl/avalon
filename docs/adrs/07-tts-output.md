# ADR 07: Lokale Sprachausgabe mit Chatterbox Multilingual

- Status: Akzeptiert; Spike und erste Read-Aloud-Integration validiert
- Priorität: Nach Textchat und nativem Audioinput
- Datum: 2026-08-26
- Aktualisiert: 2026-09-07

## Kontext

Avalo benötigt eine lokale, möglichst natürliche deutsche Sprachausgabe. Niedrigste Latenz ist weniger wichtig als Natürlichkeit. Die erste produktnahe Nutzung ist das explizite Vorlesen einer abgeschlossenen Assistant-Nachricht; automatische Sprachausgabe im Dialog kann später denselben TTS-Pfad verwenden.

Der TTS-Spike verglich unter anderem Piper, Kikiri/Kokoro und Chatterbox Multilingual. Chatterbox Multilingual V3 lieferte dabei die bevorzugte Sprachqualität.

Avalos primäre Funktion bleibt jedoch das lokale LLM. Auf der Zielhardware mit 8 GB VRAM soll Gemma vollständig auf der GPU resident bleiben. Eine TTS-Lösung muss sich deshalb in den verbleibenden GPU-Speicher einfügen und darf keine LLM-Unload- oder reduzierte LLM-Offload-Strategie voraussetzen.

## Entscheidung

- TTS bleibt hinter dem austauschbaren Python-Contract `TextToSpeech`.
- Die erste integrierte Implementierung verwendet **Chatterbox Multilingual V2 mit 4-Bit-BitsAndBytes-Quantisierung**.
- Die Quantisierungsunterstützung stammt aus einem gepinnten Chatterbox-Fork auf Commit `28dd1e642739c556e9d8728609055ea06bfb99cc`.
- `bitsandbytes` ist auf die im Spike validierte Version `0.50.2` gepinnt.
- Das Chatterbox-Modell wird lazy beim ersten TTS-Aufruf geladen und nach fünf Minuten TTS-Inaktivität wieder entladen. Die Inaktivitätszeit beginnt erst nach Ende der Audiowiedergabe.
- Die erste Konfiguration verwendet genau eine ausgewählte lokale deutsche Referenzstimme.
- Referenzaudio darf nur mit den erforderlichen Nutzungsrechten verwendet werden.
- Ausgabe und Verarbeitung bleiben vollständig lokal; es wird kein Cloud-TTS-Dienst verwendet.
- Read Aloud überträgt Plaintext an das Backend und erhält eine vollständige WAV-Antwort zurück.
- Es gibt keine parallelen TTS-Jobs und keine Queue. Ein neuer Read-Aloud-Vorgang ersetzt eine laufende Wiedergabe.
- Längere Texte werden im Chatterbox-Adapter primär an Satzgrenzen partitioniert. Ein einzelner Satz über ungefähr 300 Zeichen wird bevorzugt an Satzteilgrenzen und anschließend nötigenfalls an Whitespace geteilt. Wörter werden nicht künstlich getrennt.
- Die erzeugten Audio-Chunks werden wieder zu einer vollständigen WAV-Antwort zusammengesetzt.

## Begründung

Chatterbox lieferte im Hörvergleich die für Avalo bevorzugte natürliche deutsche Stimme.

Die zunächst bevorzugte V3-Variante benötigt in der verfügbaren Vollpräzisionsimplementierung zusammen mit dem vollständig auf der GPU residenten Gemma zu viel VRAM. CPU-Synthese war für die gewünschte Interaktion deutlich zu langsam. Eine Reduktion oder ein Unload des LLM wurde verworfen, weil das LLM Avalos primäre Runtime bleibt.

Die verfügbare 4-Bit-Quantisierung basiert auf einem älteren Chatterbox-Stand und verwendet deshalb Multilingual V2. Im realen Spike lag ihr Speicherbedarf deutlich unter der Vollversion und parallele LLM- und TTS-Nutzung funktionierte auf der Zielhardware.

Bei längeren monolithischen TTS-Aufrufen trat trotz Quantisierung erneut GPU-Out-of-Memory auf. Satzorientierte Partitionierung begrenzt den Peak pro Generierung und erzeugt gleichzeitig phonetisch sinnvolle Übergänge.

Die 4-Bit-Ausgabe klingt gegenüber der unquantisierten Variante etwas metallischer. Dieser Qualitätsverlust wird für die erste Avalo-Version bewusst akzeptiert.

## Validierung

Der Spike und die Integration haben bestätigt:

- Chatterbox Multilingual besitzt für Avalo die bevorzugte deutsche Sprachqualität;
- die ausgewählte Referenzstimme funktioniert konsistent;
- Chatterbox V2 mit 4-Bit-Quantisierung kann neben dem vollständig GPU-residenten Gemma betrieben werden;
- längere Read-Aloud-Texte funktionieren mit satzorientiertem Chunking ohne den zuvor beobachteten VRAM-Fehler;
- die reale Chatterbox-Synthese ist durch einen explizit aktivierten GPU-Integrationstest abgedeckt;
- reguläre Tests verwenden keine reale GPU-/500M-Modellinstanz;
- das manuelle End-to-End-Verhalten im Chat einschließlich längerer Nachrichten wurde validiert.

## Konsequenzen

- Das LLM bleibt bei Ressourcenentscheidungen gegenüber TTS priorisiert.
- Die integrierte TTS-Version ist derzeit V2, obwohl V3 im ursprünglichen Qualitäts-Spike bevorzugt wurde.
- Der Quantisierungs-Fork ist eine experimentelle, nicht upstream integrierte Dependency und wird deshalb auf einen konkreten Commit gepinnt.
- Ein späterer Wechsel auf V3 mit geeigneter Quantisierung oder eine andere TTS-Engine bleibt durch den Adapter-Contract möglich.
- Satzpartitionierung ist eine technische Eigenschaft des TTS-Adapters und nicht Bestandteil der Chat- oder Frontend-Logik.
- Spätere Stimmwahl verändert primär Konfiguration und Referenzaudio, nicht die Gesprächslogik.
- Chatterbox versieht erzeugte Audiodaten mit einem nicht hörbaren Herkunftswasserzeichen.

## Alternativen

- Chatterbox Multilingual V3: qualitativ bevorzugt, aber in der derzeit verfügbaren unquantisierten Variante auf der Zielhardware nicht parallel zum vollständig residenten LLM betreibbar.
- Piper: deutlich ressourcenschonender und als Fallback geeignet, im Hörvergleich jedoch nicht erste Wahl bei priorisierter Natürlichkeit.
- Kikiri/Kokoro: im Spike getestet, qualitativ gegenüber Chatterbox nicht bevorzugt.
- XTTS-v2: unterstützt Deutsch, besitzt jedoch eine restriktivere Modelllizenz.

## Quellen

- [Chatterbox GitHub-Repository](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Multilingual](https://www.resemble.ai/learn/models/chatterbox-multilingual)
- [Piper](https://github.com/cdwiegand/piper-tts)
- [XTTS-v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
