#!/usr/bin/env python3
"""Queue one creator-authorized short video to Buffer; never downloads from TikTok."""
import json, mimetypes, os, re, subprocess, sys
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"creator_videos"/"manifest.json"
STATE=ROOT/"creator_videos"/"posted.json"
ACCOUNTS=["jawad..382","hmxii_","ain.poetic","mr_dark_shayari","blurry_abdullah","idealads_2.0","lost_632"]
TAGS=["#ShortVideos","#TrendingVideos","#ViralClips","#CreatorContent","#ForYou","#Pulsenama"]
# Keep creator-provided files in their original format; no forced MP4 conversion.
VIDEO_EXTENSIONS={".mp4",".mov",".m4v",".webm",".mkv",".avi",".mpeg",".mpg",".3gp",".ts",".mts",".m2ts",".wmv",".flv"}

def read_json(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def choose_video():
    manifest=read_json(MANIFEST, {"videos":[]})
    state=read_json(STATE, {"posted_ids":[],"last_account":None})
    posted=set(state.get("posted_ids",[]))
    candidates=[]
    for item in manifest.get("videos",[]):
        vid=str(item.get("id","")).strip()
        source=str(item.get("source_username","")).lstrip("@")
        relative_file=str(item.get("file","")).strip()
        if not vid or vid in posted or source not in ACCOUNTS: continue
        if item.get("permission_granted") is not True: continue
        if not relative_file: continue
        media=(ROOT/relative_file).resolve()
        # Accept creator-supplied media anywhere inside this repository; preserve its original format.
        # The manifest remains the authorization gate, so random repository files are never auto-posted.
        repo_root=ROOT.resolve()
        if repo_root not in media.parents: continue
        if not media.is_file() or media.suffix.lower() not in VIDEO_EXTENSIONS: continue
        if media.stat().st_size < 100_000: continue
        views=max(0,int(item.get("views",0) or 0))
        likes=max(0,int(item.get("likes",0) or 0))
        comments=max(0,int(item.get("comments",0) or 0))
        engagement=(likes+2*comments)/max(views,1)
        score=(views**0.35)*(1+min(engagement,1.0)*5)
        candidates.append((score,item,media))
    if not candidates:
        print("SKIP: No eligible creator-authorized video is available.")
        found=[]
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and ".git" not in path.parts:
                found.append(str(path.relative_to(ROOT)))
        if found:
            print("Video file(s) found in repository but not eligible: " + ", ".join(found[:20]))
            print("Add the exact relative path to creator_videos/manifest.json and confirm source_username + permission_granted=true.")
        else:
            print("No supported video file exists anywhere in the checked-out repository.")
            print("Upload the creator-authorized source video in its original format anywhere in the repository, then add its exact path to creator_videos/manifest.json.")
        print("Supported formats: " + ", ".join(sorted(VIDEO_EXTENSIONS)))
        print("No Buffer post was created and no posting history was changed.")
        return None, None, state
    last=state.get("last_account")
    # Rotate accounts when possible; within the eligible rotation choose the strongest engagement/reach score.
    fresh=[x for x in candidates if x[1].get("source_username") != last]
    pool=fresh or candidates
    pool.sort(key=lambda x:x[0],reverse=True)
    return pool[0][1],pool[0][2],state

def main():
    key=os.getenv("BUFFER_API_KEY","").strip()
    channel=os.getenv("BUFFER_CHANNEL_ID","").strip()
    if not key or not channel:
        print("Buffer skipped: BUFFER_API_KEY / BUFFER_CHANNEL_ID are not configured.")
        return 0
    item,media,state=choose_video()
    if item is None:
        return 0
    source=item["source_username"]
    title=str(item.get("title") or "Creator video").strip()
    attribution=str(item.get("attribution") or f"Video shared with permission by @{source}").strip()
    hashtags=item.get("hashtags") or TAGS
    hashtags=[("#"+str(t).lstrip("#")) for t in hashtags if str(t).strip()][:6]
    while len(hashtags)<5: hashtags.append(TAGS[len(hashtags)])
    caption="\n".join([title,attribution," ".join(hashtags)])
    tag=f"creator-video-{re.sub(r'[^a-zA-Z0-9-]','-',str(item['id']))}"
    # Upload the original file unchanged; keep its original extension and container.
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
    print(f"Queued authorized video {item['id']} from @{source}; Buffer post {post.get('id')}.")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(f"Creator video workflow failed: {exc}",file=sys.stderr)
        raise
