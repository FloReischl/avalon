# Text Chat

das erste große Thema für heute.


1. Definition der UI
2. Transienter Chat
3. Text Formatierung
4. Storage und Suche
5. File Upload(?)

## 1. Definition der UI

Ich habe gestern noch lange über die UI nachgedacht...

**Vergiss den Gedanken von fliegenden Balloonns** das sieht zwar fancy aus, ist aber eigentlich gar nicht meine Arbeitsweise.

Der Avatar den wir bislang haben passt als always-on-top point of contact für Audio/Agents... aber schreiben muss ich da nicht direkt können. Anderer Gedanke

Doppelklick auf den Avatar öffnet das eigentliche Main-Window (aller AI ChatBot). Kann das auch in einem *nativen* Tauri Fenster passieren? oder muss/sollte hier eine normale Web-Page geöffnet werden?

## 2. Transienter Chat

Ist **nicht** Zielbild, aber Meilenstein. Wenn die UI steht sollte initial der Text Chat angebunden werden.

* erstmal ohne storage
* ohne persona
* ohne instructions

das wird alles nötig, aber muss nicht im ersten Meilenstein enthalten sein.

## 3. Text Formatierung

Fehlt mir eigentlich bei **allen** mir bekannten ChatBots.

1. Multi-Line Input
   1. Text-Input soll auf jeden Fall Multi-Line können
   2. Wenn ich eine Einzeilige Nachricht schreibe (kein '\n') soll ENTER die Nachricht abschicken.
   3. Sobald ich einmal einen Zeilenumbruch über SHIFT+ENTER einfüge ändert sich das Verhalten
      1. Wenn ENTER und min ein '\n' im Text enthalten -> weiterer Zeilenumbruch. Nicht Senden.
      2. Zum Senden muss jetzt CTRL+ENTER gedrückt werden. Oder ein Send-Button (Icon, nicht Text)
* Text Formatierung
  * Ich möchte, dass meine Eingaben generell als Markdown angenommen und möglichst auch direkt formatiert werden.

## 4. Storage

Wenn die vorherigen Punkte umgesetzt sind, fangen wir an die Chats zu persistieren.

1. Jeder neue Chat bekommt den Initialen Namen "New <YYYY-MM-DD HH:mm:ss>"
2. Erst nach 2 Chat Roundtrips (Prompt + Antwort) wird ein Titel aus dem Kontext erzeugt. Der erste Prompt (v.a. bei Audio) ist oft Begrüßung oder ähnliches.
3. Chats können umbenannt werden

## 5. File Upload

Keine Ahnung, ob das heute schon sein muss. Sprechen wir nachher.