import sys
import os
from datetime import datetime, timezone

def main():
    # 1. Stdin einlesen
    input_data = sys.stdin.read().strip()

    # Zielverzeichnis sicherstellen
    output_dir = "/tmp/avalon"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "test-output.txt")

    # Timestamp im ISO-Format (UTC)
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # 2. - 5. Datei schreiben
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"{timestamp_iso}\n")
        f.write(f"{input_data}\n")

if __name__ == "__main__":
    main()