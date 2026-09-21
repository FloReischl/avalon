1. Aider starten
2. Kurzes Intro (2 Sätze) + Execution Contract von Frieda einfügen
3. Aider im /architect Plan machen lassen -> Bestätigen -> Code schreiben lassen
4. Lokale Tests ausführen (pytest)
5. Bei grünem Test: git diff kopieren -> Frieda zum Review geben
6. Aider beenden/clearen (/clear) -> Bereit für Paket 2!


``` shell
cd ~/dev/avalo

aider \
  --model ollama_chat/qwen2.5-coder:14b-instruct \
  backend/app/main.py \
  tests/backend/test_main.py
```
