"""Create one spoken podcast MP3 for every supplied web article."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from avalon_workflows import AvalonWorkflowClient


OUTPUT_DIR = Path("/tmp/avalon/audio")

PODCAST_PROMPT = """Erstelle aus dem folgenden Artikel einen Podcast-Text.

Artikel:
{content}
"""

OPINION_PROMPT = """Erstelle eine zweite Podcast-Episode als eigenständige Einordnung des folgenden Artikels.

Gib nicht einfach den Artikel erneut wieder. Analysiere stattdessen das Thema und die Aussagen des Artikels kritisch und möglichst ausgewogen. Hinterfrage Argumente und Framing des Autors, berücksichtige relevante Gegenpositionen und benenne Unsicherheiten. Entwickle daraus eine begründete eigene Einschätzung.

Artikel:
{content}
"""


def _file_name(index: int, url: str, episode: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).stem or parsed.netloc or "podcast"
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-._")
    candidate = candidate[:80] or "podcast"
    return f"{index:02d}-{candidate}-episode-{episode}.mp3"


def _clean_podcast_text(text: str) -> str:
    # Entfernt [Intro], (Musik), *Jingle*, etc.
    text = re.sub(
        r"[\(\[\{\*][^\)\]\}]*?(?:musik|jingle|intro|outro|sound|pause|lachen)[^\)\]\}]*?[\)\]\}\*]",
        "",
        text,
        flags=re.IGNORECASE,
    )
    # Entfernt doppelte Leerzeichen und leere Zeilen
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


async def main() -> None:
    # init workflow
    workflow = AvalonWorkflowClient.from_stdin()

    # remove context
    workflow.model_context = None

    # get urls from input payload
    urls = workflow.payload_as_list()
    if not isinstance(urls, list) or not urls or not all(
        isinstance(url, str) and url for url in urls
    ):
        raise ValueError("Workflow payload requires a non-empty 'urls' list.")

    workflow.log(f"creating podcasts for {len(urls)} article(s)")
    await workflow.progress(f"Erzeuge Podcasts für {len(urls)} Artikel.")

    succeeded = 0

    # loop all urls
    for index, url in enumerate(urls, start=1):
        try:
            workflow.log(f"[{index}/{len(urls)}] loading {url}")
            await workflow.progress(
                f"Artikel {index}/{len(urls)} wird geladen: {url}"
            )

            podcast_audio_file = OUTPUT_DIR / _file_name(index, url, "A")
            podcast_text_file = podcast_audio_file.with_suffix(".txt")
            opinion_audio_file = OUTPUT_DIR / _file_name(index, url, "B")
            opinion_text_file = opinion_audio_file.with_suffix(".txt")

            # get web content from url
            article = await workflow.call_tool(
                "web.get-content",
                {"url": url},
            )
            if not isinstance(article, dict):
                raise RuntimeError("web.get-content returned no structured result.")

            content = article.get("content")
            if not isinstance(content, str) or not content:
                raise RuntimeError("web.get-content returned no article content.")

            # create podcast text
            workflow.log(f"[{index}/{len(urls)}] generating podcast text")
            await workflow.progress(
                f"Podcast-Text {index}/{len(urls)} wird erzeugt."
            )

            # get content podcast text
            word_count = len(re.findall(r"\b\w+\b", content))
            word_count = max(400, min(1000, word_count))
            podcast_instructions = """<format_rules>
    <rule>Erstelle einen Podcast persönlich für den User.</rule>
    <rule>Antworte stets audio-optimiert.</rule>
    <rule>Verwende niemals Tabellen in deiner Ausgabe.</rule>
    <rule>Die Länge des Podcasts soll ca. ##word_count## Wörter betragen.</rule>
    <rule>Generiere ausschließlich den gesprochenen Text. Erzeuge keinerlei Audio-Marker, Regieanweisungen, Szenenbeschreibungen oder Platzhalter für Musik/Jingles (wie z. B. [Intro-Musik], (Musik blendet ein), *Jingle* oder Sprecher-Namen).</rule>
</format_rules>

<user_profile>
    <name>Flo</name>
    <gender>männlich</gender>
    <birthdate>1977-10-12</birthdate>
</user_profile>"""

            podcast_text = await workflow.llm(
                PODCAST_PROMPT.format(content=content),
                instructions=podcast_instructions.replace("##word_count##", str(word_count)),
                context=None,
            )

            podcast_text = _clean_podcast_text(podcast_text)
            podcast_text_file.write_text(podcast_text)

            # create audio
            workflow.log(
                f"[{index}/{len(urls)}] creating audio {podcast_audio_file}"
            )
            await workflow.progress(
                f"Audio {index}/{len(urls)} wird erzeugt: {podcast_audio_file.name}"
            )

            await workflow.call_tool(
                "content.create-audio",
                {
                    "content": podcast_text,
                    "output_file": str(podcast_audio_file),
                },
            )

            # create independent opinion episode
            workflow.log(f"[{index}/{len(urls)}] generating opinion text")
            await workflow.progress(
                f"Meinungs-Episode {index}/{len(urls)} wird erzeugt."
            )

            opinion_text = await workflow.llm(
                OPINION_PROMPT.format(content=content),
                instructions=podcast_instructions.replace("##word_count##", str(max(word_count, 500))),
                context=None,
            )

            opinion_text = _clean_podcast_text(opinion_text)
            opinion_text_file.write_text(opinion_text)

            workflow.log(
                f"[{index}/{len(urls)}] creating audio {opinion_audio_file}"
            )
            await workflow.progress(
                f"Meinungs-Audio {index}/{len(urls)} wird erzeugt: {opinion_audio_file.name}"
            )

            await workflow.call_tool(
                "content.create-audio",
                {
                    "content": opinion_text,
                    "output_file": str(opinion_audio_file),
                },
            )

            succeeded += 1
            await workflow.progress(
                f"Podcast {index}/{len(urls)} erstellt: "
                f"{podcast_audio_file.name}, {opinion_audio_file.name}"
            )

        except Exception as exc:
            workflow.log(
                f"[{index}/{len(urls)}] failed for {url}: "
                f"{type(exc).__name__}: {exc}"
            )
            await workflow.progress(
                f"Podcast {index}/{len(urls)} fehlgeschlagen: {url}"
            )

    await workflow.progress(
        f"Podcast-Workflow abgeschlossen: {succeeded}/{len(urls)} erfolgreich."
    )


if __name__ == "__main__":
    asyncio.run(main())
