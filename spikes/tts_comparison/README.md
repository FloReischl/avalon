# Lokaler TTS-Vergleich

Einmalig, ausschließlich in Avalos vorhandener virtueller Umgebung:

```bash
./.venv/bin/pip install --upgrade --force-reinstall -r spikes/tts_comparison/requirements.txt
```

Der einzelne Laufbefehl lädt fehlende Modelle in `artifacts/tts-spike/models/` und erzeugt zwölf WAV-Dateien, `report.json` und `hearing-review.md`:

```bash
./.venv/bin/python spikes/tts_comparison/run.py
```

Piper: `de_DE-kerstin-low`, aus dem bei der Konfiguration festgeschriebenen `rhasspy/piper-voices`-Commit. Die konkrete Stimmenlizenz wird als `MODEL_CARD` neben dem Modell gespeichert.

Kikiri/Kokoro: `kikiri-german-victoria` (Victoria Asztaller, synthetisch), Apache-2.0, Modellrevision `ce81e20`. Die verwendete Kikiri-Inferenzquelle ist auf Commit `a12d0410e89841e6f3c09958ae5c072f90ae1d49`, der dafür erforderliche deutsche Misaki-Fork auf `9cda9268309160120fffee216280a9ca83ac4644` festgeschrieben. Die von der Konfiguration referenzierte Kokoro-Basiskonfiguration wird beim ersten Lauf geladen; deren Revision wird im Laufbericht als Downloadzeitpunkt kenntlich gemacht.

Die Auswahl ist kein Qualitätsurteil. Natürlichkeit, Ausdruck und insbesondere die Eignung des erotischen Texts müssen durch Flo per Hörbewertung entschieden werden.

`df_kerstin` wird ausschließlich aus dem von Flo lokal bereitgestellten Voicepack geladen. Der Laufbericht hält dessen SHA-256 fest. Weil keine externe Herkunft oder Lizenz vorliegt, wird beides bewusst als unbekannt dokumentiert.

Chatterbox Multilingual V3 nutzt `data/chatterbox-frieda1.wav` als lokale Referenzstimme. Flo hat deren Verwendung, einschließlich des erotischen Testtexts, bestätigt. Das Modell wird pro Spike-Lauf genau einmal geladen; die drei Chatterbox-Renderzeiten enthalten daher keinen Modellstart.
