**1. Blocker: Authorization ist nur für web.search an die MCP-Grenze gewandert.**

`AuthorizedMcpServer.list_tools()` ist schön generisch, aber die eigentliche `PermissionGuard.execute(...)`-Integration steckt weiterhin direkt in `register_web_tools()`. Damit ist der ToolRunner zwar capability-agnostisch, die **MCP-Capability-Grenze selbst aber noch nicht generisch abgesichert**. Sobald `music.play_tracks` später über `principal_permissions` sichtbar wird, läuft sein `tools/call` nach diesem Diff ohne den neuen Guard-Pfad. Das widerspricht genau unserem Ziel „keine Sonderstellungen mehr“. Die RepoMap beschreibt den Guard bislang als zentralen Authorization-Mechanismus. 

Ich würde Codex daher nachbessern lassen: Authorization/Guard muss **zentral für MCP** `tools/call` greifen, nicht innerhalb von `web.py`. Die Capability-spezifische Permission muss dabei aus dem aufgerufenen Tool bzw. dem Permission-Mapping bestimmt werden. `web.py` sollte danach wieder schlicht seine Capability implementieren.

**2. Kleiner, aber echter Scope-Verstoß: statischer Discovery-Cache fehlt.**

`ToolRunner.stream_response()` erzeugt bei jedem Turn einen Client und macht jedes Mal `client.list_tools()`. Besprochen war: principal-spezifisch statisch cachen, weil `principal_permissions` zur Laufzeit unverändert sind. Kein Drama bei zwei Tools, aber schlicht nicht umgesetzt.

Der Rest gefällt mir: ToolRunner ist tatsächlich generisch, Dedupe ist jetzt capability-unabhängig, MCP-Fehler haben keinen Fallback, Qwen-Normalisierung bleibt draußen und `principal_permissions` filtert Discovery unabhängig von Grants.