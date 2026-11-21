# Creator Video Fetch & Buffer Auto-Publishing

This repository now contains only the creator-video ingestion and Buffer queueing system.

## What it does

1. Scans the seven creator profiles configured in `creator_video_queue.py` when source fetching is enabled.
2. Reads available video metadata and ranks candidate videos by views and engagement.
3. Downloads eligible videos without transcoding, preserving the downloaded source format.
4. Skips video IDs already recorded in `creator_videos/posted.json`.
5. Hosts the selected video in a GitHub Release.
6. Builds a caption with attribution and hashtags, then adds the video to the configured Buffer channel queue.
7. Saves posting history only after Buffer confirms that the post was queued.

Only repost videos when the creator has explicitly authorized their use. The workflow does not bypass private-account restrictions or access controls.

## Schedule

The GitHub Actions workflow runs daily at 02:00 UTC (07:00 Pakistan time), and can also be started manually from **Actions → Authorized Creator Video Queue → Run workflow**.

The scheduled workflow uses repository variables:
- `ENABLE_ACCOUNT_SOURCE_FETCH` — set to `true` to enable scanning the configured creator profiles.
- `ENABLE_BUFFER_POSTING` — set to `true` to enable Buffer queueing (defaults to true).

Manual runs provide separate switches for fetching and posting.

## Required repository secrets

- `BUFFER_API_KEY` — Buffer API key.
- `BUFFER_CHANNEL_ID` — destination Buffer channel ID.

## Python dependencies

Install with:

```bash
pip install -r requirements.txt
```
