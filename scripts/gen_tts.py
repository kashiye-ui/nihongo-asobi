#!/usr/bin/env python3
"""phrases.json と names.txt から、Google Cloud Text-to-Speech の音声(MP3)を作る。
- audio/{id}.mp3                    … 名前なし版
- audio/names/{slug}/{id}.mp3       … 名前入り版（slug = 名前の各文字のUnicode16進を - でつないだもの）
環境変数: GOOGLE_TTS_API_KEY（必須） / VOICE / RATE / FORCE=1 / DRY=1
すでにあるファイルは作り直さない（料金節約）。FORCE=1 で作り直す。
"""
import base64, json, os, struct, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("GOOGLE_TTS_API_KEY", "")
VOICE = os.environ.get("VOICE", "ja-JP-Chirp3-HD-Aoede")
RATE = float(os.environ.get("RATE", "0.85"))
FORCE = os.environ.get("FORCE") == "1"
DRY = os.environ.get("DRY") == "1"

# 登場人物ごとの声（speech.json の v）。VOICEMAP='{"t":"ja-JP-Chirp3-HD-Kore"}' で上書き可
VOICES = {"n": "Kore", "p": "Leda", "t": "Gacrux", "f": "Puck", "m": "Sulafat", "dr": "Charon", "c": "Zephyr"}
try: VOICES.update({k: v.split("-")[-1] for k, v in json.loads(os.environ.get("VOICEMAP") or "{}").items()})
except Exception: pass
def vname(v): return "ja-JP-Chirp3-HD-" + VOICES.get(v, VOICES["n"])

def K(v, t):  # index.html の K() と同じ（UTF-16 単位で計算）
    s = v + "|" + t; b = s.encode("utf-16-le"); units = struct.unpack("<%dH" % (len(b) // 2), b)
    M = 0xffffffff; imul = lambda a, c: (a * c) & M
    h1, h2 = 0xdeadbeef, 0x41c6ce57
    for c in units: h1 = imul(h1 ^ c, 2654435761); h2 = imul(h2 ^ c, 1597334677)
    h1 = (imul(h1 ^ (h1 >> 16), 2246822507) ^ imul(h2 ^ (h2 >> 13), 3266489909)) & M
    h2 = (imul(h2 ^ (h2 >> 16), 2246822507) ^ imul(h1 ^ (h1 >> 13), 3266489909)) & M
    return format(4294967296 * (2097151 & h2) + h1, "x").rjust(14, "0")

def strip_name(t): return t.replace("{name}、", "").replace("、{name}", "").replace("{name}", "")

def slug(name): return "-".join(format(ord(c), "x") for c in name)
def text_for(p, name):
    t = p["ja"]
    if name: return t.replace("{name}", name)
    return t.replace("{name}、", "").replace("、{name}", "").replace("{name}", "")

def synth(text, voice=None, with_rate=True):
    cfg = {"audioEncoding": "MP3"}
    if with_rate: cfg["speakingRate"] = RATE
    body = json.dumps({"input": {"text": text},
                       "voice": {"languageCode": "ja-JP", "name": voice or VOICE},
                       "audioConfig": cfg}).encode()
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + KEY,
        data=body, headers={"Content-Type": "application/json"})
    import time
    err = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return base64.b64decode(json.load(r)["audioContent"])
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 + attempt * 3); continue
            break
        except Exception:                      # 通信の一時エラーは待って再試行
            if attempt < 5: time.sleep(2 + attempt * 3); continue
            raise
    if err is not None and err.code == 400 and with_rate:   # 話す速さに未対応の声ならスピード指定なしで再試行
        return synth(text, voice, False)
    raise SystemExit("TTS error %s: %s" % (err.code, err.read().decode()[:300]))

def main():
    phrases = json.load(open(os.path.join(ROOT, "phrases.json"), encoding="utf-8"))
    names = []
    p = os.path.join(ROOT, "names.txt")
    if os.path.exists(p):
        names = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]
    jobs = []
    names += [n.strip() for n in (os.environ.get("CHILD_NAMES") or "").split(",") if n.strip()]
    names = sorted(set(names))
    speech = []
    sp = os.path.join(ROOT, "speech.json")
    entries = []
    if os.path.exists(sp):
        entries += [(e["v"], e["t"]) for e in json.load(open(sp, encoding="utf-8"))]
    entries += [("p", ph["ja"]) for ph in phrases]          # あいさつ・はげましも 同じ声（p）で
    seen = set()
    def add(v, t, strip=False):
        if strip: t = t.strip()
        if not t: return
        k = K(v, t)
        if k in seen: return
        seen.add(k)
        speech.append((os.path.join(ROOT, "audio", "s", k + ".mp3"), t, vname(v)))
    name_voices = set()
    for v, t in entries:
        if "{name}" in t:
            name_voices.add(v)
            add(v, strip_name(t))                           # 名前なし版
            parts = t.split("{name}")
            if len(parts) == 2:                             # 名前入りは「前」「名前」「後」を つなげる
                add(v, parts[0], True); add(v, parts[1].lstrip("、"), True)
        else:
            add(v, t)
    for v in sorted(name_voices):
        for n in names:
            k = K(v, "@" + n)
            if k in seen: continue
            seen.add(k)
            speech.append((os.path.join(ROOT, "audio", "s", k + ".mp3"), n, vname(v)))
    jobs2 = [(f, t, None) for f, t in jobs] + speech
    todo = [(f, t, vo) for f, t, vo in jobs2 if FORCE or not os.path.exists(f)]
    chars = sum(len(t) for _, t, _ in todo)
    print("voice=%s names=%d 作る=%d本 文字数=%d" % (VOICE, len(names), len(todo), chars))
    if DRY:
        for f, t, vo in todo: print(" -", os.path.relpath(f, ROOT), "|", vo, "|", t)
        return
    if not KEY:
        print("GOOGLE_TTS_API_KEY が未設定のため、音声は作りません（アプリは端末の声で代用します）。")
        return
    for f, t, vo in todo:
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "wb").write(synth(t, vo))
        print("ok", os.path.relpath(f, ROOT))
    d = os.path.join(ROOT, "audio", "s")
    keys = sorted(x[:-4] for x in os.listdir(d)) if os.path.isdir(d) else []
    json.dump(keys, open(os.path.join(ROOT, "audio", "manifest.json"), "w"))
    print("manifest:", len(keys))

if __name__ == "__main__":
    main()
