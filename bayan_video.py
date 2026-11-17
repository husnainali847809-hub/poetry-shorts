#!/usr/bin/env python3
"""Create one daily Urdu Islamic reminder video using only music/bayan audio."""
import json
import random
from pathlib import Path

import poetry_demo as p

def make_bayan_text():
    """Use a small curated set of sourced Quran/Hadith meanings; never invent attribution."""
    sourced_reminders = [
        (
            "اللہ تعالیٰ کا ارشاد ہے",
            [
                "اللہ کسی جان پر اس کی طاقت سے بڑھ کر بوجھ نہیں ڈالتا",
                "یہ آیت ہمیں اللہ کی رحمت اور آسانی یاد دلاتی ہے"
            ]
        ),
        (
            "رسول اللہ ﷺ نے فرمایا",
            [
                "اعمال کا دارومدار نیتوں پر ہے",
                "اور ہر شخص کو وہی ملے گا جس کی اس نے نیت کی"
            ]
        )
    ]
    # These are original reminders, not Quran/Hadith quotations.
    original_reminders = [
        ("اسلامی یاد دہانی: اللہ کی رحمت", [
            "جب دل پریشان ہو تو اپنے رب کو یاد کرو",
            "اللہ کی رحمت سے کبھی مایوس نہ ہونا"
        ]),
        ("اسلامی یاد دہانی: محبتِ رسول ﷺ", [
            "رسول اللہ ﷺ کی سیرت ہمارے لیے بہترین رہنمائی ہے",
            "آپ ﷺ کی تعلیمات پر عمل ہی سچی محبت کا راستہ ہے"
        ]),
        ("اسلامی یاد دہانی: شکر", [
            "ہر حال میں اللہ کا شکر ادا کرنا سیکھو",
            "شکر گزار دل چھوٹی نعمت میں بھی خوشی پا لیتا ہے"
        ]),
        ("اسلامی یاد دہانی: نماز", [
            "اپنے رب کے سامنے دل کی بات رکھو",
            "نماز کو اپنی زندگی کا سکون بناؤ"
        ]),
        ("اسلامی یاد دہانی: حسنِ اخلاق", [
            "نرمی اور اچھا اخلاق دلوں کو قریب کرتے ہیں",
            "لوگوں کے ساتھ وہی سلوک کرو جو اپنے لیے پسند ہو"
        ])
    ]
    # Prefer a sourced Quran/Hadith reminder; otherwise clearly label original advice.
    return random.choice(sourced_reminders + original_reminders)

def choose_bayan_music():
    folder = Path("music/bayan")
    extensions = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
    files = [f for f in folder.iterdir() if f.is_file()
             and f.suffix.lower() in extensions and f.stat().st_size > 10000]
    valid = []
    for file in files:
        try:
            duration = p.get_audio_duration(file)
            if duration >= 8:
                valid.append((file, duration))
        except Exception as exc:
            print(f"Skipping unreadable bayan audio {file.name}: {exc}")
    if not valid:
        raise RuntimeError("No usable audio found in music/bayan/. Add an MP3/WAV/M4A/OGG/FLAC file.")
    chosen, duration = random.choice(valid)
    print(f"Selected bayan folder audio: {chosen.name} ({duration:.1f}s)")
    return chosen, duration

def main():
    p.LANG = "Urdu"
    p.MOOD = "spiritual"
    p.DURATION = 30
    p.OUT = Path("poetry_demo.mp4")
    p.WORK = Path("poetry_demo_work")
    p.WORK.mkdir(exist_ok=True)
    title, lines = make_bayan_text()
    music, music_duration = choose_bayan_music()
    p.DURATION = min(music_duration, 45)
    bg = p.get_pexels_video()
    if bg is None:
        bg = p.get_pixabay_video()
    if bg is None:
        bg = p.get_online_image()
    if bg is None:
        bg = p.get_pixabay_image()
    if bg is None:
        bg = p.get_unsplash_image()
    if bg is None:
        raise RuntimeError("No suitable background photo/video found for bayan.")
    p.render_video(title, lines, bg, music, voice=None)
    Path("poetry_demo.txt").write_text(
        f"ContentType: Bayan\nTitle: {title}\nMood: spiritual\nLanguage: Urdu\n"
        f"Duration: {p.DURATION:.1f}s\n\n" + "\n".join(lines) +
        f"\n\nBackground: {p.BACKGROUND_CREDIT}\n"
        f"Audio: User-provided music from music/bayan/{music.name}\n",
        encoding="utf-8"
    )
    print(f"SUCCESS: Daily Islamic bayan video created ({p.DURATION:.1f}s).")

if __name__ == "__main__":
    main()
