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
NOAR = False
def gen(prompt, ref=None, rmime=None, ar=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = json.dumps({"contents": [{"parts": ([{"inline_data": {"mime_type": rmime, "data": ref}}] if ref else []) + [{"text": prompt}]}], "generationConfig": dict({"responseModalities": ["IMAGE"]}, **({"imageConfig": {"aspectRatio": ar}} if ar and not NOAR else {}))}).encode()
    global NOAR
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
            if e.code == 400 and ar and not NOAR:
                NOAR = True; continue
            if e.code in (400, 403, 404): break
        except Exception as e:
            err = str(e)
        time.sleep(3 * (a + 1))
    raise RuntimeError(err)
PETS = {"dog":"a cute puppy (Shiba-inu-like, tan and cream fur)","cat":"a cute kitten (orange tabby with white chest)","rabbit":"a cute white bunny rabbit with soft pink inner ears","bird":"a cute round little yellow chick-like songbird","hamster":"a cute chubby golden hamster with cream belly"}
MOODS = {"happy":"very happy: eyes closed in a big smile, open mouth, rosy cheeks, joyful","sad":"lonely and a little sad: droopy ears or feathers, big teary eyes, small frown, gentle and cute (not distressing)"}
PSTYLE = "Warm friendly children's-book illustration, soft watercolor and gouache texture, rounded shapes, pastel palette, plain warm cream background, centered head-and-upper-body character, square, no text, no watermark. "
def gen_edit(img_b64, prompt):
    return gen(prompt, img_b64, "image/webp")
def to_webp(raw, path):
    from PIL import Image; import io
    Image.open(io.BytesIO(raw)).convert("RGB").resize((512,512)).save(path, "WEBP", quality=85)
def pets():
    os.makedirs("pets", exist_ok=True); bad = 0
    for k, d in PETS.items():
        base = f"pets/{k}_normal.webp"
        try:
            if not os.path.exists(base) or FORCE:
                raw, _ = gen(PSTYLE + d + " Calm, content, looking at the viewer with a gentle smile."); to_webp(raw, base); print("ok", base)
            ref = base64.b64encode(open(base, "rb").read()).decode()
            for m, md in MOODS.items():
                path = f"pets/{k}_{m}.webp"
                if os.path.exists(path) and not FORCE: continue
                raw, _ = gen(PSTYLE + f"Edit this exact same character (same species, colors, style, framing) so that it looks {md}. Keep everything else identical.", ref, "image/webp"); to_webp(raw, path); print("ok", path)
        except Exception as e:
            bad += 1; print("NG", k, e)
    return bad
SCENES = {
 "aisatsu":"Japanese schoolchildren greeting each other and a teacher at the school gate on a sunny morning, bowing and waving",
 "komatta":"a child raising a hand asking for help in a classroom while a kind teacher kneels down to listen",
 "mochimono":"a school bag, pencils, a notebook, indoor shoes and scissors neatly arranged on a wooden desk",
 "kyushoku":"Japanese school lunch time, children in white aprons serving trays with rice, miso soup, salad and milk",
 "ie":"a cozy Japanese home, a family breakfast table with toast and mandarin oranges, living room with TV in the background",
 "kaimono":"a child shopping with a parent in a small friendly Japanese supermarket, shopping basket, cashier counter",
 "gyoji":"Japanese seasonal events: cherry blossoms, carp streamers, summer festival lanterns, autumn leaves, a snowman",
 "rika":"a bright science classroom with a child holding a magnifying glass, a potted plant, a beaker and a solar system poster",
 "shakai":"a social studies class with a map of Japan on the wall, a globe, and children looking at a model town",
 "karada":"a friendly clinic where a kind doctor with a stethoscope talks gently to a child, a body diagram poster on the wall",
 "kazu":"colorful counting blocks, an abacus, a wall calendar and a clock on a child's desk",
 "sansuu":"a math class, a blackboard with plus, minus, times and divide symbols, children with notebooks",
 "jugyou":"a classroom lesson, a teacher at the blackboard, students with textbooks, a few raising hands",
 "otayori":"a parent and child reading a school notice letter together at a table, a backpack and an excursion picnic basket nearby",
 "kanji1":"a calligraphy table with brush, inkstone and paper, calm and traditional, no characters",
 "kanji2":"a nature scene with mountains, a river, a forest, the sun and the moon",
 "kanji3":"a Japanese elementary school building and schoolyard with children playing",
 "story_hajimete":"a new transfer student standing at the classroom door, classmates and a smiling teacher welcoming them",
 "story_wakaranai":"a child looking puzzled in math class, the teacher kindly helping, small question-mark shapes floating",
 "story_onaka":"a child holding their tummy in a school nurse's office, a kind nurse caring for them",
 "ev_asa":"children walking to school in the morning with randoseru backpacks along a cherry-tree street",
 "ev_asobi":"children playing together in a schoolyard playground, jump rope and ball games",
}
SSTYLE = "Warm friendly children's-book illustration, soft watercolor and gouache texture, pastel palette, wide 16:9 landscape scene, no text, no letters, no watermark. "
def scenes():
    os.makedirs("scenes", exist_ok=True); bad = 0
    from PIL import Image; import io
    for k, d in SCENES.items():
        path = f"scenes/{k}.webp"
        if os.path.exists(path) and not FORCE: continue
        try:
            raw, _ = gen(SSTYLE + "Scene: " + d + ".", ar="16:9")
            im = Image.open(io.BytesIO(raw)).convert("RGB"); w, h = im.size
            im = im.resize((640, int(640 * h / w))); im.save(path, "WEBP", quality=82); print("ok", path, w, h)
        except Exception as e:
            bad += 1; print("NG", k, e)
    return bad
def main():
    if not KEY: sys.exit("no key")
    os.makedirs("portraits", exist_ok=True); bad = 0
    for k, desc in PEOPLE.items():
        path = f"portraits/{k}.png"
        if (os.path.exists(path) or os.path.exists(f"portraits/{k}.webp")) and not FORCE: continue
        try:
            img, mt = gen(STYLE + desc)
            open(path, "wb").write(img); print("ok", k, len(img), mt)
        except Exception as e:
            bad += 1; print("NG", k, e)
    bad += pets()
    bad += scenes()
    sys.exit(1 if bad else 0)
main()
