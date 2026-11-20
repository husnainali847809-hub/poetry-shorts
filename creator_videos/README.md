# Authorized creator video intake

Open **Actions → Authorized Creator Video Queue → Run workflow**.

- **Enable account source fetch**: leave OFF until creator authorization and the feed secrets are configured.
- **Enable Buffer posting**: turn OFF for a dry intake run; turn ON to queue an eligible video.

## Required GitHub Actions secrets

- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`
- `CREATOR_SOURCE_FEED_URL`: HTTPS endpoint for a creator-authorized feed adapter.
- `CREATOR_SOURCE_FEED_TOKEN`: bearer token for that endpoint.

The feed must return JSON in this format:

```json
{
  "videos": [
    {
      "id": "unique-source-video-id",
      "source_username": "jawad..382",
      "download_url": "https://your-authorized-host.example/video.mov",
      "source_url": "https://www.tiktok.com/@jawad..382/video/123",
      "permission_granted": true,
      "title": "Video title",
      "views": 12000,
      "likes": 900,
      "comments": 40,
      "attribution": "Shared with permission by @jawad..382",
      "hashtags": ["#ShortVideos", "#CreatorContent", "#ForYou", "#Trending", "#Pulsenama"]
    }
  ]
}
```

Only the seven allowlisted accounts and entries with `permission_granted: true` are accepted. Media URLs must be HTTPS and have a supported original extension. Files are saved without transcoding. Videos are deduplicated by the feed's stable `id`; a video is marked posted only after Buffer confirms queue creation.

**Platform limitation:** TikTok Display API's `video.list` returns metadata for the TikTok user who authorized the app; it is not a general downloader for arbitrary usernames and does not provide original video-file downloads. Each account owner must authorize access, and the feed adapter must supply an original file that the owner explicitly allows to be reposted. No scraping, access-control bypass, or watermark removal is used. See TikTok's [Display API overview](https://developers.tiktok.com/docs/en/display-api-overview/) and [authorization guide](https://developers.tiktok.com/docs/en/display-api-get-started/).
