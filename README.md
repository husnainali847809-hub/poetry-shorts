# Authorized Creator Video Queue

This repository runs the TikTok creator-profile ingestion and Buffer scheduling system only.

## Daily batch and Facebook publishing times

GitHub Actions runs once daily at **06:00 Pakistan Standard Time** (01:00 UTC). It scans the configured creator profiles, downloads eligible unposted videos, ranks candidates by views and engagement, and attempts to schedule **four distinct videos**.

The four Facebook publishing times are fixed to Pakistan time:
- 08:00
- 12:00
- 16:00
- 20:00

The script uses Buffer's exact-time scheduling mode, converting Pakistan local times to UTC timestamps. It does not depend on Buffer's next-available queue slots. If a manual run starts after one or more slots have passed, it uses the next future slots in the same sequence.

## Video selection and duplicates

- The newest video is not mandatory. The system ranks available videos by views and engagement; an older video can be selected when it is a better eligible candidate.
- It excludes IDs already recorded in `creator_videos/posted.json` by this automation.
- It prefers rotating between different configured creators.
- A video is marked posted only after Buffer confirms the scheduled post.
- Each confirmed video is saved immediately so a later failure does not erase earlier confirmations.
- The system cannot automatically know about videos manually uploaded to Facebook outside this automation unless those IDs are also added to its posting history.

## Creator profiles

The active configured profiles are:
- `khudserabtak`
- `sultan_editx00`
- `satisfyingbytiktok`
- `ismail_wri8s_6`
- `haya_aesticxs`
- `hammadeditz_09`
- `aesthatic_creator`

Only repost content for which the account owner has granted permission.

## Download and duplicate handling

- Downloads are kept in the source format; no transcoding is performed.
- GitHub Actions runners are temporary. Missing local files are downloaded again on later runs.
- Videos are hosted as GitHub Release assets before they are sent to Buffer.

## Buffer configuration

Keep these repository Actions secrets configured:
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

Buffer must have automatic publishing enabled for the connected Facebook Page. The exact publishing times are sent with each post by the automation.

## Daily result

The workflow prints `Daily batch complete: N/4 videos confirmed in Buffer`. Four scheduled posts require at least four eligible unposted videos, successful TikTok downloads, valid Buffer credentials, and successful Buffer responses.

## Local setup

```bash
pip install -r requirements.txt
python -u creator_video_queue.py
```
