# ADR 10: MCP als einheitliche Capability-Grenze

- Status: Vorgeschlagen
- Datum: 2026-09-27

## Kontext

Avalon stellt Funktionen bereit, die von LLM-basierten Chats, Agenten und
zukünftigen Automationen genutzt werden können. Dazu gehören beispielsweise
Websuche, Musikzugriff und weitere lokale oder externe Fähigkeiten.

Diese Capabilities benötigen unabhängig vom jeweiligen Aufrufer einheitliche
Verträge sowie die Durchsetzung von Authorization, Permissions und Scopes.

Chats laufen zunächst innerhalb des Avalon-Backends. Agenten und Automationen
sollen jedoch auch in getrennten Prozessen oder Containern ausgeführt werden
können und dabei auf dieselben Capabilities zugreifen.

Avalon stellt bereits einen MCP-Server bereit. Ein Integrationstest hat
bestätigt, dass die über MCP dynamisch veröffentlichten Tooldefinitionen von
den eingesetzten lokalen Modellen Gemma 4 sowie Qwen2.5-Coder 7B und 14B für
Tool Calling verwendet werden können. Toolaufrufe und Ergebnisse konnten über
MCP erfolgreich verarbeitet werden.

## Entscheidung

MCP bildet Avalons einheitliche und verbindliche Capability-Grenze.

- Capabilities werden über MCP definiert und veröffentlicht.
- Aufrufer beziehen verfügbare Tools und deren Schemas über MCP statt über
  separat gepflegte Tooldefinitionen.
- Capability-Aufrufe verwenden die MCP-Verträge unabhängig davon, welcher
  LLM-, Agenten- oder Automationspfad den Aufruf ausgelöst hat.
- Authorization, Permissions und Scope-Prüfung liegen innerhalb bzw. unterhalb
  dieser Capability-Grenze und dürfen durch keinen Transportweg umgangen
  werden.
- Inter-Process-Zugriff über einen MCP-Netzwerktransport wird dauerhaft
  unterstützt. Er ist insbesondere für isolierte Agenten und Automationen in
  Containern erforderlich.
- Zusätzlich darf ein In-Process-Transport angeboten werden, um lokale Aufrufe
  effizienter auszuführen.
- Ein In-Process-Transport ist ausschließlich eine Optimierung. Er muss
  dieselben MCP-Verträge und dieselben sicherheitsrelevanten Prüfungen wie der
  Inter-Process-Pfad einhalten.
- Die Wahl des Transports ist kein Bestandteil der fachlichen Capability und
  darf deren Semantik nicht verändern.

## Konsequenzen

- MCP ist die zentrale Quelle für Namen, Beschreibungen und Eingabeschemas von
  Capabilities.
- LLM-spezifische Besonderheiten des Tool Callings bleiben außerhalb der
  Capability-Schicht, beispielsweise in Runtime-Adaptern oder der
  Tool-Loop-Steuerung.
- Capability-Implementierungen müssen nicht wissen, ob ihr Aufrufer ein Chat,
  ein lokaler Agent oder eine isolierte Automation ist.
- Inter-Process- und optionale In-Process-Aufrufe können dieselben
  Capability-Implementierungen verwenden.
- Neue Capabilities müssen nicht zusätzlich in einer separaten
  LLM-Tool-Registry gepflegt werden.
- Ein optionaler In-Process-Pfad darf keine zweite, schwächer abgesicherte
  Aufrufschnittstelle etablieren.
- Contract- und Authorization-Tests müssen sicherstellen, dass unterschiedliche
  Transportwege semantisch und sicherheitsseitig äquivalent bleiben.

## Verworfene Alternativen

### Separate Tooldefinitionen für LLM und MCP

LLM-Tooldefinitionen werden unabhängig von den MCP-Definitionen gepflegt.

Verworfen, weil dadurch zwei Quellen für Capability-Verträge entstehen und
Schemas, Berechtigungen und Verhalten auseinanderlaufen können.

### MCP nur für externe Aufrufer

Interne Chats rufen Capabilities direkt auf, während nur externe Agenten MCP
verwenden.

Verworfen, weil dadurch zwei unterschiedliche Capability-Pfade mit
unterschiedlicher Semantik und potenziell unterschiedlichen
Authorization-Regeln entstehen.

### Ausschließlich Inter-Process-MCP

Auch innerhalb des Backend-Prozesses werden Capabilities zwingend über den
Netzwerktransport aufgerufen.

Nicht als Architekturvorgabe gewählt. Der Netzwerkpfad muss unterstützt
werden, ein semantisch äquivalenter In-Process-Transport darf jedoch als
Optimierung verwendet werden.