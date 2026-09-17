#!/usr/bin/env python3
"""שומר שפרק שכבר יצא בפיד לא יוחלף בפרק אחר.

🚨 הבעיה שזה נולד ממנה (17/9/2026): לוח הפרסום נגזר ממיקום הפרק ברשימה
   (`schedule()` ב-make_site_data.py), ולכן הוספת שיעורים **באמצע** הסדרה
   מזיזה את כל מי שאחריהם. ברמח"ל נוספו 279 שיעורים, וחמישה פרקים שכבר
   יצאו בפיד הוחלפו בפרקים אחרים. באותו רגע זה לא הזיק — הפודקאסטים הוגשו
   לספוטיפיי באותו יום ואיש עוד לא האזין. בפעם הבאה כן יזיק: פרק שנעלם
   מהפיד נעלם גם מהאפליקציה של המאזין.

מה זה עושה: מחזיק תמונת מצב של כל פרק שתאריך הפרסום שלו כבר עבר, ומשווה
אליה אחרי כל בנייה. פרק חדש נרשם; פרק שהוחלף — נצעק עליו.

    python3 published_guard.py            # בדיקה + רישום פרקים חדשים
    python3 published_guard.py --check    # בדיקה בלבד, לא נוגע בתמונת המצב

יציאה 0 = תקין · 1 = פרק שכבר פורסם הוחלף.
"""
import json, os, sys
from datetime import datetime, timezone

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site/public/data")
SNAP = os.path.join(D, "published.json")
CHECK_ONLY = "--check" in sys.argv


def main():
    now = datetime.now(timezone.utc)
    raw = json.load(open(SNAP)) if os.path.exists(SNAP) else {}
    counts = raw.pop("_counts", {}) if isinstance(raw, dict) else {}
    snap = raw
    index = json.load(open(f"{OUT}/index.json"))

    broken, shrunk, added = [], [], 0
    for entry in index:
        slug = entry["slug"]
        if entry.get("external"):
            continue
        try:
            items = json.load(open(f"{OUT}/{slug}.json"))["items"]
        except FileNotFoundError:
            continue

        was = snap.get(slug, {})
        now_out = dict(was)
        for it in items:
            pub = it.get("pub")
            if not pub or datetime.fromisoformat(pub.replace("Z", "+00:00")) > now:
                continue
            asset = it["url"].rsplit("/", 1)[-1]
            prev = was.get(pub)
            if prev is None:
                now_out[pub] = asset
                added += 1
            elif prev != asset:
                broken.append((slug, pub[:10], prev, asset, it["title"]))
        # 🚨 גם ספירה יורדת היא אובדן. 17/9/2026: תאריך העוגן של הלוח חושב
        #    כ"היום פחות 14 יום", ולכן כל בנייה הזיזה את הלוח קדימה והחזירה
        #    פודקאסט מ-9 פרקים ל-4. אף פרק לא "הוחלף" — הם פשוט נעלמו,
        #    והבדיקה לפי תאריך לבדה לא ראתה את זה.
        was_n = counts.get(slug, 0)
        now_n = len(now_out)
        if now_n < was_n:
            shrunk.append((slug, was_n, now_n))
        counts[slug] = max(now_n, was_n)
        snap[slug] = now_out

    for slug, was_n, now_n in shrunk:
        print(f'❌ {slug}: מספר הפרקים שיצאו ירד מ-{was_n} ל-{now_n} — פרקים נעלמו')

    for slug, day, prev, cur, title in broken:
        print(f'❌ {slug} · {day}: הפרק שיצא הוחלף')
        print(f'     היה: {prev}')
        print(f'     עכשיו: {cur}  ({title})')

    if not broken and not shrunk:
        print(f'✅ אף פרק שפורסם לא הוחלף ולא נעלם'
              + (f' · נרשמו {added} פרקים חדשים' if added else ''))

    if not CHECK_ONLY:
        json.dump({**snap, "_counts": counts}, open(SNAP, "w"), ensure_ascii=False, indent=1)

    return 1 if (broken or shrunk) else 0


if __name__ == "__main__":
    sys.exit(main())
