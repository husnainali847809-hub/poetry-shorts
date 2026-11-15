# Pulsenama — AI Poetry Video Creator

Pulsenama automatically creates short vertical poetry videos in Urdu, Roman Urdu, and English.

## What it does

- Chooses the mood, language, and duration automatically.
- Generates a short 2–3 line poem, with a built-in poem fallback when the AI response is unavailable.
- Finds a mood-matched portrait video or photo for the background.
- Searches Wikimedia Commons for a licensed human recording that matches the actual displayed poem text, not merely the same language or a generic poetry keyword.
- When an exact-text recording is found, places it clearly in the foreground and mixes a quiet, original piano-and-strings instrumental underneath.
- Never generates an AI speaking voice or substitutes an unrelated recitation/song. If no licensed human recording matching the displayed poem is found, generation stops and no instrumental-only video is published.
- Renders a 1080×1920 MP4 and a text/attribution file.
- Creates a Buffer caption in the poem's language, adds a short mood-matched line, and includes relevant Urdu or English hashtags automatically.

## Automatic schedule

Five daily Pakistan-time slots (UTC+5):
- 09:00 — Qawwali performance
- 12:00 — Urdu poetry
- 15:00 — Urdu poetry
- 18:00 — Qawwali performance
- 21:00 — English poetry

Qawwali slots search Wikimedia Commons for actual performance videos and retain original audio. If no usable Qawwali video is found, that run fails instead of substituting unrelated footage. GitHub may start scheduled jobs a little later than the exact cron time.

## Captions and hashtags

Every Buffer post now includes the poem title and lines, a short mood-matched caption, a follow prompt in the same language, and relevant hashtags. Urdu posts use Urdu captions and Urdu hashtags; English posts use English captions and English hashtags. Hashtags also vary by the selected mood.

## Buffer setup

Add these repository Actions secrets:

- `BUFFER_API_KEY` — your Buffer API key.
- `BUFFER_CHANNEL_ID` — the Buffer channel where videos should be queued.

When both are configured, each generated video is sent to that channel using Buffer's **Add to Queue** mode. Buffer then uses the channel's configured queue schedule. If either secret is missing, video generation still completes and the workflow logs that Buffer publishing was skipped.

## Other required secrets

- `OPENROUTER_API_KEY` — AI poem generation.
- `PEXELS_API_KEY` — Pexels video/photo search (optional).
- `PIXABAY_API_KEY` — Pixabay video/photo search (optional).

## Generated files

The workflow stores `poetry_demo.mp4` and `poetry_demo.txt` as downloadable workflow artifacts for 7 days. The MP4 is also attached to a public GitHub Release to provide Buffer with a publicly accessible media URL.
