# Creator video queue

The repository's only automation is the authorized creator-video fetch and Buffer queue.

## Required GitHub Actions settings

Repository variables:
- `ENABLE_ACCOUNT_SOURCE_FETCH=true` to scan creator profiles on the scheduled run.
- `ENABLE_BUFFER_POSTING=true` to allow Buffer queueing.
- `AUTHORIZED_CREATOR_ACCOUNTS` — comma-separated usernames for which you have explicit permission to repost. Only these configured accounts are scanned and eligible for posting.

Repository secrets:
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

## Configured creator profiles

- `jawad..382`
- `hmxii_`
- `ain.poetic`
- `mr_dark_shayari`
- `blurry_abdullah`
- `idealads_2.0`
- `lost_632`

The system ranks available videos by views and engagement, preserves the downloaded source format without transcoding, skips previously posted IDs, and records a video as posted only after Buffer confirms queue creation.

**Permission safeguard:** a public profile is not proof of repost permission. The system will not scan or queue an account unless its username is explicitly included in `AUTHORIZED_CREATOR_ACCOUNTS`. It does not bypass private-account restrictions or access controls.
