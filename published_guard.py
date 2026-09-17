#!/usr/bin/env python3
"""שומר שפרק שכבר יצא בפיד לא יוחלף בפרק אחר ולא ייעלם.

🚨 שתי הדרכים שבהן פרק נעלם למאזין:

1. **החלפה.** לוח הפרסום נגזר ממיקום הפרק ברשימה, ולכן הוספת שיעורים
   באמצע סדרה מזיזה את כל מי שאחריהם. ברמח"ל נוספו 279 שיעורים וחמישה
   פרקים שכבר יצאו הוחלפו באחרים (17/9/2026).

2. **היעלמות.** תאריך העוגן של הלוח חושב כ"היום פחות 14 יום", ולכן כל
   בנייה הזיזה את הלוח קדימה והחזירה פודקאסט מ-9 פרקים ל-4 (17/9/2026).

פרק שנדחק מהפיד **אינו מתעדכן — הוא יורד** מהאפליקציה של מי שכבר מנוי.

    python3 published_guard.py            # בדיקה + רישום
    python3 published_guard.py --check    # בדיקה בלבד
    python3 published_guard.py --accept "סיבה"   # אישור מכוון של ירידה

יציאה 0 = תקין · 1 = פרק שכבר פורסם הוחלף או נעלם.
"""
import json, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "site/public/data")
SNAP = os.path.join(D, "published.json")
CHECK_ONLY = "--check" in sys.argv
ACCEPT = sys.argv[sys.argv.index("--accept") + 1] if "--accept" in sys.argv else None


def feeds():
    """כל הפודקאסטים — כולל החיבורים שבתוך אוסף.

    🚨 הגרסה הראשונה עברה רק על השורות העליונות ב-index.json, ולכן 14 מתוך
       23 הפודקאסטים (ramchal-2 ואילך) לא נשמרו כלל.
    """
    for c in json.load(open(f"{OUT}/index.json")):
        for s in (c.get("works") or [c]):
            if not s.get("external"):
                yield s["slug"]


def main():
    now = datetime.now(timezone.utc)
    raw = json.load(open(SNAP)) if os.path.exists(SNAP) else {}
    counts = raw.pop("_counts", {})
    raw.pop("_accepted", None)
    snap = raw

    broken, shrunk, added = [], [], 0
    for slug in feeds():
        try:
            items = json.load(open(f"{OUT}/{slug}.json"))["items"]
        except FileNotFoundError:
            continue

        was = snap.get(slug, {})
        history = dict(was)
        live = 0
        for it in items:
            pub = it.get("pub")
            if not pub or datetime.fromisoformat(pub.replace("Z", "+00:00")) > now:
                continue
            live += 1
            asset = it["url"].rsplit("/", 1)[-1]
            prev = was.get(pub)
            if prev is None:
                history[pub] = asset
                added += 1
            elif prev != asset:
                broken.append((slug, pub[:10], prev, asset, it["title"]))

        # 🚨 נספרים הפרקים שחיים **עכשיו**, לא אורך ההיסטוריה. ההיסטוריה רק
        #    גדלה, ולכן מדידה לפיה לא ראתה ירידה מ-9 פרקים ל-1.
        if live < counts.get(slug, 0):
            shrunk.append((slug, counts[slug], live))
        counts[slug] = live
        snap[slug] = history

    for slug, was_n, now_n in shrunk:
        print(f"❌ {slug}: הפרקים שבפיד ירדו מ-{was_n} ל-{now_n} — פרקים נעלמו למאזינים")
    for slug, day, prev, cur, title in broken:
        print(f"❌ {slug} · {day}: הפרק שיצא הוחלף")
        print(f"     היה: {prev}")
        print(f"     עכשיו: {cur}  ({title})")

    bad = bool(broken or shrunk)
    if not bad:
        print(f"✅ {len(counts)} פודקאסטים נבדקו · אף פרק לא הוחלף ולא נעלם"
              + (f" · {added} פרקים חדשים" if added else ""))
    elif ACCEPT:
        print(f"\n⚠️  אושר במכוון: {ACCEPT}")

    if not CHECK_ONLY and (not bad or ACCEPT):
        out = {**snap, "_counts": counts}
        if ACCEPT:
            out["_accepted"] = {"at": now.isoformat(timespec="minutes"), "why": ACCEPT}
        json.dump(out, open(SNAP, "w"), ensure_ascii=False, indent=1)

    return 0 if (not bad or ACCEPT) else 1


if __name__ == "__main__":
    sys.exit(main())
