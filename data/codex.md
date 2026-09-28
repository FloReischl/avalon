Avalon: Produktions-Tool-Calling auf generischen MCP-Pfad umstellen

Kontext
-------

Avalon verwendet MCP als einheitliche Capability-Grenze (ADR 10).

Der aktuelle ToolRunner behandelt web.search noch als speziell integrierte
Capability. Das soll entfallen.

Ein vorhandener opt-in Spike
tests/integration/test_mcp_ollama_tool_calling_spike.py
hat bereits erfolgreich gezeigt:

- MCP tools/list -> Ollama Tool-Schema
- LLM Tool Call
- MCP tools/call
- Tool-Ergebnis zurück an das LLM
- finale natürliche Antwort

Der Spike bleibt bestehen und soll nicht in den Produktionsvertrag oder eine
feste Modellmatrix umgebaut werden.

Ziel
----

ToolRunner generisch auf die vom Avalon-MCP-Server veröffentlichten
Capabilities umstellen.

Der ToolRunner darf keine Capability wie web.search oder music.play_tracks
fachlich kennen.

Produktionsfluss:

Principal
  -> erlaubte MCP-Capabilities
  -> ToolRunner / LLM Tool Loop
  -> MCP tools/call
  -> MCP Capability
  -> PermissionGuard / Grant bzw. Approval
  -> Ergebnis zurück an das LLM

Scope
-----

1. MCP tools/list ist die Quelle der LLM-Tooldefinitionen.

2. Die für einen Principal sichtbaren Tools werden anhand von
   principal_permissions gefiltert.

   Wichtig:
   - principal_permissions bestimmt, welche Capability der Principal
     grundsätzlich verwenden könnte.
   - permission_grants dürfen die Discovery NICHT filtern.
   - Ein fehlender Grant verhindert daher nicht, dass ein grundsätzlich
     erlaubtes Tool dem LLM angeboten wird.
   - Der bestehende Grant-/Approval-Flow greift erst beim Capability-Aufruf.

3. Die principal-spezifische Tool-Liste darf statisch gecacht werden.
   principal_permissions ändern sich aktuell während der Backend-Laufzeit nicht.
   Keine Cache-Invalidierungslogik implementieren.

4. Tool-Aufrufe generisch über MCP tools/call ausführen.

   Keine Dispatch-Sonderfälle für:
   - web.search
   - music.play_tracks
   - zukünftige Capabilities

5. Authorization muss innerhalb bzw. unterhalb der MCP-Capability-Grenze
   erfolgen.

   Ein direkter MCP-Aufruf darf PermissionGuard/Authorization nicht umgehen.

   Der bestehende Flow bleibt erhalten:
   - keine passende principal_permission -> PermissionDenied
   - passende Permission + aktiver Grant -> Capability ausführen
   - passende Permission ohne Grant -> bestehenden Authorization Request /
     Approval-Flow verwenden
   - Abort/Timeout behalten bestehende Semantik

6. Die bestehende turn-lokale Deduplizierung identischer Tool Calls behalten.

   Sie darf nicht mehr web.search-spezifisch sein, sondern soll generisch für
   identische MCP Tool Calls funktionieren.

   Ein identischer Call innerhalb desselben Tool-Loops wird nur einmal
   ausgeführt; bei Wiederholung wird das bereits vorhandene Ergebnis erneut
   ans Modell gegeben.

7. LLM-spezifische Tool-Call-Normalisierung bleibt im Runtime-Layer.

   Insbesondere den bestehenden Qwen2.5-Coder Text-JSON-Fallback nicht in
   MCP- oder Capability-Code verschieben.

8. MCP-Fehler bewusst einfach behandeln:

   - tools/list fehlgeschlagen -> aktuellen Turn mit verständlichem
     Tool/MCP-Fehler beenden
   - tools/call fehlgeschlagen -> aktuellen Turn entsprechend beenden
   - keine Retries
   - kein direkter Capability-Fallback

9. Inter-Process-MCP über den bestehenden MCP-Endpunkt muss erhalten bleiben.

   Keine In-Process-Optimierung in diesem Arbeitspaket implementieren.
   Diese kann später ergänzt werden, muss dann aber dieselben MCP-Verträge und
   Authorization-Regeln einhalten.

Tests
-----

Bestehende Tool-/Integrationstests auf den generischen MCP-Pfad migrieren.

Insbesondere verifizieren:

- nur über principal_permissions grundsätzlich erlaubte Tools werden dem LLM
  angeboten
- Grants beeinflussen tools/list nicht
- Tool-Aufruf läuft über MCP tools/call
- PermissionGuard / bestehender Approval-Flow bleibt wirksam
- fehlende principal_permission führt weiterhin zu PermissionDenied
- identische Tool Calls innerhalb eines Turns werden nur einmal ausgeführt
- unterschiedliche Tool Calls werden unabhängig ausgeführt
- MCP list/call Fehler führen sauber zum bestehenden Fehlerpfad
- ToolRunner enthält keine web.search- oder music.play_tracks-Sonderlogik mehr

Den vorhandenen
tests/integration/test_mcp_ollama_tool_calling_spike.py
inhaltlich unverändert als opt-in Spike behalten. Insbesondere dessen aktuelle
Modellliste nicht als stabile Produktionsanforderung behandeln.

Bestehende relevante Tests weiterhin grün halten.

Nicht im Scope
--------------

- In-Process-MCP-Transport
- Runtime-Änderungen an der Qwen Tool-Call-Normalisierung
- neue Capabilities
- music.play_tracks in principal_permissions aufnehmen
- agents.yaml an den aktuellen Permission-Stand angleichen
- dynamische Änderung von principal_permissions zur Laufzeit
- Cache-Invalidierung
- RepoMap aktualisieren
- ADR ändern
- Frontend-Änderungen

Verifikation
------------

1. Relevante Unit- und Integrationstests ausführen.
2. Gesamte pytest-Suite ausführen.
3. Prüfen, dass der vorhandene MCP-Spike weiterhin gesammelt, aber ohne
   Opt-in übersprungen wird.
4. Keine externen Dienste oder Modelle für normale Tests voraussetzen.

Done
----

- ToolRunner ist capability-agnostisch.
- LLM-Tooldefinitionen stammen aus MCP Discovery.
- Discovery ist principal-permission-spezifisch.
- Tool-Ausführung erfolgt generisch über MCP.
- Authorization kann auch bei direktem MCP-Zugriff nicht umgangen werden.
- Deduplizierung funktioniert capability-unabhängig.
- bestehender Approval-Flow funktioniert unverändert.
- bestehende Tests sind auf den neuen Pfad migriert und grün.
- vollständige pytest-Suite ist grün.