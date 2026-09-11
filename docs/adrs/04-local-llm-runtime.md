# ADR 04: Lokale LLM-Runtime für Avalo

- Status: Vorgeschlagen; durch Runtime-Spike zu bestätigen
- Datum: 2026-08-26

## Kontext

Avalos primäres Chatmodell ist Gemma 4 E4B. Text und nativer Audioinput sollen nach Möglichkeit über dieselbe lokale Runtime laufen. Ollama unterstützt den Textbetrieb, weist den gewählten Modell-Tag derzeit jedoch nicht verlässlich als Audioeingabe aus.

## Entscheidung

- Bevorzugter Kandidat für Avalo ist aktuelles `llama.cpp` mit CUDA, `llama-server`, Gemma-4-E4B-GGUF und zugehörigem multimodalem Projektor.
- Die Python-Anwendung greift über einen `ModelRuntime`-Adapter zu und kennt keine `llama.cpp`-Details.
- Die Entscheidung wird erst nach einem reproduzierbaren Spike auf der RTX 4060 Laptop GPU mit 8 GB VRAM endgültig angenommen.


## Erfolgskriterien des Spikes

- deutscher Textdialog;
- direkter Audioinput ohne separates STT;
- stabile Python-/HTTP-Anbindung;
- nachweisbare CUDA-Nutzung;
- dokumentierter RAM-/VRAM-Bedarf und Antwortzeiten;
- reproduzierbarer Start mit festgehaltenen Modell- und Runtime-Versionen.

## Konsequenzen

- GGUF und CPU/GPU-Offloading sind für 8 GB VRAM grundsätzlich erprobbar, aber noch nicht als ausreichend nachgewiesen.
- Die experimentelle Audio-Unterstützung ist das größte technische Risiko.
- Bei Scheitern wird eine alternative lokale Runtime geprüft; die Anwendungslogik bleibt durch den Adapter erhalten.

## Quellen

- [`llama.cpp`: Multimodal-Unterstützung](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- [Google: Gemma 4 Audio Understanding](https://ai.google.dev/gemma/docs/capabilities/audio)

