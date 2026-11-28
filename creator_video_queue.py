#!/usr/bin/env python3
"""Fetch creator videos once daily and queue up to four distinct videos to Buffer."""
import json, os, random, re, subprocess, sys
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import requests
from yt_dlp import YoutubeDL

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"creator_videos"/"manifest.json"
STATE=ROOT/"creator_videos"/"posted.json"
INBOX=ROOT/"creator_videos"/"inbox"
ACCOUNTS=["khudserabtak","sultan_editx00","satisfyingbytiktok","ismail_wri8s_6","haya_aesticxs","hammadeditz_09","aesthatic_creator"]
# The repository owner confirmed repost permission for these configured creators.
AUTHORIZED_ACCOUNTS=set(ACCOUNTS)
TAGS=["#ShortVideos","#TrendingVideos","#ViralClips","#CreatorContent","#ForYou","#Pulsenama"]
VIDEO_EXTENSIONS={".mp4",".mov",".m4v",".webm",".mkv",".avi",".mpeg",".mpg",".3gp",".ts",".mts",".m2ts",".wmv",".flv"}
MAX_DOWNLOAD_BYTES=200*1024*1024
VIDEOS_PER_ACCOUNT=5
QUEUE_PER_RUN=4
PAKISTAN_TZ=ZoneInfo("Asia/Karachi")
PUBLISH_TIMES=[time(8,0),time(12,0),time(16,0),time(20,0)]

def read_json(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def fetch_account_videos():
    """Try public creator profile pages directly; no external feed URL/token is needed."""
    if os.getenv("ENABLE_ACCOUNT_SOURCE_FETCH","false").lower() not in {"1","true","yes","on"}:
        print("Account-source fetching is OFF (workflow input).")
        return
    manifest=read_json(MANIFEST,{"videos":[]})
    state=read_json(STATE,{"posted_ids":[]})
    posted={str(x) for x in state.get("posted_ids",[])}
    # Only treat a manifest entry as already downloaded when its local media file exists.
    # GitHub-hosted runners are ephemeral, so old inbox files are not present on later runs.
    known=set()
    for old in manifest.get("videos",[]):
        old_id=str(old.get("id") or "").strip()
        old_file=str(old.get("file") or "").strip()
        if not old_id or old_id in posted or not old_file: continue
        old_path=(ROOT/old_file).resolve()
        if ROOT.resolve() in old_path.parents and old_path.is_file() and old_path.stat().st_size>=100_000:
            known.add(old_id)
    existing_by_id={str(x.get("id")):x for x in manifest.get("videos",[]) if x.get("id")}
    INBOX.mkdir(parents=True,exist_ok=True)
    added=0
    for username in ACCOUNTS:
        # Public profile URLs are used for discovery only. Discovery does not grant repost rights.
        profile=f"https://www.tiktok.com/@{username}"
        print(f"[{username}] Scanning public profile: {profile}")
        opts={"quiet":True,"no_warnings":True,"extract_flat":"in_playlist","skip_download":True,
              "playlistend":20,"socket_timeout":25}
        try:
            with YoutubeDL(opts) as ydl:
                info=ydl.extract_info(profile,download=False)
            entries=(info or {}).get("entries") or []
        except Exception as exc:
            print(f"[{username}] Could not read public profile: {exc}")
            continue
        candidates=[]
        for entry in entries:
            if not entry: continue
            video_id=str(entry.get("id") or "").strip()
            if not video_id or video_id in known or video_id in posted: continue
            views=int(entry.get("view_count") or 0)
            likes=int(entry.get("like_count") or 0)
            comments=int(entry.get("comment_count") or 0)
            score=(max(views,0)**0.35)*(1+min((likes+2*comments)/max(views,1),1.0)*5)
            url=entry.get("url") or entry.get("webpage_url") or f"https://www.tiktok.com/@{username}/video/{video_id}"
            candidates.append((score,video_id,url,views,likes,comments,entry.get("title") or "Creator video"))
        candidates.sort(reverse=True,key=lambda x:x[0])
        for _,video_id,url,views,likes,comments,title in candidates[:VIDEOS_PER_ACCOUNT]:
            safe_id=re.sub(r"[^A-Za-z0-9_-]","_",f"{username}_{video_id}")
            outtmpl=str(INBOX/(safe_id+".%(ext)s"))
            try:
                dl_opts={"quiet":True,"no_warnings":True,"noplaylist":True,
                         # Exclude audio-only renditions; TikTok may expose an MP3 as "best".
                         "format":"best[ext=mp4][vcodec!=none]/best[vcodec!=none]/bestvideo+bestaudio/best[ext=mp4]/best",
                         "outtmpl":outtmpl,"max_filesize":MAX_DOWNLOAD_BYTES,"socket_timeout":45,
                         "merge_output_format":"mp4"}
                with YoutubeDL(dl_opts) as ydl:
                    video_info=ydl.extract_info(url,download=True)
                    filepath=Path(ydl.prepare_filename(video_info))
                    if not filepath.exists():
                        merged=filepath.with_suffix(".mp4")
                        if merged.exists(): filepath=merged
                if not filepath.exists() or filepath.suffix.lower() not in VIDEO_EXTENSIONS or filepath.stat().st_size<100_000:
                    print(f"[{username}] SKIP {video_id}: unsupported, missing, or too-small video.")
                    filepath.unlink(missing_ok=True)
                    continue
                # Prefer metrics returned by the full video extractor when flat profile metadata is incomplete.
                views=int(video_info.get("view_count") or views or 0)
                likes=int(video_info.get("like_count") or likes or 0)
                comments=int(video_info.get("comment_count") or comments or 0)
                title=str(video_info.get("title") or title or "Creator video")
                item={"id":video_id,"file":str(filepath.relative_to(ROOT)),"source_username":username,
                      "title":title,"views":views,"likes":likes,"comments":comments,
                      "permission_granted":True,
                      "hashtags":TAGS,"source_url":str(url)}
                # Replace stale manifest metadata for the same ID instead of adding duplicates.
                old=existing_by_id.get(video_id)
                if old is not None:
                    manifest["videos"].remove(old)
                manifest.setdefault("videos",[]).append(item)
                existing_by_id[video_id]=item
                known.add(video_id); added+=1
            except Exception as exc:
                print(f"[{username}] Could not download {video_id}: {exc}")
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Account scan complete: imported {added} video(s); downloaded formats are kept as provided.")

def choose_videos(limit=QUEUE_PER_RUN):
    """Return up to four best eligible, unposted videos, preferring creator rotation."""
    manifest=read_json(MANIFEST,{"videos":[]})
    state=read_json(STATE,{"posted_ids":[],"last_account":None})
    posted={str(x) for x in state.get("posted_ids",[])}
    candidates=[]
    for item in manifest.get("videos",[]):
        vid=str(item.get("id","")).strip()
        source=str(item.get("source_username","")).lstrip("@")
        relative_file=str(item.get("file","")).strip()
        if not vid or vid in posted or source not in ACCOUNTS or source not in AUTHORIZED_ACCOUNTS: continue
        if item.get("permission_granted") is not True or not relative_file: continue
        media=(ROOT/relative_file).resolve()
        if ROOT.resolve() not in media.parents: continue
        if not media.is_file() or media.suffix.lower() not in VIDEO_EXTENSIONS or media.stat().st_size<100_000: continue
        views=max(0,int(item.get("views",0) or 0))
        likes=max(0,int(item.get("likes",0) or 0))
        comments=max(0,int(item.get("comments",0) or 0))
        engagement=(likes+2*comments)/max(views,1)
        min_views=int(os.getenv("MIN_VIDEO_VIEWS","0"))
        min_engagement=float(os.getenv("MIN_VIDEO_ENGAGEMENT","0"))
        if views < min_views or engagement < min_engagement: continue
        score=(views**0.35)*(1+min(engagement,1.0)*5)
        candidates.append((score,item,media))
    candidates.sort(key=lambda x:x[0],reverse=True)
    print(f"Eligible downloaded videos: {len(candidates)}")
    selected=[]
    remaining=list(candidates)
    last=state.get("last_account")
    while remaining and len(selected)<limit:
        # Prefer a different creator from the previous selection whenever possible.
        different=[x for x in remaining if x[1].get("source_username") != last]
        pool=different or remaining
        chosen=pool[0]
        selected.append(chosen)
        remaining.remove(chosen)
        last=chosen[1].get("source_username")
    if len(selected)<limit:
        print(f"WARNING: Only {len(selected)} eligible unposted video(s) are available; target is {limit}.")
    return selected,state

def build_caption(item):
    title=str(item.get("title") or "Trending video").strip()
    # Keep the existing caption style; do not expose source handles or URLs.
    title=re.sub(r"@[A-Za-z0-9._]+","",title)
    for username in ACCOUNTS:
        title=re.sub(re.escape(username),"",title,flags=re.IGNORECASE)
    title=re.sub(r"\s+"," ",title).strip(" -|•")
    if not title: title="Trending video"
    hashtags=[("#"+str(t).lstrip("#")) for t in (item.get("hashtags") or TAGS) if str(t).strip()][:6]
    while len(hashtags)<5: hashtags.append(TAGS[len(hashtags)])
    return "\n".join([title," ".join(hashtags)])

def queue_one_video(item,media,key,channel,due_at):
    tag=f"creator-video-{re.sub(r'[^a-zA-Z0-9-]','-',str(item['id']))}"
    title=str(item.get("title") or "Trending video").strip()
    caption=build_caption(item)
    release_exists=subprocess.run(["gh","release","view",tag],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if release_exists:
        subprocess.run(["gh","release","upload",tag,str(media),"--clobber"],check=True)
        print(f"Reused existing GitHub release: {tag}")
    else:
        subprocess.run(["gh","release","create",tag,str(media),"--title",title[:100],"--notes",""],check=True)
    repo=os.getenv("GITHUB_REPOSITORY","")
    url=f"https://github.com/{repo}/releases/download/{tag}/{media.name}"
    query=f"""
    mutation CreatePost {{
      createPost(input: {{
        text: {json.dumps(caption,ensure_ascii=False)}
        channelId: {json.dumps(channel)}
        schedulingType: automatic
        mode: customScheduled
        dueAt: {json.dumps(due_at)}
        metadata: {{ facebook: {{ type: reel }} }}
        assets: [{{ video: {{ url: {json.dumps(url)} }} }}]
      }}) {{
        ... on PostActionSuccess {{ post {{ id dueAt status }} }}
        ... on MutationError {{ message }}
      }}
    }}
    """
    response=requests.post("https://api.buffer.com",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"query":query},timeout=60)
    response.raise_for_status()
    payload=response.json()
    if payload.get("errors"): raise RuntimeError(json.dumps(payload["errors"]))
    result=(payload.get("data") or {}).get("createPost") or {}
    post=result.get("post")
    if not post: raise RuntimeError(result.get("message") or "Buffer did not confirm the post.")
    print(f"Queued creator video {item['id']} from @{item['source_username']}; Buffer post {post.get('id')}; dueAt={post.get('dueAt')}.")
    return post

def main():
    fetch_account_videos()
    if os.getenv("ENABLE_BUFFER_POSTING","true").lower() not in {"1","true","yes","on"}:
        print("Buffer posting is OFF; videos were not queued.")
        return 0
    key=os.getenv("BUFFER_API_KEY","").strip()
    channel=os.getenv("BUFFER_CHANNEL_ID","").strip()
    if not key or not channel:
        raise RuntimeError(
            "Buffer credentials are missing: configure BUFFER_API_KEY and BUFFER_CHANNEL_ID "
            "in GitHub Actions secrets. Refusing to report a successful run without queueing."
        )
    selected,state=choose_videos(QUEUE_PER_RUN*len(ACCOUNTS))
    if not selected:
        print("No eligible videos found; nothing was added to Buffer.")
        return 0
    queued=0
    now=datetime.now(PAKISTAN_TZ)
    publish_slots=[]
    # Allocate the next four fixed Pakistan-time slots. On a normal 06:00 run,
    # all four slots are today at 08:00, 12:00, 16:00 and 20:00.
    for day_offset in range(8):
        day=(now+timedelta(days=day_offset)).date()
        for slot in PUBLISH_TIMES:
            local_dt=datetime.combine(day,slot,tzinfo=PAKISTAN_TZ)
            if local_dt > now + timedelta(minutes=2):
                publish_slots.append(local_dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"))
            if len(publish_slots)>=len(selected):
                break
        if len(publish_slots)>=len(selected):
            break
    for _,item,media in selected:
        if queued>=QUEUE_PER_RUN:
            break
        try:
            # If one source file or release upload fails, use the next ranked
            # eligible video and keep the next unfilled Buffer slot.
            due_at=publish_slots[queued]
            post=queue_one_video(item,media,key,channel,due_at)
            state.setdefault("posted_ids",[]).append(str(item["id"]))
            state["last_account"]=item.get("source_username")
            state["last_post_id"]=post.get("id")
            queued+=1
            # Persist after every Buffer confirmation so a later failure cannot lose history.
            STATE.parent.mkdir(parents=True,exist_ok=True)
            STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        except Exception as exc:
            print(f"FAILED to queue video {item.get('id')}: {exc}",file=sys.stderr)
    print(f"Daily batch complete: {queued}/{QUEUE_PER_RUN} videos confirmed in Buffer.")
    print("Pakistan publishing slots: 08:00, 12:00, 16:00, 20:00 (Asia/Karachi).")
    if queued<QUEUE_PER_RUN:
        print("ACTION REQUIRED: Check scan/download errors above, available fresh videos, and Buffer/GitHub configuration.")
    return 0 if queued==QUEUE_PER_RUN else 1

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(f"Creator video workflow failed: {exc}",file=sys.stderr)
        raise
