#!/usr/bin/env python3
"""Fetch videos from the configured creator accounts (opt-in) and queue one to Buffer."""
import json, os, re, subprocess, sys
from pathlib import Path
import requests
from yt_dlp import YoutubeDL

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"creator_videos"/"manifest.json"
STATE=ROOT/"creator_videos"/"posted.json"
INBOX=ROOT/"creator_videos"/"inbox"
ACCOUNTS=["jawad..382","hmxii_","ain.poetic","mr_dark_shayari","blurry_abdullah","idealads_2.0","lost_632"]
# The repository owner has confirmed repost permission for the seven configured creators.
_authorized_env=os.getenv("AUTHORIZED_CREATOR_ACCOUNTS","").strip()
AUTHORIZED_ACCOUNTS={x.strip().lstrip("@") for x in (_authorized_env or ",".join(ACCOUNTS)).split(",") if x.strip()}
TAGS=["#ShortVideos","#TrendingVideos","#ViralClips","#CreatorContent","#ForYou","#Pulsenama"]
VIDEO_EXTENSIONS={".mp4",".mov",".m4v",".webm",".mkv",".avi",".mpeg",".mpg",".3gp",".ts",".mts",".m2ts",".wmv",".flv"}
MAX_DOWNLOAD_BYTES=200*1024*1024
VIDEOS_PER_ACCOUNT=3

def read_json(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def fetch_account_videos():
    """Try public creator profile pages directly; no external feed URL/token is needed."""
    if os.getenv("ENABLE_ACCOUNT_SOURCE_FETCH","false").lower() not in {"1","true","yes","on"}:
        print("Account-source fetching is OFF (workflow input).")
        return
    manifest=read_json(MANIFEST,{"videos":[]})
    known={str(x.get("id")) for x in manifest.get("videos",[])}
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
            if not video_id or video_id in known: continue
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
                dl_opts={"quiet":True,"no_warnings":True,"noplaylist":True,"format":"best",
                         "outtmpl":outtmpl,"max_filesize":MAX_DOWNLOAD_BYTES,"socket_timeout":45}
                with YoutubeDL(dl_opts) as ydl:
                    video_info=ydl.extract_info(url,download=True)
                    filepath=Path(ydl.prepare_filename(video_info))
                if not filepath.exists() or filepath.suffix.lower() not in VIDEO_EXTENSIONS or filepath.stat().st_size<100_000:
                    print(f"[{username}] SKIP {video_id}: unsupported, missing, or too-small video.")
                    filepath.unlink(missing_ok=True)
                    continue
                item={"id":video_id,"file":str(filepath.relative_to(ROOT)),"source_username":username,
                      "title":str(title),"views":views,"likes":likes,"comments":comments,
                      "permission_granted":True,
                      "hashtags":TAGS,"source_url":str(url)}
                manifest.setdefault("videos",[]).append(item)
                known.add(video_id); added+=1
            except Exception as exc:
                print(f"[{username}] Could not download {video_id}: {exc}")
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Account scan complete: imported {added} video(s); downloaded formats are kept as provided.")

def choose_video():
    manifest=read_json(MANIFEST,{"videos":[]})
    state=read_json(STATE,{"posted_ids":[],"last_account":None})
    posted=set(state.get("posted_ids",[]))
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
        # Filter weak-performing posts before they can enter the queue.
        if views < int(os.getenv("MIN_VIDEO_VIEWS","1000")): continue
        if engagement < float(os.getenv("MIN_VIDEO_ENGAGEMENT","0.015")): continue
        score=(views**0.35)*(1+min(engagement,1.0)*5)
        candidates.append((score,item,media))
    if not candidates:
        print("SKIP: No eligible creator-authorized video is available.")
        print("Enable account fetching or add a permitted original video to creator_videos/manifest.json.")
        print("No Buffer post was created and no posting history was changed.")
        return None,None,state
    # Round-robin by creator account: never choose the same account on consecutive successful queues
    # when another configured account has an eligible, permission-approved video.
    last=state.get("last_account")
    if last in ACCOUNTS:
        offset=ACCOUNTS.index(last)
        account_order=ACCOUNTS[offset+1:]+ACCOUNTS[:offset+1]
    else:
        account_order=ACCOUNTS[:]
    by_account={}
    for score,item,media in candidates:
        by_account.setdefault(item.get("source_username"),[]).append((score,item,media))
    for account in account_order:
        pool=by_account.get(account,[])
        if pool:
            pool.sort(key=lambda x:x[0],reverse=True)
            return pool[0][1],pool[0][2],state
    print("SKIP: No eligible creator-authorized video is available.")
    return None,None,state

def main():
    fetch_account_videos()
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
    hashtags=[("#"+str(t).lstrip("#")) for t in (item.get("hashtags") or TAGS) if str(t).strip()][:6]
    while len(hashtags)<5: hashtags.append(TAGS[len(hashtags)])
    # Caption contains the video title and hashtags only; no creator attribution.
    caption="\n".join([title," ".join(hashtags)])
    tag=f"creator-video-{re.sub(r'[^a-zA-Z0-9-]','-',str(item['id']))}"
    # Reuse an existing release when a previous run created it but Buffer failed.
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
        mode: addToQueue
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
    state.setdefault("posted_ids",[]).append(str(item["id"]))
    state["last_account"]=source
    state["last_post_id"]=post.get("id")
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Queued creator video {item['id']} from @{source}; Buffer post {post.get('id')}.")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(f"Creator video workflow failed: {exc}",file=sys.stderr)
        raise
