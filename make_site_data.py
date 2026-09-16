#!/usr/bin/env python3
"""כותב את קובצי הנתונים שהאתר והפידים קוראים."""
import json, os, re, uuid, glob
D = "data"; OUT = "site/public/data"
NS = uuid.UUID("7a3c9d20-0000-4000-8000-757269656c00")
LINKS = json.load(open(f"{D}/links.json"))

def hhmmss(s):
    s = int(s or 0); return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

def parts_of(items):
    """לאיזו חטיבה שייך כל שיעור — הרמה שבאמת מחלקת את החומר.

    🚨 ברמב"ם, «מורה הנבוכים» הוא תיקייה אחת שמכילה *שני סבבי לימוד שלמים*
       של אותו ספר (תש"פ-תשפ"א ותשפ"ב-תשפ"ג). כשמציגים אותה כחטיבה אחת,
       הספר נלמד פעמיים ברצף בלי שום סימן שמדובר בשתי סדרות נפרדות — וזה מה
       שהרב בן ציון תפס. לכן חטיבה גדולה שיש בה כמה תת-תיקיות נפתחת לרמה
       הבאה, ומי שמסתכל רואה שני סבבים ולא רצף אחד.
    """
    from collections import Counter
    top = Counter()
    kids = {}
    for it in items:
        sec = [x for x in it["section"] if x]
        if not sec: continue
        top[sec[0]] += 1
        kids.setdefault(sec[0], set()).add(sec[1] if len(sec) > 1 else None)
    out = {}
    for name, n in top.items():
        ch = {k for k in kids[name] if k}
        out[name] = (n >= 150 and len(ch) >= 2)
    return out

# סדרה אחת בדרייב יכולה להיות כמה פודקאסטים. במורה הנבוכים יש שני סבבי
# לימוד שלמים של אותו ספר, והרב ביקש שכל סבב יהיה פודקאסט בפני עצמו.
def _moreh(sec, word):
    return len(sec) > 1 and "מורה" in sec[0] and word in sec[1]

SPLITS = {
    "rambam": [
        ("rambam", 'כתבי הרמב"ם — הקדמות וספר המצוות',
         lambda sec: not (sec and "מורה" in sec[0])),
        ("moreh-rishon", 'מורה הנבוכים — סבב לימוד ראשון, תש"פ-תשפ"א',
         lambda sec: _moreh(sec, "ראשון")),
        ("moreh-sheni", 'מורה הנבוכים — סבב לימוד שני, תשפ"ב-תשפ"ג',
         lambda sec: _moreh(sec, "שני")),
    ],
}

comp = json.load(open(f"{D}/episodes_composed.json"))
# הסדרה שפוצלה יורדת מהרשימה, ובמקומה נכנסים החלקים שלה
expanded = {}
for _slug, _s in comp.items():
    if _slug not in SPLITS:
        expanded[_slug] = _s
        continue
    for out_slug, out_name, pred in SPLITS[_slug]:
        picked = [i for i in _s["items"] if pred([x for x in i["section"] if x])]
        # כשכל הפודקאסט הוא «מורה הנבוכים, סבב X», אין טעם לחזור על זה
        # בכל שורה — מורידים את שתי הרמות שהפכו לשם הפודקאסט עצמו
        drop = 2 if out_slug != _slug else 0
        for i in picked:
            i = dict(i)
            i["section"] = [x for x in i["section"] if x][drop:]
        # 🚨 שם המאגר נגזר מהסדרה *שממנה פוצלנו*, לא מהפודקאסט החדש. קבצי
        #    מורה הנבוכים יושבים ב-uriel-audio-rambam; בנייה לפי השם החדש
        #    יצרה כתובות ל-uriel-audio-moreh-rishon שלא קיים, וכל 782
        #    השיעורים החזירו 404. הרב בן ציון הוא שתפס את זה.
        expanded[out_slug] = {"name": out_name, "series": _s["series"],
                              "repo": _slug,
                              "items": [{**i, "section": [x for x in i["section"] if x][drop:]}
                                        for i in picked]}
comp = expanded
index = []
for slug, s in comp.items():
    repo = f"roeepe/uriel-audio-{s.get('repo', slug)}"
    split = parts_of([x for x in s["items"] if x.get("ready")])
    items, secs = [], []
    seq = 0
    for it in s["items"]:
        if not it.get("ready"):
            continue
        seq += 1
        tag = it.get("tag", "audio")
        sec = [x for x in it["section"] if x]
        part = ""
        if sec:
            part = (f"{sec[0]} · {sec[1]}" if split.get(sec[0]) and len(sec) > 1
                    else sec[0])
        if sec and (not secs or secs[-1] != sec):
            secs.append(sec)
        items.append({
            "n": seq,
            "title": f'{it.get("title_base", it.get("title", ""))} #{seq}',
            "desc": (it["description_html"]
                     + (f"<p>מתוך: {' · '.join(sec)}</p>" if sec else "")),
            "sec": sec,
            "part": part,
            "url": f"https://github.com/{repo}/releases/download/{tag}/{it['asset']}",
            "size": it["size"],
            "dur": hhmmss(it["duration"]),
            "secs": it["duration"],
            "guid": str(uuid.uuid5(NS, it["asset"])),
            "src": it.get("source", "structure"),
        })
    hours = round(sum(i["secs"] for i in items) / 3600)
    json.dump({"slug": slug, "name": s["name"], "count": len(items),
               "hours": hours, "links": LINKS.get(slug, {}), "items": items},
              open(f"{OUT}/{slug}.json", "w"), ensure_ascii=False)
    tops = []
    for i in items:
        if i["part"] and i["part"] not in tops: tops.append(i["part"])
    index.append({"slug": slug, "name": s["name"], "count": len(items),
                  "hours": hours, "parts": tops[:8], "links": LINKS.get(slug, {})})

# הכוזרי חי בכתובת משלו ומחובר לספוטיפיי, ולכן הפיד שלו לא מוגש מכאן.
# 🚨 אבל *עמוד* חייב להיות לו: בלעדיו הכרטיס בעמוד הבית מפנה ל-/s/kuzari,
#    הדף מבקש kuzari.json, מקבל 404 ונתקע על «…». זה מה שהרב בן ציון ראה
#    כש«ספר הכוזרי לא נפתח».
from datetime import datetime, timezone
kz = json.load(open(os.path.expanduser("~/podcasts/KuzariPod/episodes.json")))
MA = {"m1": "מאמר ראשון", "m2": "מאמר שני", "m3": "מאמר שלישי",
      "m4": "מאמר רביעי", "m5": "מאמר חמישי", "bonus": "שיעורים נוספים"}
now = datetime.now(timezone.utc)
live = [e for e in kz if datetime.fromisoformat(e["publish_at"]) <= now]
kz_items, seq = [], 0
for e in live:
    seq += 1
    part = "הקדמה" if e["n"] <= 8 else MA.get(e["maamar"], "")
    kz_items.append({
        "n": seq, "title": e["title"], "desc": e["description_html"],
        "sec": [part] if part else [], "part": part,
        "url": e["url"], "size": e["size"], "dur": e["duration"],
        "secs": (int(e["duration"][:2]) * 3600 + int(e["duration"][3:5]) * 60
                 + int(e["duration"][6:8])),
        "guid": e["guid"], "src": "kuzari",
    })
kz_hours = round(sum(i["secs"] for i in kz_items) / 3600)
waiting = len(kz) - len(live)
json.dump({"slug": "kuzari", "name": "ספר הכוזרי לרבינו יהודה הלוי",
           "count": len(kz_items), "hours": kz_hours,
           "external": True, "links": LINKS["kuzari"],
           "note": (f"עוד {waiting} שיעורים מתוזמנים ויעלו בהדרגה, שיעור בכל יום א׳-ה׳."
                    if waiting else ""),
           "items": kz_items},
          open(f"{OUT}/kuzari.json", "w"), ensure_ascii=False)

index.insert(0, {"slug": "kuzari", "name": "ספר הכוזרי לרבינו יהודה הלוי",
                 "count": len(kz_items), "hours": kz_hours, "external": True,
                 "parts": [p for p in ["הקדמה", *MA.values()]
                           if any(i["part"] == p for i in kz_items)],
                 "links": LINKS["kuzari"]})

json.dump(index, open(f"{OUT}/index.json", "w"), ensure_ascii=False)

# מפתח חיפוש רזה על פני כל הסדרות — נבנה מקובצי האתר, כדי שהכותרת והמספר
# שבחיפוש יהיו בדיוק אלה שבעמוד (אחרי הפיצול והמספור מחדש)
search = []
for x in index:
    if x.get("external"):
        continue
    dd = json.load(open(f"{OUT}/{x['slug']}.json"))
    for it in dd["items"]:
        search.append([x["slug"], it["n"], it["title"]])
for it in kz_items:
    search.append(["kuzari", it["n"], it["title"]])
json.dump(search, open(f"{OUT}/search.json", "w"), ensure_ascii=False)

tot = sum(x["count"] for x in index)
print(f"{len(index)} סדרות · {tot} שיעורים · {sum(x['hours'] for x in index)} שעות")
for x in index: print(f"   {x['slug']:11} {x['count']:5} שיעורים {x['hours']:5} שעות  {x['name'][:40]}")
print("search index:", os.path.getsize(f"{OUT}/search.json")//1024, "KB")
