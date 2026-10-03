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


def _file_name(index: int, url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).stem or parsed.netloc or "podcast"
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-._")
    candidate = candidate[:80] or "podcast"
    return f"{index:03d}-{candidate}.mp3"


async def main() -> None:
    # init workflow
    workflow = AvalonWorkflowClient.from_stdin()

    payload = workflow.payload
    if not isinstance(payload, dict):
        raise ValueError("Workflow payload must be an object.")

    # remove context
    workflow.model_context = None

    # get urls from input payload
    urls = payload.get("urls")
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

            # call LLM
            podcast_text = await workflow.llm(
                PODCAST_PROMPT.format(content=content),
                use_context=False,
            )

            output_file = OUTPUT_DIR / _file_name(index, url)

            # create audio
            workflow.log(
                f"[{index}/{len(urls)}] creating audio {output_file}"
            )
            await workflow.progress(
                f"Audio {index}/{len(urls)} wird erzeugt: {output_file.name}"
            )

            await workflow.call_tool(
                "content.create-audio",
                {
                    "content": podcast_text,
                    "output_file": str(output_file),
                },
            )

            succeeded += 1
            await workflow.progress(
                f"Podcast {index}/{len(urls)} erstellt: {output_file}"
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
