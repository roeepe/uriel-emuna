#!/usr/bin/env python3
"""כותב את קובצי הנתונים שהאתר והפידים קוראים."""
import json, os, re, uuid, glob
D = "data"; OUT = "site/public/data"
NS = uuid.UUID("7a3c9d20-0000-4000-8000-757269656c00")
LINKS = json.load(open(f"{D}/links.json"))
# הורדות אמיתיות לכל שיעור, אחרי סינון סריקות של פלטפורמות (stats_build.py)
_dlf = f"{D}/downloads.json"
DL = json.load(open(_dlf)) if os.path.exists(_dlf) else {}

# ---------- תזמון הפרסום לפודקאסט ----------
# 🚨 האתר והפיד אינם אותו דבר: באתר *כל* השיעורים זמינים מיד להאזנה
#    ולהורדה, ובפיד הם נכנסים בהדרגה — שיעור בכל יום א׳-ה׳ ב-15:00, בלי
#    חגים. זה מה שמאפשר לפודקאסט להיראות חי לאורך זמן במקום להישפך בבת אחת.
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")

def _skip_days():
    keep_modern = {"יוֹם הַשּׁוֹאָה", "יוֹם הַזִּכָּרוֹן", "יוֹם הָעַצְמָאוּת", "יוֹם יְרוּשָׁלַיִם"}
    keep_minor = {"שׁוּשָׁן פּוּרִים"}
    out = set()
    for y in range(2026, 2031):
        f = f"{D}/hebcal-{y}.json"
        if not os.path.exists(f): continue
        for it in json.load(open(f))["items"]:
            if it.get("category") != "holiday": continue
            sub, title = it.get("subcat"), it["title"]
            if sub == "major" or (sub == "modern" and title in keep_modern) \
               or (sub == "minor" and title in keep_minor):
                out.add(it["date"][:10])
    return out

SKIP = _skip_days()
# עד איזו שנה יש לנו לוח חגים. מעבר לזה הלוח "נקי" מדי והתזמון היה מפרסם
# שיעורים בחגים בלי שאיש ישים לב.
CAL_LAST = max(int(f[-9:-5]) for f in glob.glob(f"{D}/hebcal-*.json"))

def schedule(n, start):
    """n תאריכי פרסום, יום א׳-ה׳ בשעה 15:00, מדלג על חגים ומועדים."""
    out, d = [], start
    while len(out) < n:
        if d.weekday() in (6, 0, 1, 2, 3) and d.isoformat() not in SKIP:
            out.append(datetime(d.year, d.month, d.day, 15, 0, tzinfo=IL).isoformat())
        d += timedelta(days=1)
    if out and datetime.fromisoformat(out[-1]).year > CAL_LAST:
        raise SystemExit(
            f"התזמון חורג אל {datetime.fromisoformat(out[-1]).year}, "
            f"ולוח החגים מגיע רק עד {CAL_LAST}. להוריד עוד שנה מ-hebcal "
            f"לפני שממשיכים, אחרת יתפרסמו שיעורים בחגים.")
    return out

# 🚨 תאריך העוגן **קבוע**, ונקרא מקובץ. הוא היה מחושב כ"היום פחות 14 יום",
#    וזה אומר שכל בנייה מחדש הזיזה את הלוח כולו קדימה: בנייה בעוד שבוע
#    הייתה מחזירה כל פודקאסט מ-9 פרקים ל-4, כלומר **מוחקת פרקים שכבר הגיעו
#    למאזינים**. הבנייה כמעט ולא רצה, ולכן זה לא התפוצץ — עד שהוספנו
#    רענון יומי. מכאן ואילך הלוח מתקדם עם הזמן, לא זז איתו.
_sch = json.load(open(f"{D}/schedule.json"))
START = date.fromisoformat(_sch["start"])
# 🚨 הפרק הראשון יוצא לבדו, והשאר מחכים ל-START. פיד ריק לגמרי נדחה
#    בספוטיפיי, ולכן חייב להיות פרק אחד באוויר — אבל רק אחד.
FIRST = date.fromisoformat(_sch["first"])

def schedule_series(n):
    """פרק ראשון בתאריך הקבוע שלו, והשאר יום-יום מ-START."""
    head = datetime(FIRST.year, FIRST.month, FIRST.day, 15, 0, tzinfo=IL).isoformat()
    return [head] + (schedule(n - 1, START) if n > 1 else [])

# סדרה שממתינה לסדרה אחרת. שני הסבבים במורה הנבוכים הם אותו ספר, ואין טעם
# שיתפרסמו במקביל — הסבב השני מתחיל רק אחרי שהראשון הסתיים.
# `teaser` פרקים עולים מיד, רק כדי שהפיד לא ייצא ריק וספוטיפיי יקבל אותו.
DEFER = {"moreh-sheni": {"after": "moreh-rishon", "teaser": 1}}

HEB_MONTH = {1:"ינואר",2:"פברואר",3:"מרץ",4:"אפריל",5:"מאי",6:"יוני",7:"יולי",
             8:"אוגוסט",9:"ספטמבר",10:"אוקטובר",11:"נובמבר",12:"דצמבר"}

def heb_month_year(iso):
    d = datetime.fromisoformat(iso)
    return f"{HEB_MONTH[d.month]} {d.year}"

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

CFG = json.load(open(f"{D}/collections.json"))

# פיצול מפורש: מורה הנבוכים הוא ספר אחד שנלמד פעמיים, ולכן שני סבבים.
# הוא מזוהה לפי שתי רמות מדור ולא אחת, ולכן אינו נגזר אוטומטית.
EXPLICIT = {
    "rambam": [
        ("moreh-rishon", 'מורה הנבוכים — סבב לימוד ראשון, תש"פ-תשפ"א',
         lambda sec: _moreh(sec, "ראשון"), 2),
        ("moreh-sheni", 'מורה הנבוכים — סבב לימוד שני, תשפ"ב-תשפ"ג',
         lambda sec: _moreh(sec, "שני"), 2),
    ],
}
CLAIMED = {"rambam": lambda sec: bool(sec) and "מורה" in sec[0]}

comp = json.load(open(f"{D}/episodes_composed.json"))

# ---------- כל חיבור באוסף הוא פודקאסט בפני עצמו ----------
# 🚨 עד 17/9/2026 אוסף שלם היה פיד אחד, ולכן מסילת ישרים — החיבור הרביעי
#    בכתבי רמח"ל — הייתה מתחילה להישמע רק במרץ 2028, אחרי 352 שיעורים
#    אחרים. כל חיבור מתפרסם עכשיו במקביל ומתחיל מיד.
#
# 🚨 החיבור הראשון בכל אוסף **שומר על ה-slug המקורי**, ולכן הפיד שספוטיפיי
#    כבר מושך ממנו ממשיך לחיות ורק מצטמצם לחיבור אחד. הפרקים שכבר יצאו בכל
#    אוסף שייכים כולם לחיבור הראשון — נבדק לפני הפיצול. slug חדש היה יוצר
#    תוכנית חדשה ומוחק למאזינים את מה שכבר קיבלו.

def _works_of(slug):
    """שמות החיבורים של אוסף, לפי המדור העליון, בסדר הופעתם בפועל."""
    claimed = CLAIMED.get(slug, lambda sec: False)
    out = []
    for it in comp[slug]["items"]:
        if not it.get("ready"):
            continue
        sec = [x for x in it["section"] if x]
        if claimed(sec):
            continue
        if sec and sec[0] not in out:
            out.append(sec[0])
    return out


SPLITS = {}
for _c in CFG["collections"]:
    if _c not in comp:
        continue
    _parts = []
    for _i, _name in enumerate(_works_of(_c)):
        _disp = CFG["names"].get(_name, _name)
        if _i == 0:
            # 🚨 שיעור בלי מדור (דרשת סיום) נשאר בחיבור הראשון. ברמב"ן הוא
            #    פרק 1 בפיד והוא כבר יצא — הוצאה שלו הייתה מוחקת אותו אצל
            #    מי שכבר קיבל.
            _parts.append((_c, _disp, (lambda sec, n=_name: not sec or sec[0] == n), 1))
        else:
            _parts.append((f"{_c}-{_i + 1}", _disp,
                           (lambda sec, n=_name: bool(sec) and sec[0] == n), 1))
    SPLITS[_c] = _parts + EXPLICIT.get(_c, [])
# הסדרה שפוצלה יורדת מהרשימה, ובמקומה נכנסים החלקים שלה
expanded = {}
for _slug, _s in comp.items():
    if _slug not in SPLITS:
        expanded[_slug] = _s
        continue
    for out_slug, out_name, pred, drop in SPLITS[_slug]:
        picked = [i for i in _s["items"] if pred([x for x in i["section"] if x])]
        # כשכל הפודקאסט הוא «מורה הנבוכים, סבב X», אין טעם לחזור על זה
        # בכל שורה — מורידים את שתי הרמות שהפכו לשם הפודקאסט עצמו
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
built = {}
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
            "dl": DL.get(it["asset"], 0),
            "src": it.get("source", "structure"),
        })
    hours = round(sum(i["secs"] for i in items) / 3600)
    built[slug] = {"slug": slug, "name": s["name"], "count": len(items),
                   "hours": hours, "links": LINKS.get(slug, {}), "items": items}
    tops = []
    for i in items:
        if i["part"] and i["part"] not in tops: tops.append(i["part"])
    index.append({"slug": slug, "name": s["name"], "count": len(items),
                  "hours": hours, "parts": tops[:8], "links": LINKS.get(slug, {})})

for slug, d in built.items():
    if slug in DEFER:
        continue
    for it, when in zip(d["items"], schedule_series(len(d["items"]))):
        it["pub"] = when

for slug, cfg in DEFER.items():
    d = built.get(slug)
    if not d:
        continue
    base = built.get(cfg["after"])
    teaser = cfg["teaser"]
    for it, when in zip(d["items"][:teaser], schedule_series(teaser)):
        it["pub"] = when
    # הסבב מתחיל ביום שאחרי הפרק האחרון של הסדרה שלפניו
    after_last = datetime.fromisoformat(max(i["pub"] for i in base["items"])).date()
    rest = d["items"][teaser:]
    for it, when in zip(rest, schedule(len(rest), after_last + timedelta(days=1))):
        it["pub"] = when
    d["startsAt"] = rest[0]["pub"] if rest else None
    when_txt = heb_month_year(d["startsAt"]) if d.get("startsAt") else ""
    d["waitingDesc"] = (
        f"הסבב השני של מורה הנבוכים יתחיל לעלות כאן ב{when_txt}, "
        f"אחרי שיסתיים הסבב הראשון. בינתיים עולה שיעור הפתיחה בלבד — "
        f"וכל {d['count']} השיעורים כבר זמינים להאזנה ולהורדה באתר.")
    d["note"] = (f"בפודקאסט הסדרה תתחיל לעלות ב{when_txt}, אחרי שיסתיים הסבב "
                 f"הראשון. באתר כל השיעורים זמינים כבר עכשיו.")

for slug, d in built.items():
    json.dump(d, open(f"{OUT}/{slug}.json", "w"), ensure_ascii=False)

# הכוזרי חי בכתובת משלו ומחובר לספוטיפיי, ולכן הפיד שלו לא מוגש מכאן.
# 🚨 אבל *עמוד* חייב להיות לו: בלעדיו הכרטיס בעמוד הבית מפנה ל-/s/kuzari,
#    הדף מבקש kuzari.json, מקבל 404 ונתקע על «…». זה מה שהרב בן ציון ראה
#    כש«ספר הכוזרי לא נפתח».
from datetime import datetime, timezone
kz = json.load(open(os.path.expanduser("~/podcasts/KuzariPod/episodes.json")))
MA = {"m1": "מאמר ראשון", "m2": "מאמר שני", "m3": "מאמר שלישי",
      "m4": "מאמר רביעי", "m5": "מאמר חמישי", "bonus": "שיעורים נוספים"}
now = datetime.now(timezone.utc)
live = kz          # באתר מציגים את כולם; הפיד של הכוזרי מסנן בעצמו
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
        "guid": e["guid"], "src": "kuzari", "pub": e["publish_at"],
    })
kz_hours = round(sum(i["secs"] for i in kz_items) / 3600)
waiting = sum(1 for e in kz if datetime.fromisoformat(e["publish_at"]) > now)
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

# ---------- אוספי סדרות ----------
# כל חיבור הוא כבר סדרה מלאה עם פיד משלה (ראה SPLITS למעלה). כאן רק מקבצים
# אותם לתצוגה: דף הבית מראה אוסף אחד במקום חמישה חיבורים מפוזרים.
flat = {x["slug"]: x for x in index}
col_index = []
for slug in CFG["order"]:
    if slug in CFG["collections"] and slug in SPLITS:
        works = [flat[w] for w, *_ in SPLITS[slug] if w in flat]
        col_index.append({
            "slug": slug, "kind": "collection",
            "name": CFG["collections"][slug]["name"],
            "count": sum(w["count"] for w in works),
            "hours": sum(w["hours"] for w in works),
            "works": [{"slug": w["slug"], "name": w["name"], "count": w["count"],
                       "hours": w["hours"], "links": LINKS.get(w["slug"], {})}
                      for w in works],
            "links": LINKS.get(slug, {}),
        })
    elif slug in flat:
        col_index.append({**flat[slug], "kind": "series"})

# בעמוד של חיבור צריך להיות קישור חזרה לאוסף שלו
for c in col_index:
    for w in c.get("works", []):
        d = json.load(open(f"{OUT}/{w['slug']}.json"))
        d["collection"], d["col_slug"] = c["name"], c["slug"]
        json.dump(d, open(f"{OUT}/{w['slug']}.json", "w"), ensure_ascii=False)

json.dump(col_index, open(f"{OUT}/index.json", "w"), ensure_ascii=False)

ncol = len([c for c in col_index if c["kind"] == "collection"])
print(f"\nאוספים: {ncol} · סדרות עצמאיות: {len(col_index) - ncol} · "
      f"פידים בסך הכל: {len(index)}")
for c in col_index:
    mark = "▸" if c["kind"] == "collection" else " "
    print(f" {mark} {c['name'][:44]:46} {c['count']:5}")
    for w in c.get("works", []):
        print(f"      └ {w['slug']:16} {w['name'][:34]:36} {w['count']:5}")


# ---------- נתונים לדף הפרטי ----------
# 🚨 המספר נקרא "הורדות" ולא "האזנות" בכוונה. אפליקציית פודקאסט שמורידה
#    מראש נספרת גם אם איש לא לחץ נגן, ולכן "האזנות" היה מספר מנופח.
_hist = json.load(open(f"{D}/stats_history.json"))["snapshots"]
_log = json.load(open(f"{D}/sweeps.json")) if os.path.exists(f"{D}/sweeps.json") else []
rows = []
for c in col_index:
    for w in (c.get("works") or [c]):
        if w.get("external"):
            continue
        try:
            d = json.load(open(f"{OUT}/{w['slug']}.json"))
        except FileNotFoundError:
            continue
        live = [i for i in d["items"]
                if i.get("pub") and datetime.fromisoformat(i["pub"]) <= datetime.now(IL)]
        # 🚨 נספרות רק הורדות של פרקים **שכבר יצאו בפיד**. פרק שלא יצא אינו
        #    נגיש לאיש דרך אפליקציית פודקאסט, ולכן הורדה שלו היא בהכרח
        #    מכונה. ב-17/9/2026: 260 מתוך 321 ההורדות ישבו על פרקים שמעולם
        #    לא פורסמו — כלומר המספר "האמיתי" היה עדיין כמעט כולו רעש.
        live_ids = {i["n"] for i in live}
        rows.append({
            "slug": w["slug"], "name": w["name"],
            "collection": c["name"] if c["kind"] == "collection" else None,
            "episodes": w["count"], "published": len(live),
            "downloads": sum(i.get("dl", 0) for i in d["items"] if i["n"] in live_ids),
            "noise": sum(i.get("dl", 0) for i in d["items"] if i["n"] not in live_ids),
            "top": sorted(({"n": i["n"], "title": i["title"], "dl": i.get("dl", 0)}
                           for i in live), key=lambda x: -x["dl"])[:3],
        })
rows.sort(key=lambda r: -r["downloads"])
json.dump({
    "updated": datetime.now(IL).isoformat(timespec="minutes"),
    "since": _hist[0]["at"][:10],
    "raw": sum(_hist[-1]["series"][s_][k] - _hist[0]["series"].get(s_, {}).get(k, 0)
               for s_ in _hist[-1]["series"] for k in _hist[-1]["series"][s_]),
    "filtered": sum(x["removed"] for x in _log),
    "sweeps": _log[-12:],
    "downloads": sum(r["downloads"] for r in rows),
    "noise": sum(r["noise"] for r in rows),
    "episodes": sum(r["episodes"] for r in rows),
    "published": sum(r["published"] for r in rows),
    "series": rows,
}, open(f"{OUT}/{json.load(open(f'{D}/stats_path.json'))['path']}.json", "w"), ensure_ascii=False)
print(f"\nנתוני הורדות: {sum(r['downloads'] for r in rows):,} אמיתיות")

# ---------- גוגל: מפת אתר ו-robots ----------
# 🚨 נבנים מהאינדקס, לא ביד: עמוד של חיבור חדש נכנס לגוגל בלי שאיש יזכור.
#    הדפים הפרטיים (טיוטת הכתבה, חומר לעיתונות, דף הנתונים) אינם כאן
#    ומסומנים noindex בקוד שלהם.
SITE = "https://uriel-emuna.vercel.app"
_today = datetime.now(IL).date().isoformat()
_urls = [(SITE + "/", "1.0")]
for c in col_index:
    if c["kind"] == "collection":
        _urls.append((f"{SITE}/c/{c['slug']}", "0.9"))
    for w in (c.get("works") or [c]):
        if not w.get("external"):
            _urls.append((f"{SITE}/s/{w['slug']}", "0.8"))
open("site/public/sitemap.xml", "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{_today}</lastmod>"
              f"<priority>{p}</priority></url>\n" for u, p in _urls)
    + "</urlset>\n")
open("site/public/robots.txt", "w").write(
    "User-agent: *\nAllow: /\n"
    "Disallow: /press\nDisallow: /press-kit\nDisallow: /data/\n"
    f"Sitemap: {SITE}/sitemap.xml\n")
print(f"מפת אתר: {len(_urls)} כתובות")
