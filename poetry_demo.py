#!/usr/bin/env python3
"""Standalone, manual-only cinematic poetry demo. Never publishes to Buffer."""
import json, os, re, subprocess, sys, math, random, wave, struct, time
# Force poetry-only operation; ignore any stale Qawwali mode environment setting.
os.environ.pop("VIDEO_MODE_OVERRIDE", None)
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 24
KEY=os.getenv("OPENROUTER_API_KEY","").strip()
PEXELS=os.getenv("PEXELS_API_KEY","").strip()
PIXABAY=os.getenv("PIXABAY_API_KEY","").strip()
MODEL=os.getenv("OPENROUTER_MODEL","openrouter/free")
# Automatically choose creative settings; no workflow questions.
MOOD=random.choice(["sad","romantic","motivational","deep","peaceful","rain","memories"])
# Pakistan schedule: 9 AM, 12 PM, 6 PM Urdu; 3 PM Punjabi; 9 PM English.
SCHEDULE_CRON=os.getenv("SCHEDULE_CRON","").strip()
# Poetry-only mode: Qawwali generation is removed and disabled.
def scheduled_language():
    if os.getenv("GITHUB_EVENT_NAME") == "schedule":
        if SCHEDULE_CRON == "0 10 * * *":
            return "Punjabi"
        if SCHEDULE_CRON == "0 16 * * *":
            return "English"
        return "Urdu"
    return "Urdu"

LANG=scheduled_language()
DURATION=random.choice([18,20,22,24])
OUT,WORK=Path("poetry_demo.mp4"),Path("poetry_demo_work")
WORK.mkdir(exist_ok=True)

def run(cmd): subprocess.run(cmd,check=True)

def fallback_poem():
    """Original local fallback so a temporary AI/API response issue does not stop the demo."""
    poems = {
      "Urdu": {
        "sad": ("خاموش رات", ["بارش میں تیری یاد آئی، دل پھر خاموش ہو گیا", "جو خواب کبھی اپنا تھا، آج دھند میں کھو گیا"]),
        "deep": ("خاموش سوال", ["خاموشی بھی کبھی دل کی صدا بن جاتی ہے", "جو بات کہہ نہ سکیں، وہ دعا بن جاتی ہے"]),
        "peaceful": ("سکون کا لمحہ", ["ہوا کے ساتھ کچھ خواب بہنے دو", "آج دل کو ذرا سکون سے رہنے دو"]),
      },
      "Roman Urdu": {
        "sad": ("Khamosh Raat", ["Barish mein teri yaad phir laut aayi", "Khamosh dil ne bas teri sada lagayi"]),
        "deep": ("Khamosh Sawal", ["Khamoshi mein bhi ek awaaz hoti hai", "Har raat ke baad nayi subah hoti hai"]),
        "peaceful": ("Sukoon Ka Lamha", ["Hawa se keh do zara dheere chale", "Aaj dil ko apne khayalon mein rehne de"]),
      },
      "Punjabi": {
        "sad": ("ادھوریاں یاداں", ["کجھ یاداں دل وچ وسدیاں رہندیاں نیں", "کجھ لوک دور ہو کے وی کول رہندے نیں"]),
        "deep": ("دل دی گل", ["خاموشی وی کئی وار سب کجھ کہہ جاندی اے", "دل دی ہر گل لفظاں وچ نہیں آندی"]),
        "peaceful": ("سکون دا ویلا", ["ہولی ہولی ہوا نال خواب سجاؤن دے", "اج دل نوں اپنے حال وچ مسکراؤن دے"]),
      },
      "English": {
        "sad": ("After the Rain", ["Some memories still whisper in the rain", "Some goodbyes keep echoing again"]),
        "deep": ("Quiet Questions", ["The quiet holds what words cannot say", "Even the darkest night gives way"]),
        "peaceful": ("A Gentle Moment", ["Let the world grow quiet for a while", "And let your tired heart learn to smile"]),
      }
    }
    lang = LANG if LANG in poems else "English"
    mood = MOOD if MOOD in poems[lang] else ("peaceful" if MOOD in ("romantic","peaceful") else ("deep" if MOOD in ("motivational","deep") else "sad"))
    title, lines = poems[lang][mood]
    print("Using built-in original poem fallback; AI response was unavailable or invalid.")
    return title, lines

def make_poem():
    if not KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY GitHub secret.")
    prompt=f"""Create text for a {MOOD} cinematic vertical poetry video in {LANG}.
Randomly choose ONE format: (A) a beautiful original 2-3 line poem, (B) a memorable quote, or (C) a famous, accurately attributed public-domain literary/poetry line.
Use well-known poets/writers where appropriate, but NEVER invent a famous author or falsely attribute words. If unsure of exact wording or attribution, write an original line instead.
Return ONLY valid JSON: {{"title":"short title","lines":["short line 1","short line 2","optional short attribution or third line"]}}.
Use 2 or 3 short lines total, emotionally strong and easy to read on a phone. No paragraphs, no explanations, no decorative quote marks, no emojis. Keep every line concise enough to fit on a 1080x1920 video. For Urdu, write proper Urdu script. For Punjabi, write natural Pakistani Punjabi in Shahmukhi script (not Hindi or Gurmukhi). For English, write natural English."""
    try:
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",
          headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"},
          json={"model":MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.75,"max_tokens":500},timeout=90)
        r.raise_for_status()
        payload=r.json()
        choices=payload.get("choices") or []
        message=choices[0].get("message") if choices else None
        content=message.get("content") if isinstance(message,dict) else None
        if isinstance(content,list):
            content="\n".join(str(part.get("text","")) for part in content if isinstance(part,dict))
        if not isinstance(content,str) or not content.strip():
            reason=(choices[0].get("finish_reason") if choices else None) or payload.get("error") or "empty AI content"
            print(f"OpenRouter returned no poem text ({reason}); switching to fallback.")
            return fallback_poem()
        raw=content.strip()
        if raw.startswith("```"):
            raw=raw.split("\\n",1)[1] if "\\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw=raw[:-3].strip()
        data=json.loads(raw)
        lines=[str(x).strip() for x in data.get("lines",[]) if str(x).strip()]
        if len(lines)<2:
            print("OpenRouter returned fewer than four lines; switching to fallback.")
            return fallback_poem()
        return str(data.get("title") or "")[:80],lines[:3]
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"OpenRouter poem request failed ({exc}); switching to fallback.")
        return fallback_poem()

BACKGROUND_CREDIT = "Source details unavailable"

def mood_search_terms():
    # Rotate through photographic subjects so consecutive videos do not reuse one look.
    choices = {
      "sad":["moody rainy street photography night reflections","misty forest cinematic photography","rain on window city lights photography"],
      "romantic":["golden hour ocean sunset photography","soft pink sky wildflowers cinematic photography","romantic mountain lake sunset landscape photo"],
      "motivational":["dramatic sunrise mountain landscape photography","golden sunlight ocean cliffs photography","winding mountain road sunrise cinematic photo"],
      "deep":["starry sky mountains long exposure photography","dramatic cloudy mountains fine art landscape","moonlit ocean night photography"],
      "peaceful":["misty lake forest morning photography","calm turquoise ocean aerial landscape photo","sunlight through green forest nature photography"],
      "rain":["rainy city street reflections cinematic photography","misty mountain rain landscape photography","rain drops on glass blurred city lights photo"],
      "memories":["old European street golden hour photography","vintage countryside road sunset photo","nostalgic seaside town film photography"],
      "spiritual":["Sufi dargah illuminated courtyard night cinematic video","Sufi sama devotional gathering architecture","traditional South Asian shrine courtyard evening lights"],
    }
    return random.choice(choices.get(MOOD, ["cinematic nature landscape photography","fine art mountain landscape photo"]))

def get_pexels_video():
    """Return a mood-matched portrait Pexels video, or None if unavailable."""
    if not PEXELS:
        print("No PEXELS_API_KEY; moving to online image sources.")
        return None
    try:
        r=requests.get("https://api.pexels.com/videos/search",
          headers={"Authorization":PEXELS},
          params={"query":mood_search_terms(),"orientation":"portrait","per_page":12},timeout=30)
        r.raise_for_status()
        choices=[]
        for video in r.json().get("videos",[]):
            for item in video.get("video_files",[]):
                if item.get("link") and item.get("file_type")=="video/mp4":
                    vw,vh=int(item.get("width") or 0),int(item.get("height") or 0)
                    if vh>=720 and vh>vw:
                        choices.append((vw*vh,item["link"]))
        if not choices:
            print("No suitable portrait Pexels video found.")
            return None
        path=WORK/"background.mp4"
        with requests.get(max(choices)[1],stream=True,timeout=90) as response:
            response.raise_for_status()
            with path.open("wb") as out:
                for chunk in response.iter_content(1024*1024):
                    if chunk: out.write(chunk)
        if path.stat().st_size<100000:
            path.unlink(missing_ok=True)
            return None
        print("Using mood-matched portrait video from Pexels.")
        return path
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Pexels video search failed; trying images: {exc}")
        return None


def get_pixabay_video():
    """Fetch a mood-matched, portrait Pixabay video and record its creator/source."""
    global BACKGROUND_CREDIT
    if not PIXABAY:
        print("No PIXABAY_API_KEY; skipping Pixabay video search.")
        return None
    try:
        r=requests.get("https://pixabay.com/api/videos/",
          params={"key":PIXABAY,"q":mood_search_terms(),"video_type":"film",
                  "safesearch":"true","per_page":20},timeout=30)
        r.raise_for_status()
        hits=r.json().get("hits",[])
        random.shuffle(hits)
        choices=[]
        for hit in hits:
            files=hit.get("videos") or {}
            for quality in ("large","medium","small","tiny"):
                item=files.get(quality) or {}
                url=item.get("url")
                vw,vh=int(item.get("width") or 0),int(item.get("height") or 0)
                if url and vh>=600 and vh>vw:
                    choices.append((vw*vh,hit,item))
                    break
        if not choices:
            print("No suitable portrait Pixabay video found.")
            return None
        # Prefer the largest portrait version, while shuffling equal-sized candidates.
        choices.sort(key=lambda x:x[0],reverse=True)
        for _,hit,item in choices:
            try:
                path=WORK/"background.mp4"
                with requests.get(item["url"],stream=True,timeout=90) as response:
                    response.raise_for_status()
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size<100000:
                    path.unlink(missing_ok=True)
                    continue
                creator=hit.get("user","Pixabay contributor")
                page=hit.get("pageURL","https://pixabay.com/videos/")
                BACKGROUND_CREDIT=f"Pixabay video by {creator} | {page}"
                print(f"Using mood-matched portrait Pixabay video by {creator}.")
                return path
            except (requests.RequestException,OSError) as exc:
                print(f"Pixabay video candidate failed; trying another: {exc}")
                path.unlink(missing_ok=True)
                continue
    except (requests.RequestException,ValueError,KeyError) as exc:
        print(f"Pixabay video search failed; trying other sources: {exc}")
    return None



def get_archive_video():
    """Fetch a random non-performance moving background clip from Internet Archive (no API key)."""
    global BACKGROUND_CREDIT
    # Keep visuals generic and separate from the Qawwal/audio performance.
    visual_terms = {
        "spiritual": ["Sufi shrine courtyard", "dargah night lights", "Islamic architecture courtyard", "Sufi devotional gathering"],
        "peaceful": ["Sufi shrine courtyard", "dargah evening lights", "Islamic architecture"]
    }
    term = random.choice(visual_terms.get(MOOD, ["nature landscape", "ocean waves", "forest river"]))
    try:
        search = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f'mediatype:movies AND (title:("{term}") OR description:("{term}"))',
                "fl[]": ["identifier", "title"],
                "rows": 35,
                "page": 1,
                "output": "json"
            },
            timeout=35
        )
        search.raise_for_status()
        docs = (search.json().get("response") or {}).get("docs") or []
        random.shuffle(docs)
        for doc in docs:
            identifier = doc.get("identifier")
            if not identifier:
                continue
            try:
                meta_response = requests.get(
                    "https://archive.org/metadata/" + requests.utils.quote(identifier, safe=""),
                    timeout=35
                )
                meta_response.raise_for_status()
                files = (meta_response.json().get("files") or [])
                mp4s = [
                    item for item in files
                    if str(item.get("name", "")).lower().endswith(".mp4")
                    and int(item.get("size") or 0) > 250000
                    and not item.get("private")
                ]
                random.shuffle(mp4s)
                for item in mp4s[:4]:
                    filename = item["name"]
                    from urllib.parse import quote
                    url = "https://archive.org/download/" + quote(identifier, safe="") + "/" + quote(filename, safe="/")
                    path = WORK / "background.mp4"
                    try:
                        with requests.get(url, stream=True, timeout=100) as response:
                            response.raise_for_status()
                            with path.open("wb") as output:
                                for chunk in response.iter_content(1024 * 1024):
                                    if chunk:
                                        output.write(chunk)
                        if path.stat().st_size < 200000:
                            path.unlink(missing_ok=True)
                            continue
                        probe = subprocess.run(
                            ["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_entries", "stream=codec_type,width,height",
                             "-of", "json", str(path)],
                            capture_output=True, text=True, timeout=30, check=True
                        )
                        streams = json.loads(probe.stdout).get("streams", [])
                        if not streams or not any(x.get("codec_type") == "video" for x in streams):
                            path.unlink(missing_ok=True)
                            continue
                        title = doc.get("title", identifier)
                        BACKGROUND_CREDIT = (
                            "Internet Archive: " + str(title) +
                            " | https://archive.org/details/" + identifier
                        )
                        print("Using random moving background video from Internet Archive: " + str(title))
                        return path
                    except (requests.RequestException, OSError, ValueError, subprocess.SubprocessError) as exc:
                        print(f"Internet Archive video candidate failed; trying another: {exc}")
                        path.unlink(missing_ok=True)
            except (requests.RequestException, ValueError, KeyError) as exc:
                print(f"Internet Archive metadata lookup failed; trying another item: {exc}")
        print("Internet Archive returned no usable moving background video for this search.")
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f"Internet Archive video search failed: {exc}")
    return None

def get_pixabay_image():
    """Fetch a real, mood-matched portrait photo from Pixabay."""
    global BACKGROUND_CREDIT
    if not PIXABAY:
        print("No PIXABAY_API_KEY; skipping Pixabay photo search.")
        return None
    try:
        r=requests.get("https://pixabay.com/api/",
          params={"key":PIXABAY,"q":mood_search_terms(),"image_type":"photo",
                  "orientation":"vertical","safesearch":"true","per_page":20,
                  "order":"popular"},timeout=30)
        r.raise_for_status()
        hits=r.json().get("hits",[])
        random.shuffle(hits)
        hits.sort(key=lambda hit:int(hit.get("imageWidth",0))*int(hit.get("imageHeight",0)),reverse=True)
        for hit in hits:
            url=hit.get("largeImageURL") or hit.get("webformatURL")
            if not url: continue
            try:
                path=WORK/"online_background.jpg"
                with requests.get(url,stream=True,timeout=60) as response:
                    response.raise_for_status()
                    if "image" not in response.headers.get("Content-Type","").lower():
                        continue
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size<20000:
                    path.unlink(missing_ok=True)
                    continue
                try:
                    with Image.open(path) as check: check.verify()
                except Exception:
                    path.unlink(missing_ok=True)
                    continue
                creator=hit.get("user","Pixabay contributor")
                page=hit.get("pageURL","https://pixabay.com/")
                BACKGROUND_CREDIT=f"Pixabay photo by {creator} | {page}"
                print(f"Using real mood-matched Pixabay photo by {creator}.")
                return path
            except (requests.RequestException,OSError) as exc:
                print(f"Pixabay photo candidate failed; trying another: {exc}")
                path.unlink(missing_ok=True)
                continue
    except (requests.RequestException,ValueError,KeyError) as exc:
        print(f"Pixabay photo search failed; trying other sources: {exc}")
    return None

def get_online_image():
    """Fetch a mood-matched reusable image from Pexels or Wikimedia Commons."""
    global BACKGROUND_CREDIT
    terms=mood_search_terms()
    if PEXELS:
        try:
            r=requests.get("https://api.pexels.com/v1/search",
              headers={"Authorization":PEXELS},
              params={"query":terms,"orientation":"portrait","per_page":15},timeout=30)
            r.raise_for_status()
            photos=sorted(r.json().get("photos",[]),
              key=lambda p:p.get("width",0)*p.get("height",0),reverse=True)
            for photo in photos:
                srcs=photo.get("src") or {}
                url=srcs.get("portrait") or srcs.get("large2x") or srcs.get("large")
                if not url: continue
                path=WORK/"online_background.jpg"
                with requests.get(url,stream=True,timeout=60) as response:
                    response.raise_for_status()
                    with path.open("wb") as out:
                        for chunk in response.iter_content(1024*1024):
                            if chunk: out.write(chunk)
                if path.stat().st_size>20000:
                    BACKGROUND_CREDIT=f"Pexels photo by {photo.get('photographer','Pexels contributor')} "
                    print("Using a mood-matched Pexels photo.")
                    return path
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            print(f"Pexels photo search failed; trying Wikimedia Commons: {exc}")

    try:
        params={"action":"query","format":"json","generator":"search",
          "gsrsearch":terms+" filetype:bitmap","gsrnamespace":6,"gsrlimit":15,
          "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1600}
        r=requests.get("https://commons.wikimedia.org/w/api.php",params=params,
          headers={"User-Agent":"PulsenamaPoetryVideo/1.0 (attribution recorded)"},timeout=30)
        r.raise_for_status()
        pages=(r.json().get("query") or {}).get("pages") or {}
        candidates=[]
        for page in pages.values():
            info=(page.get("imageinfo") or [{}])[0]
            meta=info.get("extmetadata") or {}
            url=info.get("thumburl") or info.get("url")
            if url: candidates.append((page,info,url))
        for page,info,url in candidates:
            meta=info.get("extmetadata",{})
            artist=(meta.get("Artist") or {}).get("value","Unknown")
            filename=page.get("title","").replace("File:","",1)
            # Commons thumbnail URLs can occasionally return 403. Try the original
            # URL and Commons' own FilePath redirect independently, then continue
            # to the next candidate instead of aborting the entire search.
            urls=[url]
            if info.get("url") and info.get("url") not in urls:
                urls.append(info["url"])
            if filename:
                from urllib.parse import quote
                redirect="https://commons.wikimedia.org/wiki/Special:FilePath/"+quote(filename)
                if redirect not in urls: urls.append(redirect)
            for candidate_url in urls:
                try:
                    path=WORK/"online_background.jpg"
                    with requests.get(candidate_url,stream=True,timeout=60,
                      headers={"User-Agent":"PulsenamaPoetryVideo/1.0 (image download; contact: project owner)",
                               "Referer":"https://commons.wikimedia.org/"}) as response:
                        response.raise_for_status()
                        content_type=response.headers.get("Content-Type","").lower()
                        if "image" not in content_type:
                            continue
                        with path.open("wb") as out:
                            for chunk in response.iter_content(1024*1024):
                                if chunk: out.write(chunk)
                    if path.stat().st_size>20000:
                        try:
                            with Image.open(path) as check: check.verify()
                        except Exception:
                            path.unlink(missing_ok=True)
                            continue
                        page_url="https://commons.wikimedia.org/wiki/"+page.get("title","").replace(" ","_")
                        BACKGROUND_CREDIT=f"Wikimedia Commons: {page.get('title','image')} | Creator: {artist} | {page_url}"
                        print("Using a reusable Wikimedia Commons image; attribution recorded.")
                        return path
                except (requests.RequestException, OSError) as exc:
                    print(f"Commons candidate download failed; trying another URL/image: {exc}")
                    continue
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Wikimedia Commons image search failed: {exc}")
    return None


def get_unsplash_image():
    """Fetch a real photograph from Unsplash's public search endpoint; never generate art."""
    global BACKGROUND_CREDIT
    # Short search phrases work better than long keyword strings on photo libraries.
    terms = {
      "sad": ["rainy street night", "misty forest", "rain window city lights"],
      "romantic": ["sunset ocean", "wildflowers golden hour", "mountain lake sunset"],
      "motivational": ["mountain sunrise", "ocean cliffs sunrise", "mountain road dawn"],
      "deep": ["starry mountains", "dramatic cloudy mountains", "moonlit ocean"],
      "peaceful": ["misty lake forest", "calm turquoise ocean", "sunlight green forest"],
      "rain": ["rainy city reflections", "misty mountains rain", "raindrops window city"],
      "memories": ["old street golden hour", "countryside road sunset", "seaside town film"],
    }.get(MOOD, ["cinematic nature landscape"])
    headers = {
      "User-Agent": "Mozilla/5.0 (compatible; PulsenamaPoetryVideo/1.0)",
      "Accept": "application/json",
      "Referer": "https://unsplash.com/",
    }
    for query in terms:
        try:
            response = requests.get(
              "https://unsplash.com/napi/search/photos",
              params={"query": query, "per_page": 20, "orientation": "portrait"},
              headers=headers, timeout=30)
            response.raise_for_status()
            photos = response.json().get("results", [])
            random.shuffle(photos)
            for photo in photos:
                urls = photo.get("urls") or {}
                image_url = urls.get("regular") or urls.get("full") or urls.get("raw")
                if not image_url:
                    continue
                path = WORK / "online_background.jpg"
                try:
                    with requests.get(image_url, stream=True, timeout=60, headers=headers) as image_response:
                        image_response.raise_for_status()
                        if "image" not in image_response.headers.get("Content-Type", "").lower():
                            continue
                        with path.open("wb") as out:
                            for chunk in image_response.iter_content(1024 * 1024):
                                if chunk:
                                    out.write(chunk)
                    if path.stat().st_size < 20000:
                        path.unlink(missing_ok=True)
                        continue
                    try:
                        with Image.open(path) as check:
                            check.verify()
                    except Exception:
                        path.unlink(missing_ok=True)
                        continue
                    user = photo.get("user") or {}
                    creator = user.get("name", "Unsplash contributor")
                    profile = user.get("links", {}).get("html", "https://unsplash.com/")
                    page_url = photo.get("links", {}).get("html", "https://unsplash.com/")
                    BACKGROUND_CREDIT = (
                      f"Unsplash photo by {creator} | "
                      f"Photo: {page_url} | Creator: {profile}"
                    )
                    print(f"Using a real mood-matched Unsplash photograph: {creator}.")
                    return path
                except (requests.RequestException, OSError) as exc:
                    print(f"Unsplash photo candidate failed; trying another: {exc}")
                    path.unlink(missing_ok=True)
                    continue
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Unsplash search unavailable for '{query}': {exc}")
            continue
    return None


def generated_background():
    """Create a fresh, original cinematic nature illustration for every run (no stock footage)."""
    rng = random.Random()
    rng_sun_x = rng.uniform(0.35, 0.68)
    img = Image.new("RGB", (W, H))
    px = img.load()
    palettes = {
        "sad": ((10, 19, 34), (80, 91, 112), (205, 142, 105)),
        "rain": ((12, 25, 39), (66, 91, 111), (160, 183, 194)),
        "romantic": ((48, 31, 55), (190, 105, 92), (255, 197, 132)),
        "peaceful": ((12, 42, 54), (74, 139, 135), (235, 207, 151)),
        "deep": ((5, 11, 29), (43, 57, 88), (194, 176, 151)),
        "motivational": ((20, 42, 65), (111, 132, 126), (255, 202, 120)),
        "memories": ((27, 25, 42), (119, 88, 93), (226, 173, 135)),
    }
    top, horizon, light = palettes.get(MOOD, palettes["peaceful"])
    horizon_y = int(H * rng.uniform(0.43, 0.53))
    for y in range(H):
        t = y / max(1, horizon_y)
        if y <= horizon_y:
            q = min(1.0, t)
            col = tuple(int(top[k] * (1-q) + horizon[k] * q) for k in range(3))
        else:
            q = (y-horizon_y) / (H-horizon_y)
            col = tuple(int(horizon[k] * (1-q) + max(0, horizon[k]*0.35) * q) for k in range(3))
        for x in range(W):
            glow = max(0.0, 1.0 - (((x-W*rng_sun_x)/W)**2 + ((y-horizon_y*0.72)/(H*0.42))**2))
            px[x,y] = tuple(min(255, int(col[k] + light[k]*0.18*glow)) for k in range(3))
    d = ImageDraw.Draw(img, "RGBA")
    sun_x = int(W*rng_sun_x); sun_y = int(horizon_y*rng.uniform(0.58,0.82))
    radius = rng.randint(48,82)
    for rr, alpha in ((radius+34,12),(radius+18,20),(radius,210)):
        d.ellipse((sun_x-rr,sun_y-rr,sun_x+rr,sun_y+rr),fill=(*light,alpha))
    # Layered mountain silhouettes with varied original contours.
    for layer, base_y in enumerate((horizon_y+45,horizon_y+115,horizon_y+205)):
        pts=[(0,H)]
        x=0
        while x<=W:
            peak_x=x+rng.randint(35,115)
            peak_y=base_y-rng.randint(80,250)//(layer+1)
            pts.extend([(x,base_y),(min(W,peak_x),max(horizon_y-40,peak_y))])
            x=peak_x
        pts.extend([(W,H)])
        shade=(17+layer*10,28+layer*12,43+layer*13,235-layer*22)
        d.polygon(pts,fill=shade)
    # Lake/river with a broken reflection under the light.
    water_top=horizon_y+210
    d.rectangle((0,water_top,W,H),fill=(12,27,39,95))
    for i in range(95):
        yy=rng.randint(water_top,H-8)
        half=rng.randint(5,100)
        xx=sun_x+rng.randint(-half*2,half*2)
        d.line((xx-half,yy,xx+half,yy),fill=(*light,rng.randint(12,55)),width=rng.randint(1,4))
    # Dark pine silhouettes frame the scene without covering the text area.
    for side in (0,1):
        for i in range(13):
            x=rng.randint(0,150) if side==0 else rng.randint(W-150,W)
            y=rng.randint(horizon_y+80,H-40)
            height=rng.randint(90,260)
            d.rectangle((x-3,y-height//5,x+3,y),fill=(5,13,19,190))
            for k in range(4):
                yy=y-height+k*height//5
                width=(k+1)*rng.randint(12,22)
                d.polygon([(x,yy-height//4),(x-width,yy+height//8),(x+width,yy+height//8)],fill=(5,20,25,190))
    # Soft atmospheric haze and cinematic vignette.
    haze=Image.new("RGBA",(W,H),(0,0,0,0))
    hd=ImageDraw.Draw(haze)
    hd.ellipse((W*0.12,horizon_y-100,W*0.9,horizon_y+350),fill=(*light,24))
    img=Image.alpha_composite(img.convert("RGBA"),haze.filter(ImageFilter.GaussianBlur(75)))
    vignette=Image.new("L",(W,H),0); vd=ImageDraw.Draw(vignette)
    vd.ellipse((-W*0.22,-H*0.12,W*1.22,H*1.12),fill=210)
    vignette=vignette.filter(ImageFilter.GaussianBlur(95))
    dark=Image.new("RGBA",(W,H),(0,0,0,105))
    dark.putalpha(Image.eval(vignette,lambda v: 105-int(v*0.35)))
    img=Image.alpha_composite(img,dark)
    path=WORK/"original_nature_art.jpg"
    img.convert("RGB").save(path,quality=94)
    print("Created a unique original cinematic nature image; no stock image used.")
    return path

def get_font(size):
    # Use a real Latin font for English and an Arabic-script font for Urdu.
    # Pillow's tiny bitmap default font does not contain these glyphs and shows boxes.
    if LANG.lower() in ("urdu", "punjabi"):
        candidates = [
          "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
          "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates = [
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
          "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
          "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    raise RuntimeError("Required text font is missing; install DejaVu Sans and Noto Arabic fonts.")

def poetry_text_color(bg):
    """Choose a mood-led text color, adjusted for contrast against the existing background."""
    palettes = {
        "sad": ((225, 240, 255, 255), (28, 55, 92, 255)),
        "rain": ((225, 245, 255, 255), (25, 58, 78, 255)),
        "romantic": ((255, 215, 232, 255), (105, 35, 70, 255)),
        "motivational": ((255, 235, 160, 255), (105, 65, 12, 255)),
        "deep": ((240, 225, 255, 255), (62, 38, 92, 255)),
        "peaceful": ((225, 255, 230, 255), (30, 78, 60, 255)),
        "memories": ((255, 232, 205, 255), (105, 62, 35, 255)),
    }
    light, dark = palettes.get(MOOD, palettes["peaceful"])
    sample = WORK / "poetry_color_sample.jpg"
    try:
        if Path(bg).suffix.lower() == ".mp4":
            subprocess.run(["ffmpeg", "-y", "-ss", "2", "-i", str(bg),
                            "-frames:v", "1", "-vf", "scale=360:640", str(sample)],
                           check=True, capture_output=True)
            image = Image.open(sample).convert("RGB")
        else:
            image = Image.open(bg).convert("RGB").resize((360, 640))
        crop = image.crop((30, 105, 330, 225)).resize((1, 1))
        red, green, blue = crop.getpixel((0, 0))
        brightness = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        # Bright mood-matched text is paired with a dark outline and shadow.
        print(f"Bright {MOOD} poetry color selected; dark outline adds contrast.")
        return light
    except Exception as exc:
        print(f"Could not sample background for text contrast ({exc}); using mood color.")
        return light


def text_page_png(title, lines, bg):
    """Render one of two reference-style text layouts; do not alter the background."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rtl = LANG.lower() in ("urdu", "punjabi")
    text_color = poetry_text_color(bg)
    visible = [str(line).strip() for line in lines[:3] if str(line).strip()]

    # Alternate the two requested typography-only layouts on each generated video.
    layout = random.choice(("center", "red_rule"))
    print(f"Poetry typography layout: {layout} (background and video effects unchanged).")

    def measure(text, font):
        try:
            return d.textbbox((0, 0), text, font=font,
                              direction="rtl" if rtl else None)
        except Exception:
            return d.textbbox((0, 0), text, font=font)

    def wrap_lines(max_width, base_size):
        wrapped = []
        for raw in visible:
            current = ""
            for word in raw.split():
                candidate = (current + " " + word).strip()
                test_font = get_font(base_size)
                box = measure(candidate, test_font)
                if current and box[2] - box[0] > max_width:
                    wrapped.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                wrapped.append(current)
        return wrapped[:4] or [""]

    # Screenshot-like compact typography: modest size, no panel, no decorative effects.
    max_width = int(W * (0.72 if layout == "red_rule" else 0.82))
    base_size = 50 if rtl else 47
    visible = wrap_lines(max_width, base_size)
    chosen = None
    for size in range(base_size, 27, -2):
        font = get_font(size)
        boxes = [measure(line, font) for line in visible]
        heights = [max(1, b[3] - b[1]) for b in boxes]
        gap = max(13, int(size * 0.28))
        total_h = sum(heights) + gap * max(0, len(heights) - 1)
        if max((b[2] - b[0] for b in boxes), default=0) <= max_width and total_h <= int(H * 0.19):
            chosen = (font, boxes, heights, gap, total_h)
            break
    if chosen is None:
        font = get_font(28)
        boxes = [measure(line, font) for line in visible]
        heights = [max(1, b[3] - b[1]) for b in boxes]
        gap, total_h = 10, sum(heights) + 10 * max(0, len(heights) - 1)
    else:
        font, boxes, heights, gap, total_h = chosen

    def draw_bright_line(x, y, line):
        kwargs = {"direction": "rtl"} if rtl else {}
        # Soft dark shadow plus a strong outline keeps every Urdu/English line crisp.
        d.text((x + 2, y + 4), line, font=font, fill=(0, 0, 0, 220),
               stroke_width=7, stroke_fill=(0, 0, 0, 220), **kwargs)
        d.text((x, y), line, font=font, fill=text_color,
               stroke_width=3, stroke_fill=(16, 19, 34, 255), **kwargs)

    if layout == "center":
        # First reference: centered block, positioned in the upper-middle area.
        y = int(H * 0.30 - total_h / 2)
        for line, box, height in zip(visible, boxes, heights):
            text_w = box[2] - box[0]
            x = (W - text_w) // 2
            draw_bright_line(x, y, line)
            y += height + gap
    else:
        # Second reference: text block beside a slim red vertical rule on the right.
        rule_x = int(W * 0.88)
        rule_top = int(H * 0.23)
        rule_bottom = min(int(H * 0.43), rule_top + total_h + 26)
        d.rounded_rectangle((rule_x, rule_top, rule_x + 5, rule_bottom),
                            radius=2, fill=(220, 45, 55, 255))
        y = rule_top + 5
        for line, box, height in zip(visible, boxes, heights):
            text_w = box[2] - box[0]
            x = max(55, rule_x - 24 - text_w)
            draw_bright_line(x, y, line)
            y += height + gap

    path = WORK / "poetry_overlay.png"
    layer.save(path)
    return path


def get_google_drive_music():
    """Reserved hook for the Google Drive song library; integration will be completed later."""
    # Keep this function in the music pipeline so a Drive folder can be connected
    # without changing the video-generation flow. No Drive URL or credentials
    # are currently configured in this repository.
    print("Google Drive song library is not connected yet; continuing to the existing song source.")
    return None


def get_online_poetry_voice(title, lines):
    """Find a licensed human recording of this exact poem; never use unrelated recitation or synthesize speech."""
    global BACKGROUND_CREDIT
    import html
    import re
    from urllib.parse import urlparse

    def normalize(value):
        value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).lower()
        return " ".join(re.findall(r"[\w]+", value, flags=re.UNICODE))

    # Search using the actual displayed poem, not generic 'poetry' keywords.
    phrases = [normalize(line) for line in lines if len(normalize(line)) >= 12]
    if not phrases:
        print("Poem text is too short to verify against a human recording.")
        return None

    searches = [f'"{title}" "{lines[0]}"', f'"{lines[0]}"', f'"{title}"']
    candidates = {}
    headers = {"User-Agent": "PulsenamaPoetryVideo/1.0 (audio search)"}
    for query in searches:
        try:
            response = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "format": "json", "generator": "search",
                    "gsrsearch": query + " filetype:audio", "gsrnamespace": 6,
                    "gsrlimit": 30, "prop": "imageinfo",
                    "iiprop": "url|mime|extmetadata",
                },
                headers=headers, timeout=30,
            )
            response.raise_for_status()
            pages = (response.json().get("query") or {}).get("pages") or {}
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                mime = str(info.get("mime") or "").lower()
                url = info.get("url")
                if not url or not mime.startswith("audio/"):
                    continue
                meta = info.get("extmetadata") or {}
                title_text = page.get("title") or ""
                description = (meta.get("ImageDescription") or {}).get("value") or ""
                searchable = normalize(title_text + " " + description)
                # Require the recording metadata/transcript to contain at least one
                # complete displayed poem line. Generic poetry audio is not enough.
                matched = [phrase for phrase in phrases if phrase in searchable]
                if not matched:
                    continue

                license_name = (meta.get("LicenseShortName") or {}).get("value", "")
                license_text = normalize(license_name)
                usage = normalize((meta.get("UsageTerms") or {}).get("value", ""))
                restricted_terms = ("nc" in license_text.split() or "nd" in license_text.split()
                                    or "noncommercial" in usage or "non commercial" in usage
                                    or "no derivatives" in usage)
                cc_by_allowed = (
                    license_text.startswith("cc by ")
                    and not restricted_terms
                )
                permitted = (
                    "cc0" in license_text or "public domain" in license_text
                    or cc_by_allowed
                    or ("creative commons attribution" in usage and not restricted_terms)
                    or "public domain" in usage
                )
                if not permitted:
                    print(f"Skipping exact-text audio with unclear/restricted reuse terms: {title_text}")
                    continue
                candidates[title_text] = (page, info, matched[0])
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Wikimedia exact-poem audio search failed for '{query}': {exc}")

    for title_text, (page, info, matched_phrase) in candidates.items():
        url = info.get("url")
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix not in (".mp3", ".ogg", ".oga", ".opus", ".wav", ".flac", ".m4a"):
            suffix = ".audio"
        path = WORK / ("poetry_voice" + suffix)
        try:
            with requests.get(url, stream=True, timeout=90, headers=headers) as download:
                download.raise_for_status()
                if "audio" not in download.headers.get("Content-Type", "").lower():
                    continue
                with path.open("wb") as out:
                    for chunk in download.iter_content(256 * 1024):
                        if chunk:
                            out.write(chunk)
            if path.stat().st_size < 12000:
                path.unlink(missing_ok=True)
                continue
            probe = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(path), "-t", "2", "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            if probe.returncode != 0:
                path.unlink(missing_ok=True)
                continue

            meta = info.get("extmetadata") or {}
            artist = (meta.get("Artist") or {}).get("value", "Unknown contributor")
            license_name = (meta.get("LicenseShortName") or {}).get("value", "Unknown")
            page_url = "https://commons.wikimedia.org/wiki/" + title_text.replace(" ", "_")
            BACKGROUND_CREDIT += (
                f"\nPoetry voice: {title_text} | Voice credit: {artist} | "
                f"License: {license_name} | {page_url}"
            )
            print(f"Using licensed human recording verified against the displayed poem: {title_text}.")
            return path
        except (requests.RequestException, OSError, subprocess.SubprocessError) as exc:
            print(f"Exact-poem recording download failed; trying another: {exc}")
            path.unlink(missing_ok=True)

    print("No licensed human recording matching the displayed poem was found; refusing to create/publish an instrumental-only video.")
    return None

def get_online_music():
    """Choose vocals by poem language: English tracks for English, PAK/IND artists for Urdu."""
    global BACKGROUND_CREDIT
    client_id=os.getenv("JAMENDO_CLIENT_ID","").strip()
    if not client_id:
        print("Missing JAMENDO_CLIENT_ID; add it as a GitHub Actions secret.")
        return None

    try:
        candidates=[]
        if LANG == "English":
            mood_tags={
              "sad":"sad emotional pop",
              "romantic":"romance pop",
              "motivational":"energetic pop rock",
              "deep":"emotional soul pop",
              "peaceful":"chillout acoustic pop",
              "rain":"sad chillout pop",
              "memories":"nostalgic emotional pop",
            }.get(MOOD,"pop")
            params={
              "client_id":client_id,"format":"json","limit":100,
              "type":"single albumtrack","vocalinstrumental":"vocal",
              "lang":"en","fuzzytags":mood_tags.replace(" ","+"),
              "audioformat":"mp32","audiodlformat":"mp32",
              "boost":"popularity_week","include":"musicinfo",
            }
            response=requests.get("https://api.jamendo.com/v3.0/tracks/",params=params,timeout=40)
            response.raise_for_status()
            payload=response.json()
            headers=payload.get("headers") or {}
            if headers.get("status")!="success":
                raise RuntimeError(headers.get("error_message") or "Jamendo English-track search failed")
            candidates=payload.get("results") or []
            print(f"Jamendo returned {len(candidates)} popular English vocal tracks.")
        else:
            # Jamendo's trending chart can be restricted to the artist's country.
            # PAK and IND keep Urdu videos within Pakistani/Indian music creators.
            chart_ids=[]
            for country in ("PAK","IND"):
                params={"client_id":client_id,"format":"json","limit":100,
                        "order":"trending","country":country}
                response=requests.get("https://api.jamendo.com/v3.0/charts/track/",params=params,timeout=40)
                response.raise_for_status()
                payload=response.json()
                headers=payload.get("headers") or {}
                if headers.get("status")!="success":
                    raise RuntimeError(headers.get("error_message") or f"Jamendo {country} trending chart failed")
                ids=[str(item.get("id")) for item in (payload.get("results") or []) if item.get("id")]
                print(f"Jamendo {country} trending chart: {len(ids)} tracks.")
                chart_ids.extend(ids)
            # Preserve chart order while removing duplicates.
            chart_ids=list(dict.fromkeys(chart_ids))
            if chart_ids:
                params={"client_id":client_id,"format":"json","limit":200,
                        "id":"+".join(chart_ids),"type":"single albumtrack",
                        "vocalinstrumental":"vocal","audioformat":"mp32",
                        "audiodlformat":"mp32","include":"musicinfo"}
                response=requests.get("https://api.jamendo.com/v3.0/tracks/",params=params,timeout=40)
                response.raise_for_status()
                payload=response.json()
                headers=payload.get("headers") or {}
                if headers.get("status")!="success":
                    raise RuntimeError(headers.get("error_message") or "Jamendo regional-track lookup failed")
                by_id={str(track.get("id")):track for track in (payload.get("results") or [])}
                candidates=[by_id[track_id] for track_id in chart_ids if track_id in by_id]
                print(f"Jamendo returned {len(candidates)} Pakistani/Indian trending-chart vocal tracks.")
            else:
                print("No Pakistani or Indian tracks appeared in Jamendo's trending charts.")

        seen=set()
        for track in candidates:
            track_id=str(track.get("id",""))
            if not track_id or track_id in seen:
                continue
            seen.add(track_id)
            musicinfo=track.get("musicinfo") or {}
            vocal=musicinfo.get("vocalinstrumental","vocal")
            if str(vocal).lower()!="vocal":
                continue
            allowed=track.get("audiodownload_allowed")
            if not (allowed is True or str(allowed).lower() in ("1","true")):
                continue
            url=track.get("audiodownload")
            if not url:
                continue
            path=WORK/"jamendo_vocal_song.mp3"
            try:
                with requests.get(url,stream=True,timeout=90) as download:
                    download.raise_for_status()
                    with path.open("wb") as out:
                        for chunk in download.iter_content(256*1024):
                            if chunk:
                                out.write(chunk)
                if path.stat().st_size<50000:
                    path.unlink(missing_ok=True)
                    continue
                probe=subprocess.run(
                  ["ffmpeg","-v","error","-i",str(path),"-t","2","-f","null","-"],
                  stdout=subprocess.DEVNULL,stderr=subprocess.PIPE
                )
                if probe.returncode!=0:
                    path.unlink(missing_ok=True)
                    continue
                title=track.get("name","Jamendo song")
                artist=track.get("artist_name","Jamendo artist")
                page=f"https://www.jamendo.com/track/{track_id}"
                region="English" if LANG=="English" else "Pakistani/Indian"
                BACKGROUND_CREDIT += f"\nSong: {title} — {artist} ({region} vocals) | Jamendo: {page}"
                print(f"Using {region} vocal song: {title} — {artist}.")
                return path
            except (requests.RequestException,OSError,subprocess.SubprocessError) as exc:
                print(f"Song download failed; trying the next matching vocal track: {exc}")
                path.unlink(missing_ok=True)

        if LANG=="English":
            print("Jamendo found no downloadable English vocal song.")
        else:
            print("Jamendo found no downloadable Pakistani/Indian vocal song; no foreign song will be substituted.")
    except (requests.RequestException,ValueError,KeyError,RuntimeError) as exc:
        print(f"Jamendo language-specific song search failed: {exc}")
    return None

def get_audio_duration(path):
    """Read the exact media duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError(f"Could not determine a valid audio duration for {path}.")
    return duration


def get_local_music(target_duration=None):
    """Choose valid music only from music/urdu; match the voice length when supplied."""
    language_folder = "urdu"
    folder = Path("music") / language_folder
    supported = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
    candidates = [p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in supported and p.stat().st_size > 10000] if folder.exists() else []
    valid = []
    for path in candidates:
        try:
            duration = get_audio_duration(path)
            valid.append((path, duration))
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            print(f"Skipping unreadable music file {path}: {exc}")
    if not valid:
        raise RuntimeError(
            f"No usable music file found in {folder}. Upload an MP3 (or WAV/OGG/M4A/FLAC) "
            f"and rerun the workflow."
        )
    if target_duration is None:
        path, duration = random.choice(valid)
    else:
        path, duration = min(valid, key=lambda item: abs(item[1] - target_duration))
    print(f"Using local {language_folder} music: {path.name} ({duration:.2f}s)")
    if target_duration is not None:
        print(f"Matched music to human voice duration: {target_duration:.2f}s.")
    return path


def make_mood_music(title, lines):
    """Compose a fresh, gentle piano-and-strings instrumental using a SoundFont."""
    try:
        import pretty_midi
    except ImportError as exc:
        raise RuntimeError("pretty_midi is required for the piano-and-strings soundtrack.") from exc

    profiles = {
      "sad":          {"bpm":66,"root":57,"chords":[[0,3,7],[8,0,3],[5,8,0],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "romantic":     {"bpm":76,"root":57,"chords":[[0,4,7],[9,0,4],[5,9,0],[7,11,2]],"lead":[0,2,4,5,7,9,11]},
      "peaceful":     {"bpm":70,"root":55,"chords":[[0,4,7],[5,9,0],[2,5,9],[7,11,2]],"lead":[0,2,4,5,7,9,11]},
      "deep":         {"bpm":62,"root":55,"chords":[[0,3,7],[6,10,1],[8,0,3],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "motivational": {"bpm":88,"root":55,"chords":[[0,4,7],[7,11,2],[9,0,4],[5,9,0]],"lead":[0,2,4,5,7,9,11]},
      "rain":         {"bpm":66,"root":55,"chords":[[0,3,7],[8,0,3],[5,8,0],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
      "memories":     {"bpm":68,"root":57,"chords":[[0,3,7],[5,8,0],[8,0,3],[3,7,10]],"lead":[0,2,3,5,7,8,10]},
    }
    mood=MOOD if MOOD in profiles else "peaceful"
    p=profiles[mood]
    rng=random.Random()
    bpm=p["bpm"]+rng.randint(-3,3)
    beat=60.0/bpm
    bar=beat*4
    midi=pretty_midi.PrettyMIDI(initial_tempo=bpm)
    piano=pretty_midi.Instrument(program=0,name="Soft Grand Piano")
    strings=pretty_midi.Instrument(program=48,name="Warm Strings")
    pad=pretty_midi.Instrument(program=89,name="Warm Atmosphere")
    bell=pretty_midi.Instrument(program=10,name="Soft Music Box")
    progression=list(p["chords"])
    shift=rng.randrange(len(progression))
    progression=progression[shift:]+progression[:shift]
    if rng.random()<0.35: progression=list(reversed(progression))
    bars=int(math.ceil(DURATION/bar))+1
    for bi in range(bars):
        start=bi*bar
        if start>=DURATION:
            continue
        chord=progression[bi%len(progression)]
        # Long, quiet string harmony underneath the piano.
        for j,interval in enumerate(chord):
            note=p["root"]+interval
            strings.notes.append(pretty_midi.Note(
              velocity=42 if j==0 else 34,pitch=note+12,
              start=start,end=min(DURATION,start+bar*1.08)))
            pad.notes.append(pretty_midi.Note(
              velocity=22,pitch=note+24,
              start=start,end=min(DURATION,start+bar*1.2)))
        # Broken-chord piano notes with natural pauses, rather than repetitive beeps.
        arp=[p["root"]+chord[0]+12,p["root"]+chord[1]+12,
             p["root"]+chord[2]+12,p["root"]+chord[1]+24]
        order=[0,1,2,3] if mood in ("motivational","romantic") else [0,2,1,3]
        for k,idx in enumerate(order):
            onset=start+k*beat*0.82+rng.uniform(0,0.035)
            if onset>=DURATION: continue
            pitch=arp[idx]+rng.choice([0,0,0,12])
            dur=beat*rng.uniform(0.55,0.82)
            piano.notes.append(pretty_midi.Note(
              velocity=rng.randint(45,61),pitch=pitch,
              start=onset,end=min(DURATION,onset+dur)))
        # Sparse, lyrical top melody; keep plenty of breathing room.
        if bi%2==0 or mood=="motivational":
            scale=p["lead"]
            degree=rng.choice(scale)
            pitch=p["root"]+24+degree
            onset=start+beat*rng.choice([0.0,1.0,2.0])
            dur=beat*rng.uniform(1.0,1.8)
            if onset<DURATION:
                piano.notes.append(pretty_midi.Note(
                  velocity=rng.randint(34,49),pitch=pitch,
                  start=onset,end=min(DURATION,onset+dur)))
            if mood in ("romantic","peaceful","memories") and rng.random()<0.45 and onset+beat<DURATION:
                bell.notes.append(pretty_midi.Note(
                  velocity=27,pitch=pitch+12,start=onset+beat,
                  end=min(DURATION,onset+beat+beat*0.7)))
    midi.instruments.extend([strings,pad,piano,bell])
    midi_path=WORK/"cinematic_original.mid"
    wav_path=WORK/"cinematic_original.wav"
    midi.write(str(midi_path))
    soundfont="/usr/share/sounds/sf2/TimGM6mb.sf2"
    if not Path(soundfont).exists():
        raise RuntimeError("The General MIDI SoundFont was not installed by the workflow.")
    run(["fluidsynth","-ni",soundfont,str(midi_path),"-F",str(wav_path),"-r","22050"])
    print(f"Composed a fresh {mood} piano-and-strings soundtrack at {bpm} BPM.")
    return wav_path


def render_video(title,lines,bg,music,voice=None):
    # If no matching human recitation exists, keep the earlier text-poetry + music format.
    page=text_page_png(title,lines,bg)
    if bg.suffix.lower()==".mp4":
        inputs=["-stream_loop","-1","-i",str(bg),"-loop","1","-i",str(page)]
    else:
        inputs=["-loop","1","-i",str(bg),"-loop","1","-i",str(page)]
    # Music is an original instrumental bed. A real recitation, when found, stays in front.
    inputs += ["-i",str(music)]
    if voice is not None:
        inputs += ["-i",str(voice)]

    base="[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.00012,1.06)':d=1:s=1080x1920:fps=24,setsar=1,trim=duration="+str(DURATION)+",setpts=PTS-STARTPTS,fade=t=in:st=0.75:d=1.15[bg]"
    filters=[base,
      "[1:v]format=rgba,fade=t=in:st=1.35:d=0.65:alpha=1[poem]",
      "[bg][poem]overlay=(W-w)/2:(H-h)/2:enable='between(t,1.30,"+str(DURATION)+")'[vout]"]
    if voice is not None:
        filters += [
          "[2:a]volume=0.13,atrim=duration="+str(DURATION)+",asetpts=PTS-STARTPTS[bed]",
          "[3:a]atrim=duration="+str(DURATION)+",asetpts=PTS-STARTPTS,apad=pad_dur="+str(DURATION)+",loudnorm=I=-16:TP=-1.5:LRA=7[voice]",
          "[voice][bed]amix=inputs=2:duration=longest:dropout_transition=1:normalize=0,alimiter=limit=0.98,afade=t=in:st=0:d=0.5,afade=t=out:st="+str(max(0,DURATION-2))+":d=2[aout]"
        ]
    else:
        filters += [
          "[2:a]volume=0.9,loudnorm=I=-18:TP=-1.5:LRA=8,alimiter=limit=0.98,afade=t=in:st=0:d=1.0,afade=t=out:st="+str(max(0,DURATION-3))+":d=3[aout]"
        ]
    cmd=["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),
      "-map","[vout]","-map","[aout]","-t",str(DURATION),"-r",str(FPS),
      "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-s","1080x1920",
      "-c:a","aac","-b:a","160k","-movflags","+faststart",str(OUT)]
    run(cmd)
    audio_note = "Human poetry recitation + quiet local background music." if voice is not None else "No matching human recitation found; text poetry + music selected only from music/urdu (no AI voice)."
    Path("poetry_demo.txt").write_text(f"Title: {title}\nMood: {MOOD}\nLanguage: {LANG}\nDuration: {DURATION}s\n\n"+
      "\n".join(lines)+"\n\nBackground: "+BACKGROUND_CREDIT+"\nShort 2–3 line poetry displayed directly on background; no text box or watermark.\nAudio: "+audio_note+"\n",encoding="utf-8")




def main():
    global DURATION
    # Always generate poetry. Qawwali mode is intentionally disabled.
    print(f"Auto-selected: {MOOD} mood / {LANG} / {DURATION}s.")
    title,lines=make_poem()
    lines=lines[:3]
    # Prefer real portrait video backgrounds, then fall back to real photographs.
    bg=get_pexels_video()
    if bg is None:
        bg=get_pixabay_video()
    if bg is None:
        print("No suitable stock video found; trying online photos.")
        bg=get_online_image()
    if bg is None:
        bg=get_pixabay_image()
    if bg is None:
        print("Pixabay/Pexels/Wikimedia did not return a usable photo; trying Unsplash.")
        bg=get_unsplash_image()
    if bg is None:
        raise RuntimeError("No usable internet photo/video could be downloaded; no AI image will be generated.")

    # Prefer a real human recitation. If none matches this generated poem,
    # fall back to the original text-on-screen poetry video with local background music.
    voice=get_online_poetry_voice(title,lines)
    if voice is None:
        print("No matching human recitation found; using text poetry + local background music fallback.")
    if voice is not None:
        voice_duration = get_audio_duration(voice)
        music = get_local_music(voice_duration)
        DURATION = voice_duration
        print(f"Video duration follows original poetry voice: {DURATION:.2f}s.")
    else:
        music = get_local_music()
        DURATION = get_audio_duration(music)
        print(f"Text-poetry video duration follows selected music: {DURATION:.2f}s.")
    render_video(title,lines,bg,music,voice)
    print(f"SUCCESS: {OUT} ({OUT.stat().st_size} bytes). Video generation completed.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise