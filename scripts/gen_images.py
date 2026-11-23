#!/usr/bin/env python3
"""サンプルの かぞく イラストを Gemini の がぞうモデル(Nano Banana)で つくる。
env: GEMINI_API_KEY, IMG_MODEL, FORCE"""
import os, sys, json, base64, time, urllib.request, urllib.error
KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("IMG_MODEL") or "gemini-2.5-flash-image"
FORCE = os.environ.get("FORCE") == "1"
STYLE = ("Warm, friendly children's-book illustration, soft watercolor and gouache texture, gentle rounded shapes, "
         "cozy pastel palette with warm cream background, head-and-shoulders portrait of a smiling Japanese person facing the viewer, "
         "square composition, no text, no letters, no watermark. ")
PEOPLE = {
 "mama": "A kind, gentle Japanese mother in her late 30s, shoulder-length dark hair, soft cardigan, warm smile.",
 "papa": "A cheerful Japanese father in his early 40s, short black hair, light stubble, casual shirt, big friendly smile.",
 "onii": "A sporty Japanese teenage big brother around 15, short messy hair, school gym jacket, confident grin.",
 "onee": "A cheerful Japanese teenage big sister around 14, hair in a ponytail with a small ribbon, bright smile.",
 "obaa": "A sweet Japanese grandmother in her late 60s, short gray hair, round glasses, knitted vest, kind wrinkled smile.",
}
def gen(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}).encode()
    err = None
    for a in range(5):
        try:
            req = urllib.request.Request(url, body, {"Content-Type": "application/json", "x-goog-api-key": KEY})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            for c in d.get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    inl = p.get("inlineData") or p.get("inline_data")
                    if inl: return base64.b64decode(inl["data"]), inl.get("mimeType", "image/png")
            err = "no image: " + json.dumps(d)[:300]
        except urllib.error.HTTPError as e:
            err = f"{e.code} {e.read().decode()[:300]}"
            if e.code in (400, 403, 404): break
        except Exception as e:
            err = str(e)
        time.sleep(3 * (a + 1))
    raise RuntimeError(err)
def main():
    if not KEY: sys.exit("no key")
    os.makedirs("portraits", exist_ok=True); bad = 0
    for k, desc in PEOPLE.items():
        path = f"portraits/{k}.png"
        if os.path.exists(path) and not FORCE: continue
        try:
            img, mt = gen(STYLE + desc)
            open(path, "wb").write(img); print("ok", k, len(img), mt)
        except Exception as e:
            bad += 1; print("NG", k, e)
    sys.exit(1 if bad else 0)
main()
