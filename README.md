# Single-Creator Cartoon Video Queue

This repository now uses **only the approved TikTok account `@viral_ai_toon`** as its video source. The previous creator-account list is no longer active.

## Daily Facebook schedule

GitHub Actions runs once daily at **06:00 Pakistan time** (01:00 UTC). It scans the configured TikTok profile, downloads eligible videos that have not already been used by this automation, and attempts to schedule four distinct Facebook Reels through Buffer.

Publishing slots (Pakistan time):
- 08:00
- 12:00
- 16:00
- 20:00

## Video selection

- Only `@viral_ai_toon` is scanned.
- The newest video is not mandatory; any eligible unposted video from the profile can be selected.
- The script ranks candidates using available views and engagement data, then selects up to four.
- Videos already recorded in `creator_videos/posted.json` are excluded.
- The original downloaded format is retained; no trimming or transcoding is performed.
- Downloads larger than 200 MB are rejected to keep assets manageable for GitHub Release hosting and Buffer delivery.
- Common video extensions are accepted by the downloader, but Buffer/Facebook may reject formats they do not support. No conversion is performed because the original format is preserved.

## Captions and attribution

The existing caption and hashtag generator remains enabled. The TikTok username and source URL are not added to the Facebook caption. Use this automation only for videos covered by the creator's reposting permission; removing attribution from the caption does not replace any legal or platform attribution requirement.

## Daily target and limitations

The automation attempts four scheduled posts per day. It cannot guarantee four publishes if the profile does not provide at least four eligible unposted videos, downloads fail, video files exceed the size limit, or Buffer/Facebook rejects a file or post. A run with fewer than four Buffer confirmations fails visibly instead of reporting success.

The state file tracks videos used by this automation. It does not automatically detect videos manually uploaded to Facebook outside this workflow.

## Buffer configuration

Repository Actions secrets required:
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

Buffer must be connected to the intended Facebook Page and support publishing the submitted video format.

## Local setup

```bash
pip install -r requirements.txt
python -u creator_video_queue.py
```
