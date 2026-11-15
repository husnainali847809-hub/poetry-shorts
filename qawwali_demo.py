#!/usr/bin/env python3
"""Create a short vertical Qawwali performance video from reusable Wikimedia Commons footage."""
import html
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
DURATION = 30
OUT = Path("poetry_demo.mp4")
WORK = Path("qawwali_work")
WORK.mkdir(exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "PulsenamaQawwaliShorts/1.0 (automated video creator)"}


def run(cmd):
    subprocess.run(cmd, check=True)


def find_qawwali_video():
    """Find a Qawwali performance whose Commons metadata permits reuse."""
    queries = ['Qawwali filetype:video', '"Qawwali performance" filetype:video',
               'Qawwali singer concert filetype:video']
    candidates = {}
    for query in queries:
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 50,
            "prop": "imageinfo", "iiprop": "url|mime|extmetadata|size",
        }
        response = requests.get(API, params=params, headers=HEADERS, timeout=40)
        response.raise_for_status()
        pages = (response.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            mime = str(info.get("mime") or "").lower()
            url = info.get("url")
            if not url or not mime.startswith("video/"):
                continue
            meta = info.get("extmetadata") or {}
            license_name = html.unescape((meta.get("LicenseShortName") or {}).get("value", ""))
            license_lower = license_name.lower()
            usage = html.unescape((meta.get("UsageTerms") or {}).get("value", "")).lower()
            # Permit public-domain, CC0, and attribution licenses that allow reuse.
            allowed = ("public domain" in license_lower or "cc0" in license_lower
                       or license_lower.startswith("cc by ")
                       or "creative commons attribution" in usage)
            if not allowed or "noncommercial" in usage or "no derivatives" in usage:
                continue
            title = page.get("title", "")
            searchable = (title + " " + html.unescape((meta.get("ImageDescription") or {}).get("value", ""))).lower()
            if "qawwali" not in searchable and "qawwali" not in query.lower():
                continue
            candidates[title] = (page, info, meta, license_name)
    if not candidates:
        raise RuntimeError("No reusable Qawwali performance video was found on Wikimedia Commons. No video was published.")
    return random.choice(list(candidates.values()))


def download_video(info):
    url = info["url"]
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in (".mp4", ".webm", ".ogv", ".mkv", ".mov"):
        ext = ".video"
    path = WORK / ("qawwali_source" + ext)
    with requests.get(url, stream=True, timeout=120, headers=HEADERS) as response:
        response.raise_for_status()
        with path.open("wb") as out:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    out.write(chunk)
    if path.stat().st_size < 100_000:
        raise RuntimeError("Downloaded Qawwali video is unexpectedly small.")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                           capture_output=True, text=True)
    if probe.returncode or not probe.stdout.strip():
        raise RuntimeError("Downloaded Qawwali file is not a readable video.")
    return path, float(probe.stdout.strip())


def make_overlay():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    ]
    font_path = next((p for p in candidates if Path(p).exists()), None)
    if not font_path:
        raise RuntimeError("Noto Arabic font is missing.")
    font = ImageFont.truetype(font_path, 48)
    phrase = "محفلِ قوالی"
    color = random.choice([(255, 245, 190, 255), (190, 240, 255, 255),
                           (255, 215, 225, 255), (235, 225, 255, 255),
                           (255, 225, 180, 255)])
    box = draw.textbbox((0, 0), phrase, font=font, direction="rtl")
    x = (W - (box[2] - box[0])) // 2
    y = int(H * 0.245)
    draw.text((x + 2, y + 3), phrase, font=font, fill=(0, 0, 0, 180),
              stroke_width=3, stroke_fill=(0, 0, 0, 140), direction="rtl")
    draw.text((x, y), phrase, font=font, fill=color, stroke_width=2,
              stroke_fill=(12, 12, 18, 210), direction="rtl")
    path = WORK / "qawwali_overlay.png"
    layer.save(path)
    return path


def render(source, duration):
    overlay = make_overlay()
    start = random.uniform(0, max(0, duration - DURATION)) if duration > DURATION else 0
    run(["ffmpeg", "-y", "-ss", str(start), "-i", str(source),
         "-loop", "1", "-i", str(overlay), "-t", str(min(DURATION, max(8, duration-start))),
         "-filter_complex",
         "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
         "setsar=1,fps=30,fade=t=in:st=0:d=0.5[bg];"
         "[1:v]format=rgba,fade=t=in:st=0.4:d=0.5:alpha=1[txt];"
         "[bg][txt]overlay=0:0[v]",
         "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=7,afade=t=in:st=0:d=0.5",
         "-shortest", "-movflags", "+faststart", str(OUT)])


def main():
    page, info, meta, license_name = find_qawwali_video()
    source, duration = download_video(info)
    render(source, duration)
    title = page.get("title", "Qawwali performance")
    artist = html.unescape((meta.get("Artist") or {}).get("value", "Unknown contributor"))
    description = html.unescape((meta.get("ImageDescription") or {}).get("value", ""))
    page_url = "https://commons.wikimedia.org/wiki/" + quote(title.replace(" ", "_"))
    Path("poetry_demo.txt").write_text(
        "Title: Qawwali — " + title.replace("File:", "") + "\n"
        "Mood: peaceful\nLanguage: Urdu\nDuration: " + str(DURATION) + "s\n\n"
        "محفلِ قوالی\n\nBackground: Wikimedia Commons Qawwali performance\n"
        + "Artist: " + artist + "\nLicense: " + license_name + "\nSource: " + page_url
        + "\nDescription: " + re.sub(r"\\s+", " ", description)[:1200]
        + "\nAudio: Original audio from the selected performance.\n",
        encoding="utf-8")
    print("SUCCESS: Qawwali performance Short rendered: " + str(OUT))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise
