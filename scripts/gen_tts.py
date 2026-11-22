#!/usr/bin/env python3
"""phrases.json と names.txt から、Google Cloud Text-to-Speech の音声(MP3)を作る。
- audio/{id}.mp3                    … 名前なし版
- audio/names/{slug}/{id}.mp3       … 名前入り版（slug = 名前の各文字のUnicode16進を - でつないだもの）
環境変数: GOOGLE_TTS_API_KEY（必須） / VOICE / RATE / FORCE=1 / DRY=1
すでにあるファイルは作り直さない（料金節約）。FORCE=1 で作り直す。
"""
import base64, json, os, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("GOOGLE_TTS_API_KEY", "")
VOICE = os.environ.get("VOICE", "ja-JP-Chirp3-HD-Aoede")
RATE = float(os.environ.get("RATE", "0.9"))
FORCE = os.environ.get("FORCE") == "1"
DRY = os.environ.get("DRY") == "1"

def slug(name): return "-".join(format(ord(c), "x") for c in name)
def text_for(p, name):
    t = p["ja"]
    if name: return t.replace("{name}", name)
    return t.replace("{name}、", "").replace("、{name}", "").replace("{name}", "")

def synth(text, with_rate=True):
    cfg = {"audioEncoding": "MP3"}
    if with_rate: cfg["speakingRate"] = RATE
    body = json.dumps({"input": {"text": text},
                       "voice": {"languageCode": "ja-JP", "name": VOICE},
                       "audioConfig": cfg}).encode()
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + KEY,
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return base64.b64decode(json.load(r)["audioContent"])
    except urllib.error.HTTPError as e:
        if e.code == 400 and with_rate:   # 話す速さに未対応の声ならスピード指定なしで再試行
            return synth(text, False)
        raise SystemExit("TTS error %s: %s" % (e.code, e.read().decode()[:300]))

def main():
    phrases = json.load(open(os.path.join(ROOT, "phrases.json"), encoding="utf-8"))
    names = []
    p = os.path.join(ROOT, "names.txt")
    if os.path.exists(p):
        names = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]
    jobs = []
    for ph in phrases:
        jobs.append((os.path.join(ROOT, "audio", ph["id"] + ".mp3"), text_for(ph, "")))
        for n in names:
            jobs.append((os.path.join(ROOT, "audio", "names", slug(n), ph["id"] + ".mp3"), text_for(ph, n)))
    todo = [(f, t) for f, t in jobs if FORCE or not os.path.exists(f)]
    chars = sum(len(t) for _, t in todo)
    print("voice=%s names=%d 作る=%d本 文字数=%d" % (VOICE, len(names), len(todo), chars))
    if DRY:
        for f, t in todo: print(" -", os.path.relpath(f, ROOT), "|", t)
        return
    if not KEY:
        print("GOOGLE_TTS_API_KEY が未設定のため、音声は作りません（アプリは端末の声で代用します）。")
        return
    for f, t in todo:
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "wb").write(synth(t))
        print("ok", os.path.relpath(f, ROOT))

if __name__ == "__main__":
    main()
