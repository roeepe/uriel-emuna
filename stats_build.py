#!/usr/bin/env python3
"""מחשב האזנות אמיתיות לכל שיעור, אחרי סינון סריקות של פלטפורמות.

🚨 הבעיה שזה נולד ממנה: גיטהאב סופר כל הורדה של קובץ, ואינו יודע מי הוריד.
   כשספוטיפיי קולט פודקאסט הוא מוריד את **כל** הפרקים כדי לארח עותק משלו,
   וכך ב-17/9/2026 המונה קפץ מ-295 ל-6,704 ביום אחד. 6,400 מהם מכונה.

איך מזהים סריקה: ביום שבו רוב מוחלט של פרקי הסדרה עלו **באותו מספר בדיוק**,
זו סריקה ולא אנשים. אדם מוריד פרק אחד או שניים; פלטפורמה מורידה 464 פרקים
ב-+2 כל אחד. בפועל ב-17/9: ברמב"ם 1,152 פרקים מתוך 1,226 עלו בדיוק ב-2.

הערך הנפוץ מוחסר מכל פרק באותו יום, ומה שנשאר הוא ההפרש שאדם יצר.

🚨 גם מה שנשאר אינו "האזנות" במובן המדויק: אפליקציית פודקאסט שמורידה מראש
   נספרת גם אם איש לא לחץ נגן. לכן בכל מקום שבו המספר מוצג הוא נקרא
   **הורדות**, לא האזנות. נתוני האזנה אמיתיים קיימים רק אצל ספוטיפיי.
"""
import json, os, sys, collections
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "site/public/data")

# אחוז מפרקי הסדרה שחייבים לזוז באותו ערך כדי שזו תיחשב סריקה.
SWEEP_SHARE = 0.55
# סריקה היא ערך קטן שחוזר על עצמו. +30 על 90% מהסדרה אינו סריקה אלא אירוע.
SWEEP_MAX = 5


def sweeps_and_real(snapshots):
    """מחזיר (הורדות אמיתיות לכל נכס, יומן הסריקות שזוהו)."""
    real = collections.Counter()
    log = []
    for prev, cur in zip(snapshots, snapshots[1:]):
        day = cur["at"][:10]
        for slug, now in cur["series"].items():
            was = prev["series"].get(slug, {})
            # 🚨 המכנה הוא הפרקים שהיו **בצילום הקודם**, לא כל הפרקים היום.
            #    ברמח"ל נוספו 279 פרקים באותו יום; הם לא יכלו לזוז, ולכן
            #    לפי כל הפרקים נראה שרק 44% זזו — והסריקה האמיתית פספסה.
            known = {k: now[k] - was[k] for k in now if k in was}
            if not known:
                continue
            moved = [d for d in known.values() if d > 0]
            if not moved:
                continue
            mode, n = collections.Counter(moved).most_common(1)[0]
            sweep = 0
            if mode <= SWEEP_MAX and n >= SWEEP_SHARE * len(known):
                sweep = mode
                log.append({"day": day, "slug": slug, "per_episode": sweep,
                            "episodes": len(known), "removed": sweep * len(known)})
            delta = known
            for k, d in delta.items():
                if d > 0:
                    real[k] += max(0, d - sweep)
    return real, log


def main():
    hist = json.load(open(os.path.join(D, "stats_history.json")))["snapshots"]
    if len(hist) < 2:
        print("צריך לפחות שני צילומים כדי לחשב הפרש", file=sys.stderr)
        return 1

    real, log = sweeps_and_real(hist)
    json.dump(dict(real), open(os.path.join(D, "downloads.json"), "w"), ensure_ascii=False)
    json.dump(log, open(os.path.join(D, "sweeps.json"), "w"), ensure_ascii=False)

    raw_total = sum(hist[-1]["series"][s][k] - hist[0]["series"].get(s, {}).get(k, 0)
                    for s in hist[-1]["series"] for k in hist[-1]["series"][s])
    removed = sum(x["removed"] for x in log)
    print(f"מ-{hist[0]['at'][:10]} עד {hist[-1]['at'][:10]}")
    print(f"  גיטהאב ספר : {raw_total:,}")
    print(f"  סריקות     : {removed:,} ({len(log)} סריקות זוהו)")
    print(f"  נשאר אמיתי : {sum(real.values()):,}")
    for x in log:
        print(f"    {x['day']} · {x['slug']:14} +{x['per_episode']} × {x['episodes']} פרקים")
    return 0


if __name__ == "__main__":
    sys.exit(main())
