# Authorized Creator Video Queue

This repository runs the TikTok creator-profile ingestion and Buffer queueing system only.

## Daily schedule

GitHub Actions runs four times daily (Pakistan Standard Time):
- 07:00
- 11:00
- 15:00
- 19:00

Each successful run selects and queues one video to the configured Buffer channel. Buffer's own queue schedule determines the exact publication time.

## Creator profiles

The active configured profiles are:
- `khudserabtak`
- `sultan_editx00`
- `satisfyingbytiktok`
- `ismail_wri8s_6`
- `haya_aesticxs`
- `hammadeditz_09`
- `aesthatic_creator`

The workflow scans public profile videos, ranks available candidates using views and engagement, and rotates away from the previous creator when another eligible creator is available. It does not bypass private-account restrictions or access controls. Only repost content for which the account owner has permission.

## Download and duplicate handling

- Downloads are kept in the source format; no transcoding is performed.
- Posted IDs are stored in `creator_videos/posted.json`.
- GitHub Actions runners are temporary. If a manifest entry points to a video file that is not present on the new runner, the workflow downloads that video again instead of permanently treating it as available.
- The workflow skips IDs already confirmed in Buffer posting history.
- The selected video is hosted as a GitHub Release asset before it is sent to Buffer.
- Posting history is updated only after Buffer confirms the queue operation.

## Buffer configuration

Add these repository Actions secrets:
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

The workflow enables profile fetching and Buffer queueing automatically. It does not need manual workflow switches.

## Local setup

```bash
pip install -r requirements.txt
python creator_video_queue.py
```
