#!/usr/bin/env python3
"""Fetch creator-authorized source-feed videos (opt-in), then queue one to Buffer."""
import json, mimetypes, os, re, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"creator_videos"/"manifest.json"
STATE=ROOT/"creator_videos"/"posted.json"
INBOX=ROOT/"creator_videos"/"inbox"
ACCOUNTS=["jawad..382","hmxii_","ain.poetic","mr_dark_shayari","blurry_abdullah","idealads_2.0","lost_632"]
TAGS=["#ShortVideos","#TrendingVideos","#ViralClips","#CreatorContent","#ForYou","#Pulsenama"]
VIDEO_EXTENSIONS={".mp4",".mov",".m4v",".webm",".mkv",".avi",".mpeg",".mpg",".3gp",".ts",".mts",".m2ts",".wmv",".flv"}
MAX_DOWNLOAD_BYTES=200*1024*1024

def read_json(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def fetch_authorized_feed():
    """Optional connector contract: a creator-authorized feed returns direct original-media URLs."""
    if os.getenv("ENABLE_ACCOUNT_SOURCE_FETCH","false").lower() not in {"1","true","yes","on"}:
        print("Account-source intake is OFF (workflow input).")
        return
    feed_url=os.getenv("CREATOR_SOURCE_FEED_URL","").strip()
    token=os.getenv("CREATOR_SOURCE_FEED_TOKEN","").strip()
    if not feed_url or not token:
        raise RuntimeError("Account-source intake is ON but CREATOR_SOURCE_FEED_URL / CREATOR_SOURCE_FEED_TOKEN secrets are missing.")
    parsed=urlparse(feed_url)
    if parsed.scheme!="https" or not parsed.hostname:
        raise RuntimeError("CREATOR_SOURCE_FEED_URL must be an HTTPS endpoint.")
    response=requests.get(feed_url,headers={"Authorization":f"Bearer {token}","Accept":"application/json"},timeout=45)
    response.raise_for_status()
    payload=response.json()
    entries=payload.get("videos",[])
    manifest=read_json(MANIFEST,{"videos":[]})
    known={str(x.get("id")) for x in manifest.get("videos",[])}
    INBOX.mkdir(parents=True,exist_ok=True)
    added=0
    for entry in entries:
        vid=str(entry.get("id","")).strip()
        source=str(entry.get("source_username","")).lstrip("@")
        media_url=str(entry.get("download_url","")).strip()
        if not vid or vid in known or source not in ACCOUNTS: continue
        if entry.get("permission_granted") is not True:
            print(f"SKIP {vid}: source feed did not confirm creator permission.")
            continue
        parsed_media=urlparse(media_url)
        if parsed_media.scheme!="https" or not parsed_media.hostname:
            print(f"SKIP {vid}: media URL must use HTTPS.")
            continue
        ext=Path(parsed_media.path).suffix.lower()
        if ext not in VIDEO_EXTENSIONS:
            print(f"SKIP {vid}: unsupported or missing original file extension ({ext or 'none'}).")
            continue
        target=INBOX/(re.sub(r"[^A-Za-z0-9_-]","_",vid)+ext)
        if not target.exists():
            with requests.get(media_url,stream=True,timeout=90) as media:
                media.raise_for_status()
                length=int(media.headers.get("Content-Length","0") or 0)
                if length>MAX_DOWNLOAD_BYTES: raise RuntimeError(f"Video {vid} exceeds 200 MB limit.")
                total=0
                with target.open("wb") as out:
                    for chunk in media.iter_content(1024*1024):
                        if not chunk: continue
                        total+=len(chunk)
                        if total>MAX_DOWNLOAD_BYTES:
                            target.unlink(missing_ok=True)
                            raise RuntimeError(f"Video {vid} exceeds 200 MB limit.")
                        out.write(chunk)
                if total<100_000:
                    target.unlink(missing_ok=True)
                    print(f"SKIP {vid}: downloaded file is too small.")
                    continue
        item={
            "id":vid,"file":str(target.relative_to(ROOT)),"source_username":source,
            "title":str(entry.get("title") or "Creator video"),
            "views":int(entry.get("views",0) or 0),"likes":int(entry.get("likes",0) or 0),
            "comments":int(entry.get("comments",0) or 0),"permission_granted":True,
            "attribution":str(entry.get("attribution") or f"Shared with permission by @{source}"),
            "hashtags":entry.get("hashtags") or TAGS,
            "source_url":str(entry.get("source_url") or "")
        }
        manifest.setdefault("videos",[]).append(item)
        known.add(vid); added+=1
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Authorized source feed: imported {added} new video(s); original formats preserved.")

def choose_video():
    manifest=read_json(MANIFEST,{"videos":[]})
    state=read_json(STATE,{"posted_ids":[],"last_account":None})
    posted=set(state.get("posted_ids",[]))
    candidates=[]
    for item in manifest.get("videos",[]):
        vid=str(item.get("id","")).strip()
        source=str(item.get("source_username","")).lstrip("@")
        relative_file=str(item.get("file","")).strip()
        if not vid or vid in posted or source not in ACCOUNTS: continue
        if item.get("permission_granted") is not True or not relative_file: continue
        media=(ROOT/relative_file).resolve()
        if ROOT.resolve() not in media.parents: continue
        if not media.is_file() or media.suffix.lower() not in VIDEO_EXTENSIONS or media.stat().st_size<100_000: continue
        views=max(0,int(item.get("views",0) or 0))
        likes=max(0,int(item.get("likes",0) or 0))
        comments=max(0,int(item.get("comments",0) or 0))
        engagement=(likes+2*comments)/max(views,1)
        score=(views**0.35)*(1+min(engagement,1.0)*5)
        candidates.append((score,item,media))
    if not candidates:
        print("SKIP: No eligible creator-authorized video is available.")
        print("Add an authorized feed endpoint or upload an original video and list it in creator_videos/manifest.json.")
        print("No Buffer post was created and no posting history was changed.")
        return None,None,state
    last=state.get("last_account")
    fresh=[x for x in candidates if x[1].get("source_username")!=last]
    pool=fresh or candidates
    pool.sort(key=lambda x:x[0],reverse=True)
    return pool[0][1],pool[0][2],state

def main():
    fetch_authorized_feed()
    if os.getenv("ENABLE_BUFFER_POSTING","true").lower() not in {"1","true","yes","on"}:
        print("Buffer posting is OFF (workflow input); videos were not queued.")
        return 0
    key=os.getenv("BUFFER_API_KEY","").strip()
    channel=os.getenv("BUFFER_CHANNEL_ID","").strip()
    if not key or not channel:
        print("Buffer skipped: BUFFER_API_KEY / BUFFER_CHANNEL_ID are not configured.")
        return 0
    item,media,state=choose_video()
    if item is None: return 0
    source=item["source_username"]
    title=str(item.get("title") or "Creator video").strip()
    attribution=str(item.get("attribution") or f"Video shared with permission by @{source}").strip()
    hashtags=[("#"+str(t).lstrip("#")) for t in (item.get("hashtags") or TAGS) if str(t).strip()][:6]
    while len(hashtags)<5: hashtags.append(TAGS[len(hashtags)])
    caption="\n".join([title,attribution," ".join(hashtags)])
    tag=f"creator-video-{re.sub(r'[^a-zA-Z0-9-]','-',str(item['id']))}"
    subprocess.run(["gh","release","create",tag,str(media),"--title",title[:100],"--notes",attribution],check=True)
    repo=os.getenv("GITHUB_REPOSITORY","")
    url=f"https://github.com/{repo}/releases/download/{tag}/{media.name}"
    query=f"""
    mutation CreatePost {{
      createPost(input: {{
        text: {json.dumps(caption,ensure_ascii=False)}
        channelId: {json.dumps(channel)}
        schedulingType: automatic
        mode: addToQueue
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
    state.setdefault("posted_ids",[]).append(str(item["id"]))
    state["last_account"]=source
    state["last_post_id"]=post.get("id")
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Queued authorized video {item['id']} from @{source}; Buffer post {post.get('id')}.")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(f"Creator video workflow failed: {exc}",file=sys.stderr)
        raise
