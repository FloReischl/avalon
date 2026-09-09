# ADR 07: Lokale Sprachausgabe mit austauschbaren TTS-Engines

- Status: Akzeptiert; Kokoro und Chatterbox produktnah validiert
- Priorität: Nach Textchat und nativem Audioinput
- Datum: 2026-08-26
- Aktualisiert: 2026-09-09

## Kontext

Avalo benötigt eine lokale, möglichst natürliche deutsche Sprachausgabe. Niedrigste Latenz ist weniger wichtig als Natürlichkeit. Die erste produktnahe Nutzung ist das explizite Vorlesen einer abgeschlossenen Assistant-Nachricht; automatische Sprachausgabe im Dialog kann später denselben TTS-Pfad verwenden.

Der TTS-Spike verglich unter anderem Piper, Kikiri/Kokoro und Chatterbox Multilingual. Chatterbox Multilingual V3 lieferte dabei die bevorzugte Sprachqualität. Die integrierte 4-Bit-V2-Variante konnte diese Qualität mit geringerem Speicherbedarf verfügbar machen, blieb im praktischen Read-Aloud-Betrieb jedoch deutlich schwergewichtiger und langsamer als Kokoro.

Avalos primäre Funktion bleibt das lokale LLM. Auf der Zielhardware mit 8 GB VRAM soll Gemma vollständig auf der GPU resident bleiben. TTS soll deshalb möglichst wenig zusätzliche Ressourcen binden und darf keine LLM-Unload- oder reduzierte LLM-Offload-Strategie voraussetzen. Da Sprachqualität und Interaktionsgeschwindigkeit je nach Anwendungsfall unterschiedlich gewichtet werden können, bleibt die konkrete TTS-Engine konfigurierbar.

## Entscheidung

- TTS bleibt hinter dem austauschbaren Python-Contract `TextToSpeech`.
- Die konkrete Engine wird beim Backend-Start über Konfiguration und eine kleine Factory ausgewählt. Unbekannte Engine-Namen sind Konfigurationsfehler und verhindern den Backend-Start; es gibt keinen stillen Fallback.
- **Kikiri/Kokoro mit der deutschen Victoria-Stimme ist die Default-Engine.**
- Kokoro verwendet lokale Modell-, Voice- und Config-Artefakte und lädt sie nicht automatisch aus dem Netz nach.
- Bei `tts_device = "auto"` verwendet Kokoro CUDA, sofern verfügbar, andernfalls CPU.
- **Chatterbox Multilingual V2 mit 4-Bit-BitsAndBytes-Quantisierung bleibt als alternative Engine vollständig verfügbar.**
- Die Quantisierungsunterstützung stammt aus einem gepinnten Chatterbox-Fork auf Commit `28dd1e642739c556e9d8728609055ea06bfb99cc`; `bitsandbytes` ist auf `0.50.2` gepinnt.
- Die ausgewählte Engine wird lazy beim ersten TTS-Aufruf geladen und nach fünf Minuten TTS-Inaktivität wieder entladen. Die Inaktivitätszeit beginnt erst nach Ende der Audiowiedergabe.
- Chatterbox verwendet die konfigurierte lokale deutsche Referenzstimme; Kokoro verwendet die konfigurierte Victoria-Stimme.
- Referenzaudio darf nur mit den erforderlichen Nutzungsrechten verwendet werden.
- Ausgabe und Verarbeitung bleiben vollständig lokal; es wird kein Cloud-TTS-Dienst verwendet.
- Read Aloud überträgt Plaintext an das Backend und erhält eine vollständige WAV-Antwort zurück.
- Es gibt keine parallelen TTS-Jobs und keine Queue. Ein neuer Read-Aloud-Vorgang ersetzt eine laufende Wiedergabe.
- Längere Texte werden im Chatterbox-Adapter primär an Satzgrenzen partitioniert. Ein einzelner Satz über ungefähr 300 Zeichen wird bevorzugt an Satzteilgrenzen und anschließend nötigenfalls an Whitespace geteilt. Wörter werden nicht künstlich getrennt.
- Die erzeugten Audio-Chunks werden wieder zu einer vollständigen WAV-Antwort zusammengesetzt.

## Begründung

Chatterbox lieferte im Hörvergleich die für Avalo bevorzugte natürliche deutsche Stimme. Die zunächst bevorzugte V3-Variante benötigt in der verfügbaren Vollpräzisionsimplementierung zusammen mit dem vollständig auf der GPU residenten Gemma jedoch zu viel VRAM. Die verfügbare 4-Bit-Quantisierung auf Basis von Multilingual V2 reduzierte den Speicherbedarf ausreichend, blieb aber vergleichsweise rechenintensiv. CPU-Synthese war für die gewünschte Interaktion deutlich zu langsam.

Kokoro erreicht nicht die bevorzugte Chatterbox-Sprachqualität, benötigt mit dem 82M-Basismodell aber erheblich weniger Ressourcen. Die reale Integration mit der deutschen Victoria-Stimme läuft auf der Zielhardware über CUDA wesentlich flüssiger als Chatterbox und kann neben dem vollständig GPU-residenten Gemma betrieben werden. Für häufige interaktive Sprachausgabe wie Read Aloud überwiegt dieser Laufzeitvorteil den Qualitätsvorsprung von Chatterbox.

Chatterbox bleibt bewusst verfügbar, weil seine höhere Sprachqualität für spätere Anwendungsfälle weiterhin relevant sein kann. Die Engine-Abstraktion erlaubt diese Wahl, ohne `TtsService`, HTTP-Contract oder Frontend an eine konkrete TTS-Implementierung zu koppeln.

Bei längeren monolithischen Chatterbox-Aufrufen trat trotz Quantisierung GPU-Out-of-Memory auf. Die bestehende satzorientierte Partitionierung bleibt deshalb eine Eigenschaft des Chatterbox-Adapters.

## Validierung

Spike, Integrationstests und manuelle Read-Aloud-Nutzung haben bestätigt:

- Chatterbox Multilingual besitzt für Avalo die bevorzugte deutsche Sprachqualität;
- Chatterbox V2 mit 4-Bit-Quantisierung kann neben dem vollständig GPU-residenten Gemma betrieben werden;
- längere Chatterbox-Texte funktionieren mit satzorientiertem Chunking ohne den zuvor beobachteten VRAM-Fehler;
- Kokoro Victoria erzeugt lokal gültige WAV-Ausgabe mit 24 kHz;
- `auto` wählt auf der Zielhardware erfolgreich CUDA;
- Kokoro kann lazy geladen, vollständig entladen und anschließend erneut geladen und verwendet werden;
- Kokoro Read Aloud funktioniert im realen Avalo-UI wesentlich flüssiger als Chatterbox;
- reale TTS-Modelltests bleiben explizit aktivierte Integrationstests; reguläre Unit-Tests laden keine großen Modelle.

## Konsequenzen

- Das LLM bleibt bei Ressourcenentscheidungen gegenüber TTS priorisiert.
- Kokoro Victoria ist die aktuelle Default-Engine und optimiert den normalen interaktiven TTS-Pfad auf geringe Laufzeitkosten.
- Chatterbox V2 bleibt als ressourcenintensivere Alternative mit bevorzugter Sprachqualität verfügbar.
- Der Chatterbox-Quantisierungs-Fork ist eine experimentelle, nicht upstream integrierte Dependency und bleibt deshalb auf einen konkreten Commit gepinnt.
- Engine-Auswahl ist Backend-Konfiguration; ein Runtime- oder UI-Umschalter ist derzeit nicht vorgesehen.
- Kokoro-Modellartefakte liegen lokal außerhalb des Git-Repositories und müssen vor Nutzung vorhanden sein.
- Satzpartitionierung bleibt eine technische Eigenschaft des Chatterbox-Adapters und ist nicht Bestandteil der Chat- oder Frontend-Logik.
- Spätere Engines oder Stimmen verändern primär Adapter und Konfiguration, nicht `TtsService`, Gesprächslogik oder HTTP-Contract.
- Chatterbox versieht erzeugte Audiodaten mit einem nicht hörbaren Herkunftswasserzeichen.

## Alternativen

- Chatterbox Multilingual V2 4-Bit als Default: bessere Sprachqualität, im praktischen Read-Aloud-Betrieb aber deutlich schwergewichtiger und langsamer als Kokoro.
- Chatterbox Multilingual V3: qualitativ bevorzugt, aber in der derzeit verfügbaren unquantisierten Variante auf der Zielhardware nicht parallel zum vollständig residenten LLM betreibbar.
- Piper: deutlich ressourcenschonender, im Hörvergleich jedoch qualitativ klar unter Kokoro und Chatterbox.
- XTTS-v2: unterstützt Deutsch, besitzt jedoch eine restriktivere Modelllizenz.

## Quellen

- [Chatterbox GitHub-Repository](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Multilingual](https://www.resemble.ai/learn/models/chatterbox-multilingual)
- [Piper](https://github.com/cdwiegand/piper-tts)
- [XTTS-v2 Model Card](https://huggingface.co/coqui/XTTS-v2)
