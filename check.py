#!/usr/bin/env python3
"""בודק שהאתר באמת עובד — כל עמוד נפתח, וקובצי השמע באמת מתנגנים.

🚨 נולד מתקלה אמיתית: «ספר הכוזרי לא נפתח לי» ו«חלק מהשיעורים לא נפתחים».
   שתי התקלות היו שקטות לגמרי — העמוד נראה תקין בבנייה, הפיד נראה תקין,
   ורק לחיצה אמיתית גילתה 404. שתיהן היו מסוג שבדיקה אוטומטית תופסת מיד:

   1. כרטיס בעמוד הבית שמפנה לסדרה שאין לה קובץ נתונים.
   2. כתובת שמע שנבנתה משם פודקאסט שאין לו מאגר (אחרי פיצול סדרה).

השימוש: `python3 check.py` — יציאה 1 אם משהו שבור.
        `python3 check.py --full` — סורק את *כל* קובצי השמע ולא מדגם.
"""
import json, os, random, subprocess, sys
import concurrent.futures as cf

BASE = "https://uriel-emuna.vercel.app"
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "public", "data")
SAMPLE_PER_SERIES = 10

def http(url, rng=False):
    cmd = ["curl", "-sL", "--max-time", "60", "-o", "/dev/null", "-D", "-", url]
    if rng: cmd[2:2] = ["-r", "0-0"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    codes = [l.split()[1] for l in out.splitlines() if l.startswith("HTTP/")]
    size = -1
    for l in out.splitlines():
        if l.lower().startswith("content-range"):
            size = int(l.split("/")[-1])
    return (codes[-1] if codes else "?"), size

def main():
    full = "--full" in sys.argv
    problems = []

    index = json.load(open(os.path.join(D, "index.json")))
    print(f"{len(index)} סדרות")

    for s in index:
        slug = s["slug"]
        # 1. לכל כרטיס בעמוד הבית חייב להיות קובץ נתונים — אחרת העמוד נתקע
        code, _ = http(f"{BASE}/data/{slug}.json")
        if code != "200":
            problems.append(f"עמוד הסדרה «{s['name']}» לא ייפתח: /data/{slug}.json מחזיר {code}")
            continue
        code, _ = http(f"{BASE}/cover/{slug}.jpg")
        if code != "200":
            problems.append(f"חסרה עטיפה ל«{s['name']}» ({code})")
        # 2. פיד — או פיד אמיתי, או הפניה לפיד החיצוני
        code, _ = http(f"{BASE}/feed/{slug}.xml")
        if code not in ("200", "301", "302"):
            problems.append(f"הפיד של «{s['name']}» מחזיר {code}")

    # 3. השמע עצמו
    targets = []
    for s in index:
        d = json.load(open(os.path.join(D, f"{s['slug']}.json")))
        its = d["items"]
        pick = its if full else (its[:1] + its[-1:] +
                                 random.sample(its, min(SAMPLE_PER_SERIES, len(its))))
        for i in pick:
            targets.append((s["slug"], i["n"], i["url"], i["size"]))

    def probe(t):
        slug, n, url, size = t
        code, real = http(url, rng=True)
        return (slug, n, code in ("200", "206") and real == size, code)

    with cf.ThreadPoolExecutor(12) as ex:
        for slug, n, ok, code in ex.map(probe, targets):
            if not ok:
                problems.append(f"שיעור #{n} ב«{slug}» לא מתנגן ({code})")

    print(f"נבדקו {len(targets)} קובצי שמע" + ("" if full else " (מדגם)"))
    if problems:
        print(f"\n{len(problems)} תקלות:")
        for p in problems[:25]:
            print("  ✗", p)
        return 1
    print("הכל תקין.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
