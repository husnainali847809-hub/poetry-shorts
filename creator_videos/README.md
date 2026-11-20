# Creator video queue

Open **Actions → Authorized Creator Video Queue → Run workflow**.

- **Enable account source fetch**: scans the seven configured public creator profiles directly. No external feed URL or feed token is required.
- **Enable Buffer posting**: turn ON to queue one eligible video to Buffer.

## Required GitHub Actions secrets

- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

No `CREATOR_SOURCE_FEED_URL` or `CREATOR_SOURCE_FEED_TOKEN` secrets are used.

## Configured creator profiles

- `jawad..382`
- `hmxii_`
- `ain.poetic`
- `mr_dark_shayari`
- `blurry_abdullah`
- `idealads_2.0`
- `lost_632`

The workflow attempts to read publicly available profile/video information with yt-dlp. Platform restrictions, login requirements, rate limits, deleted/private videos, or format changes can prevent a profile from being read or a video from downloading. It does not bypass private-account restrictions or access controls. Use this only for videos whose owners have explicitly authorized reposting. Downloaded files are not transcoded; the source format is retained. Previously queued video IDs are skipped, and a video is marked posted only after Buffer confirms queue creation.

## Buffer setup

Add `BUFFER_API_KEY` and `BUFFER_CHANNEL_ID` under **Settings → Secrets and variables → Actions → New repository secret**.
