# Feature-Konzept: Dynamischer Web-Zugriff (Internet-Recherche) für Avalon

## 1. Ziel & Nutzerwirkung
Avalon soll Fragen zu aktuellen Ereignissen (z. B. „Was ist am Wochenende im Olympiapark München geboten?“) oder zu neuen Technologien dynamisch beantworten können, indem aktuelle Informationen aus dem Internet nachgeladen werden.

---

## 2. Architekturentscheidungen & Lösungsoptionen

### Option A: Native Tool / Function Calling via Ollama (Empfohlen)
* **Ablauf:**
  1. Das Python-Backend übergibt Ollama beim Chat-Request Definitionen von verfügbaren Werkzeugen (z. B. `web_search(query: str)`).
  2. Gemma / das gewählte Modell entscheidet autonom, wenn lokales Wissen nicht ausreicht, und gibt einen Tool-Call zurück.
  3. Das Avalon-Backend führt die Suche aus und sendet die Ergebnisse als Werkzeug-Antwort zurück an Ollama.
  4. Ollama generiert die finale Antwort an den Nutzer.
* **Vorteile:**
  * Fügt sich nahtlos in die bestehende `OllamaRuntime` und die `ChatService`-Architektur ein.
  * Das Modell entscheidet selbstständig, wann eine Suche notwendig ist.
* **Voraussetzung:**
  * Das genutzte Ollama-Modell unterstützt Tool-Calling.

### Option B: MCP (Model Context Protocol) Werkzeug
* **Ablauf:**
  * Bereitstellung des Web-Search-Tools als MCP-Server/Tool (analog zur bestehenden `music.play_tracks`-Integration).
* **Vorteile:**
  * Klare Kapselung und Wiederverwendbarkeit über das MCP-Protokoll.

---

## 3. Randbedingungen & Fehlerbehandlung
* **Netzwerk-/Offline-Fallback:** Ist keine Internetverbindung vorhanden oder schlägt die Suche fehl, darf der Chat nicht blockieren oder abstürzen. Avalon muss die Fehlfunktion abfangen und transparent informieren.
* **Timeouts:** Web-Suchanfragen müssen strikte Timeouts besitzen (z. B. max. 3–5 Sekunden), um die UX nicht negativ zu beeinträchtigen.
* **Datenschutz:** Es werden nur die vom Modell generierten Suchbegriffe an externe Suchanbieter übermittelt, keine privaten Chat-Historien.

---

## 4. Akzeptanzkriterien & Testkonzept
1. **Funktional:**
   * Anfragen nach aktuellen Events oder Informationen lösen verlässliche Suchanfragen aus.
   * Die Suchergebnisse fließen korrekt als Kontext in die Antwort ein.
2. **Fehlerbehandlung:**
   * Bei Timeouts oder Offline-Status wird ein eleganter Fallback ausgegeben.
3. **Tests:**
   * Unit-Tests für die Suchdienst-Komponente (ge-mockter HTTP-Client).
   * Integrationstests für den Tool-Call-Loop im Backend.

---

## 5. Geplante Arbeitspakete
1. **Arbeitspaket 1:** `WebSearchService` im Backend (Anbindung Such-Provider + HTML/Text-Extraction).
2. **Arbeitspaket 2:** Erweiterung der `OllamaRuntime` um Tool-Definitions & Tool-Call-Handling.
3. **Arbeitspaket 3:** Integration im `ChatService` inkl. Resilienz & Timeouts.
4. **Arbeitspaket 4:** Tests & Validierung.