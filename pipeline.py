#!/usr/bin/env python3
"""מוריד את ההקלטות מהדרייב, מדחיס אותן לדיבור, ומעלה ל-Releases של GitHub.

עובד במנות: מוריד ~40 קבצים, מקודד אותם במקביל, מעלה, ומוחק מהדיסק — כך
שהצריכה בכל רגע נתון היא כמה מאות מגה ולא 100 ג'יגה. אידמפוטנטי לחלוטין:
נכס שכבר יושב ב-release בגודל הנכון מדולג, ולכן אפשר לעצור ולהריץ שוב.

🚨 הדחיסה ל-48k מונו היא החלטה מודעת: אלה שיעורי דיבור בקול אחד, וזה עדיין
   מעל האיכות של הקלטות הכוזרי שכבר מתפרסמות בפועל (32k מונו).
"""
import json, os, re, subprocess, sys, time, hashlib, threading
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "uriel-emuna")
WORK = os.path.join(BASE, "work")
ROOT_ID = "1CRxSrjs0ec_fTHfhlyNvUZZgVexI0Tgr"
RCLONE = os.path.join(HOME, "bin", "rclone")
FFMPEG = os.path.join(HOME, "shorts", "bin", "ffmpeg")
FFPROBE = os.path.join(HOME, "shorts", "bin", "ffprobe")
CHUNK = int(os.environ.get("URIEL_CHUNK", 40))
ENC_WORKERS = int(os.environ.get("URIEL_ENC", 5))
UP_WORKERS = int(os.environ.get("URIEL_UP", 4))
DL_TRANSFERS = os.environ.get("URIEL_DL", "8")

TOKEN = next(l.split("=", 1)[1].strip() for l in
             open(os.path.join(HOME, "personal-ops/podcasts.env"))
             if l.startswith("GITHUB_TOKEN="))

def api(method, url, data=None, extra=()):
    cmd = ["curl", "-sS", "--max-time", "1800", "-X", method,
           "-H", f"Authorization: token {TOKEN}",
           "-H", "Accept: application/vnd.github+json", *extra, url]
    if data is not None:
        cmd[-1:] = ["-d", json.dumps(data), url]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try: return json.loads(out or "{}")
    except Exception: return {"_raw": out[:300]}

# 🚨 גיטהאב מגביל release אחד ל-1000 קבצים. לרמב"ם יש 1227, ולכן 226 שיעורים
#    נדחו בשקט עם "file_count limited to 1000 assets per release". מכאן ואילך
#    כל release מקבל עד 900 קבצים, והתג נשמר לצד כל נכס כי הוא חלק מהכתובת.
PER_RELEASE = 900

def release_by_tag(repo, tag):
    """מחזיר את מזהה ה-release, ויוצר אותו אם אינו קיים.

    🚨 שני חוטי העלאה קראו לזה בו-זמנית, שניהם ניסו ליצור את אותו release,
       והשני קיבל 'already_exists' בלי id — וכל הריצה נפלה על KeyError.
       לכן גם נעילה, וגם קריאה חוזרת אם היצירה נכשלה."""
    r = api("GET", f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
    if r.get("id"): return r["id"]
    r = api("POST", f"https://api.github.com/repos/{repo}/releases",
            {"tag_name": tag, "name": "קבצי השמע" + ("" if tag == "audio" else " " + tag.split("-")[-1]),
             "body": "קבצי השמע של הפודקאסט. הפיד מוגש מ-uriel-emuna.vercel.app",
             "draft": False, "prerelease": False})
    if r.get("id"): return r["id"]
    for _ in range(5):                      # מישהו אחר יצר אותו בינתיים
        time.sleep(2)
        r = api("GET", f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
        if r.get("id"): return r["id"]
    raise RuntimeError(f"cannot open release {tag}: {str(r)[:200]}")

def tag_name(n):
    return "audio" if n == 0 else f"audio-{n + 1}"

def existing(repo, rid):
    have, page = {}, 1
    while True:
        c = api("GET", f"https://api.github.com/repos/{repo}/releases/{rid}/assets?per_page=100&page={page}")
        if not isinstance(c, list) or not c: break
        for a in c: have[a["name"]] = a
        page += 1
    return have

def dur_of(p):
    o = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    try: return float(o)
    except Exception: return 0.0

def main():
    man = json.load(open(os.path.join(BASE, "data/manifest.json")))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only: man = [r for r in man if r["slug"] == only]
    os.makedirs(WORK, exist_ok=True)
    meta_path = os.path.join(BASE, f"data/audio_meta_{only or 'all'}.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}

    by_slug = {}
    for r in man: by_slug.setdefault(r["slug"], []).append(r)

    for slug, rows in by_slug.items():
        repo = f"roeepe/uriel-audio-{slug}"
        # פותחים כל release שכבר קיים, וסופרים כמה מקום נשאר בכל אחד. לא מחשבים
        # את היעד מראש לפי אינדקס: 1001 שיעורי הרמב"ם כבר יושבים ב-audio, ותג
        # מחושב היה שולח אליו קבצים חדשים שאין להם שם מקום.
        rids, have, fill = {}, {}, {}
        n = 0
        while True:
            t = tag_name(n)
            got = api("GET", f"https://api.github.com/repos/{repo}/releases/tags/{t}")
            if not got.get("id"): break
            rids[t] = got["id"]
            a = existing(repo, got["id"])
            fill[t] = len(a)
            for k, v in a.items(): v["tag"] = t; have[k] = v
            n += 1
        if not rids:
            t = tag_name(0); rids[t] = release_by_tag(repo, t); fill[t] = 0

        tag_lock = threading.Lock()

        def target_tag():
            """ה-release הראשון שיש בו מקום; אם כולם מלאים — פותחים את הבא."""
            with tag_lock:
                for i in range(len(fill) + 2):
                    t = tag_name(i)
                    if fill.get(t, 0) < PER_RELEASE:
                        if t not in rids:
                            rids[t] = release_by_tag(repo, t); fill.setdefault(t, 0)
                        return t
                raise RuntimeError("no room")

        todo = [r for r in rows
                if not (r["asset"] in have and have[r["asset"]].get("state") == "uploaded"
                        and r["asset"] in meta and meta[r["asset"]].get("tag"))]
        # שיעור שכבר הועלה אך חסר לו התג — משלימים מהמצב האמיתי ולא מעלים שוב
        for r in rows:
            a = have.get(r["asset"])
            if a and a.get("state") == "uploaded" and r["asset"] in meta:
                meta[r["asset"]]["tag"] = a["tag"]
        todo = [r for r in todo if r["asset"] not in meta or not meta[r["asset"]].get("tag")]
        print(f"\n=== {slug}: {len(rows)} קבצים, {len(rows)-len(todo)} כבר שם, {len(todo)} לעשות", flush=True)
        for i in range(0, len(todo), CHUNK):
            batch = todo[i:i + CHUNK]
            d = os.path.join(WORK, slug)
            subprocess.run(["rm", "-rf", d]); os.makedirs(d, exist_ok=True)
            # 1. הורדה — כל קובץ ישירות לשם השטוח שלו.
            #
            # 🚨 הגרסה הקודמת הורידה מנה שלמה ב-`copy --files-from` והתעלמה מקוד
            #    היציאה. כשההורדה נפלה, כל 40 הקבצים של אותה מנה נרשמו כ-FAIL בלי
            #    שאיש ידע למה — ככה נעלמו 226 שיעורים ברמב"ם. עכשיו כל קובץ נבדק
            #    בנפרד, וכישלון שלו הוא כישלון שלו בלבד.
            def dl(r):
                dst = os.path.join(d, "src-" + r["asset"])
                for attempt in range(3):
                    cp = subprocess.run(
                        [RCLONE, f"--drive-root-folder-id={ROOT_ID}", "copyto",
                         "gdrive:" + r["path"], dst,
                         "--retries", "3", "--low-level-retries", "20"],
                        capture_output=True, text=True)
                    if cp.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0:
                        return (r, dst)
                    time.sleep(3 * (attempt + 1))
                print(f"  DL-FAIL {r['asset']}  rc={cp.returncode} {cp.stderr.strip()[:120]}", flush=True)
                return (r, None)
            fetched = list(ThreadPoolExecutor(int(DL_TRANSFERS)).map(dl, batch))
            # 2. קידוד
            def enc(t):
                r, src = t
                if not src: return (r, None, 0)
                dst = os.path.join(d, r["asset"])
                subprocess.run([FFMPEG, "-v", "error", "-y", "-i", src,
                                "-ac", "1", "-b:a", "48k", "-ar", "44100",
                                "-map_metadata", "-1", dst], capture_output=True)
                if not os.path.exists(dst): return (r, None, 0)
                return (r, dst, dur_of(dst))
            encoded = list(ThreadPoolExecutor(ENC_WORKERS).map(enc, fetched))
            # 3. העלאה
            def up(t):
                r, dst, dur = t
                if not dst: return (r, False, 0, 0)
                size = os.path.getsize(dst)
                r["tag"] = target_tag()
                with tag_lock: fill[r["tag"]] = fill.get(r["tag"], 0) + 1
                cur = have.get(r["asset"])
                if cur: api("DELETE", f"https://api.github.com/repos/{repo}/releases/assets/{cur['id']}")
                for _ in range(3):
                    res = api("POST",
                              f"https://uploads.github.com/repos/{repo}/releases/{rids[r['tag']]}/assets?name={r['asset']}",
                              extra=("-H", "Content-Type: audio/mpeg", "--data-binary", f"@{dst}"))
                    if res.get("state") == "uploaded" and res.get("size") == size:
                        return (r, True, size, dur)
                    msg = (res.get("errors") or [{}])[0].get("message") or res.get("message")
                    if msg: print(f"  UP-ERR {r['asset']} {str(msg)[:110]}", flush=True)
                    time.sleep(4)
                return (r, False, size, dur)
            for r, ok, size, dur in ThreadPoolExecutor(UP_WORKERS).map(up, encoded):
                if ok:
                    meta[r["asset"]] = {"size": size, "duration": round(dur), "tag": r["tag"]}
                else:
                    print(f"  FAIL {r['asset']}  {r['path'][:70]}", flush=True)
            json.dump(meta, open(meta_path, "w"), ensure_ascii=False)
            subprocess.run(["rm", "-rf", d])
            done = sum(1 for r in rows if r["asset"] in meta)
            print(f"  {slug}: {done}/{len(rows)}  ({time.strftime('%H:%M:%S')})", flush=True)

    print("\n=== סיום ===", flush=True)

if __name__ == "__main__":
    main()
