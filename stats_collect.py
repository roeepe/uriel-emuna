#!/usr/bin/env python3
"""אוסף את מוני ההורדות של כל פרק ושומר צילום יומי.

גיטהאב סופר כל הורדה של כל קובץ שמע בנפרד, אבל הוא מחזיר רק מספר **מצטבר**.
מספר מצטבר לבדו לא עונה על "כמה לומדים" — הוא לא יודע להראות מגמה, ולא יודע
להבדיל בין פרק שירד 500 פעם בשנה לפרק שירד 500 פעם אתמול. לכן אנחנו שומרים
צילום יומי, וההפרש בין צילומים הוא ההאזנות של אותו יום.

🚨 מה שהמספר הזה **אינו**: הוא סופר הורדות, לא האזנות, ולא האזנות עד הסוף.
   אפליקציית פודקאסט שמורידה מראש נספרת גם אם איש לא לחץ נגן. נתוני האזנה
   אמיתיים (כמה דקות, כמה נטשו באמצע) קיימים רק אצל ספוטיפיי ויוטיוב.
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "uriel-emuna")
HIST = os.path.join(BASE, "data", "stats_history.json")

TOKEN = next(l.split("=", 1)[1].strip() for l in
             open(os.path.join(HOME, "personal-ops/podcasts.env"))
             if l.startswith("GITHUB_TOKEN="))

REPOS = {
    "kuzari": "roeepe/KuzariPod",
    **{s: f"roeepe/uriel-audio-{s}" for s in
       ["saadia", "chovot", "rambam", "ramban", "haran",
        "or-hashem", "ikarim", "maharal", "ramchal"]},
}

def api(url):
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "120",
         "-H", f"Authorization: token {TOKEN}",
         "-H", "Accept: application/vnd.github+json", url],
        capture_output=True, text=True).stdout
    try: return json.loads(out or "null")
    except Exception: return None

def counts_for(repo):
    """כל הנכסים של כל ה-releases במאגר, ומונה ההורדות של כל אחד."""
    out = {}
    rels = api(f"https://api.github.com/repos/{repo}/releases?per_page=100")
    if not isinstance(rels, list): return out
    for rel in rels:
        page = 1
        while True:
            assets = api(f"https://api.github.com/repos/{repo}/releases/"
                         f"{rel['id']}/assets?per_page=100&page={page}")
            if not isinstance(assets, list) or not assets: break
            for a in assets:
                if a["name"].lower().endswith((".mp3", ".m4a")):
                    out[a["name"]] = a["download_count"]
            page += 1
    return out

def main():
    hist = json.load(open(HIST)) if os.path.exists(HIST) else {"snapshots": []}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = {"at": stamp, "series": {}}
    for slug, repo in REPOS.items():
        c = counts_for(repo)
        if c: snap["series"][slug] = c
        print(f"{slug:11} {len(c):5} פרקים  {sum(c.values()):8} הורדות", flush=True)

    # לא שומרים צילום ריק - ריצה שנכשלה לא צריכה להיראות כמו יום בלי האזנות
    if not snap["series"]:
        print("לא התקבל שום נתון; לא נשמר צילום.", file=sys.stderr)
        return 1

    hist["snapshots"].append(snap)
    hist["snapshots"] = hist["snapshots"][-800:]      # ~שנתיים של ימים
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    tmp = HIST + ".tmp"
    json.dump(hist, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, HIST)

    tot = sum(sum(v.values()) for v in snap["series"].values())
    eps = sum(len(v) for v in snap["series"].values())
    print(f"\nסך הכל: {eps} פרקים, {tot} הורדות מצטברות. צילומים בהיסטוריה: {len(hist['snapshots'])}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
