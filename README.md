# Authorized Creator Video Queue

This repository runs the TikTok creator-profile ingestion and Buffer queueing system only.

## Daily batch schedule

GitHub Actions runs once daily at **07:00 Pakistan Standard Time** (02:00 UTC). Each run scans the configured creator profiles, downloads eligible unposted videos, ranks them by views and engagement, and attempts to add **four distinct videos** to the Buffer queue.

Buffer's own Facebook channel publishing schedule controls when those four queued videos are actually published. Configure at least four daily publishing slots in Buffer if you want all four to publish on the same day. If Buffer has fewer than four slots, extra posts may remain queued for later days.

The workflow reports the confirmed Buffer count as `Daily batch complete: N/4`. Four daily publications are dependent on successful TikTok profile access/downloads, at least four eligible unposted videos, valid Buffer credentials, and four available Buffer publishing slots. The automation does not bypass platform restrictions or creator permissions.

## Creator profiles

The active configured profiles are:
- `khudserabtak`
- `sultan_editx00`
- `satisfyingbytiktok`
- `ismail_wri8s_6`
- `haya_aesticxs`
- `hammadeditz_09`
- `aesthatic_creator`

The workflow scans public profile videos, ranks candidates using views and engagement, and prefers rotating between creators. Only repost content for which the account owner has granted permission.

## Download and duplicate handling

- Downloads are kept in the source format; no transcoding is performed.
- Posted IDs are stored in `creator_videos/posted.json`.
- GitHub Actions runners are temporary. Missing local files are downloaded again on later runs.
- A video is marked posted only after Buffer confirms that it was added to the queue.
- Each confirmed video is saved to history immediately, so a later failure in the batch does not erase earlier confirmations.
- Videos are hosted as GitHub Release assets before they are sent to Buffer.

## Buffer configuration

Add these repository Actions secrets:
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

Set the Facebook channel's Buffer publishing schedule to at least four daily slots. The workflow adds four posts to the queue; Buffer determines their publication times.

## Local setup

```bash
pip install -r requirements.txt
python -u creator_video_queue.py
```
