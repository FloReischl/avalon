"""Organize Gmail inbox chronologically from oldest to newest into defined taxonomies."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path

from avalon_workflows import AvalonWorkflowClient

# ------------------------------------------------------------------------------
# Workflow Header Configuration
# ------------------------------------------------------------------------------
SOURCE_CATEGORY = "INBOX"
ARCHIVE_AFTER_LABELING = False
FALLBACK_CATEGORY = "Unkategorisiert"
MAX_LLM_CATEGORY_COUNT = 4

# Exkludierte System-Labels, die nicht als Taxonomie verwendet werden dürfen
SYSTEM_LABELS = {
    "INBOX", "SENT", "UNREAD", "SPAM", "TRASH", "DRAFT", "DRAFTS", "STARRED",
    "IMPORTANT", "CATEGORY_PERSONAL", "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_FORUMS", "ALL MAIL", 
}

# Persona & Instruction Prompting für den stateless LLM Call
CLASSIFICATION_INSTRUCTIONS = """<format_rules>
<rule>Wähle maximal 4 Kategorien aus der übergebenen Liste ERLAUBTE KATEGORIEN.</rule>
<rule>Antworte AUSSCHLIESSLICH im gültigen JSON-Format: {"categories": ["...", "..."]}.</rule>
<rule>Erfinde KEINE neuen Kategorien oder Hauptpfade.</rule>
<rule>Wenn kein spezifischer Untertyp passt, wähle das entsprechende 'Sonstiges'-Label der Hauptkategorie (z. B. 'Finanzen/Sonstiges').</rule>
<rule>Wenn gar nichts passt, wähle ausschließlich 'Unkategorisiert'.</rule>
</format_rules>"""


def _clean_json_response(raw_text: str, allowed_categories: list[str]) -> list[str]:
    """Extrahiert sauber die Kategorien-Liste aus der LLM-Antwort."""
    try:
        # Falls Markdown Codeblocks vorhanden sind
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            cats = data.get("categories", [])
            if isinstance(cats, list):
                return [str(c) for c in cats if c in allowed_categories]
    except Exception:
        pass
    return [FALLBACK_CATEGORY]


async def main() -> None:
    workflow = AvalonWorkflowClient.from_stdin()
    workflow.model_context = None  # Kein störender Chat-Kontext
    
    workflow.log("Starting Mail Organization Workflow")
    await workflow.progress("Initialisiere E-Mail-Organisations-Workflow...")

    # Bekannte Gmail-Labels als Taxonomie holen & System-Labels ausfiltern
    all_categories = await workflow.get_mail_categories()
    allowed_categories = [
        cat for cat in all_categories if cat not in SYSTEM_LABELS and not cat.startswith("[Gmail]")
    ]
    workflow.log(f"Taxonomie geladen ({len(allowed_categories)} erlaubte Labels)")

    # Provider Gmail
    await workflow.set_mail_provider("gmail")

    # Provider Stats abrufen, um ältestes E-Mail-Datum zu ermitteln
    stats = await workflow.get_mail_provider_stats()
    oldest_date_str = stats.get("oldest_message_date")
    
    if not oldest_date_str or not isinstance(oldest_date_str, str):
        await workflow.progress("Keine Mails oder kein ältestes Datum in Postbox gefunden.")
        return

    # UTC-Zeitstempel parsen
    current_batch_start = datetime.fromisoformat(oldest_date_str.replace("Z", "+00:00")) \
                                  .replace(day=1, hour=0, minute=0, second=0, microsecond=0)    
    until = (datetime.now(current_batch_start.tzinfo) - timedelta(days=100)) \
                     .replace(hour=0, minute=0, second=0, microsecond=0)

    processed_threads: set[str] = set()
    total_messages_processed = 0

    # Monatsweise Iteration von alt nach neu
    while current_batch_start < until:
        batch_end = min(current_batch_start + relativedelta(months=1), until)
        month_label = current_batch_start.strftime("%Y-%m")

        workflow.log(f"Processing Batch: {month_label} ({current_batch_start.date()} bis {batch_end.date()})")
        await workflow.progress(f"Lade Mails für Zeitraum {month_label}...")

        # Mails im Monatsfenster holen (since >=, before <)
        messages = await workflow.get_mail_messages(
            category=SOURCE_CATEGORY,
            since=current_batch_start,
            before=batch_end,
        )

        if not messages:
            workflow.log(f"Keine Mails in {month_label}")
            current_batch_start = batch_end
            continue

        workflow.log(f"{len(messages)} Nachricht(en) in {month_label} gefunden.")

        for msg in messages:
            msg_id = str(msg["message_id"])
            thread_id = str(msg["thread_id"]) if msg.get("thread_id") else msg_id
            internal_date_str = str(msg["internal_date"])

            # --- A. Deterministisches Jahre-Labeling auf Message-Ebene ---
            msg_date = datetime.fromisoformat(internal_date_str.replace("Z", "+00:00"))
            year_category = f"Jahre/{msg_date.year}"

            # Jahres-Label sicherstellen & auf Nachricht anwenden
            if year_category not in all_categories:
                await workflow.create_mail_categories([year_category])
                all_categories.append(year_category)

            await workflow.set_mail_categories(
                message_id=msg_id,
                categories=[year_category],
                archive=False,
            )

            # --- B. Themen-Kategorisierung auf Thread-Ebene ---
            if thread_id in processed_threads:
                total_messages_processed += 1
                continue

            # Thread-Kontext für LLM aufbereiten
            thread_messages = await workflow.get_mail_messages_by_thread(thread_id)
            
            # Thread-Inhalte zusammenstellen
            thread_summary = []
            for t_msg in thread_messages:
                full_mail = await workflow.get_mail(str(t_msg["message_id"]), as_text=True)
                sender = full_mail.get("sender", {}).get("name") or full_mail.get("sender", {}).get("email_address")
                body = full_mail.get("body_content", "")[:1000]  # Ersten 1000 Zeichen je Mail genügen
                thread_summary.append(f"Von: {sender}\nInhalt: {body}")

            combined_thread_text = "\n---\n".join(thread_summary)
            subject = msg.get("subject", "Kein Betreff")

            prompt = (
                f"ERLAUBTE KATEGORIEN:\n{json.dumps(allowed_categories, indent=2)}\n\n"
                f"E-MAIL THREAD DETAILS:\n"
                f"Betreff: {subject}\n"
                f"Thread-Auszug:\n{combined_thread_text}"
            )

            # LLM Stateless Aufruf
            llm_response = await workflow.llm(
                prompt=prompt,
                instructions=CLASSIFICATION_INSTRUCTIONS,
                context=None,
            )

            chosen_categories = _clean_json_response(llm_response, allowed_categories)[:MAX_LLM_CATEGORY_COUNT]

            # Themen-Labels auf alle Nachrichten des Threads setzen
            for t_msg in thread_messages:
                await workflow.set_mail_categories(
                    message_id=str(t_msg["message_id"]),
                    categories=chosen_categories,
                    archive=ARCHIVE_AFTER_LABELING,
                )

            processed_threads.add(thread_id)
            total_messages_processed += 1

            await workflow.progress(
                f"[{month_label}] Thread verarbeitet: '{subject[:40]}...' -> {chosen_categories}"
            )

        # Nächster Monat
        current_batch_start = batch_end

        break # FLO TODO

    await workflow.progress(
        f"Mail-Organisation abgeschlossen! Insgesamt {total_messages_processed} Mails / {len(processed_threads)} Threads verarbeitet."
    )


if __name__ == "__main__":
    asyncio.run(main())
