#!/usr/bin/env python3
"""כותב את קובצי הנתונים שהאתר והפידים קוראים."""
import json, os, re, uuid, glob
D = "data"; OUT = "site/public/data"
NS = uuid.UUID("7a3c9d20-0000-4000-8000-757269656c00")
LINKS = json.load(open(f"{D}/links.json"))

# ---------- תזמון הפרסום לפודקאסט ----------
# 🚨 האתר והפיד אינם אותו דבר: באתר *כל* השיעורים זמינים מיד להאזנה
#    ולהורדה, ובפיד הם נכנסים בהדרגה — שיעור בכל יום א׳-ה׳ ב-15:00, בלי
#    חגים. זה מה שמאפשר לפודקאסט להיראות חי לאורך זמן במקום להישפך בבת אחת.
from datetime import datetime, timedelta, timezone
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

# 🚨 מתחילים שבועיים אחורה, לא מחר: פיד שכל הפרקים בו עתידיים יוצא ריק,
#    וספוטיפיי לא מקבל פיד ריק. ככה כל סדרה נולדת עם כ-10 פרקים באוויר,
#    ומשם ממשיכה שיעור ביום.
START = datetime.now(IL).date() - timedelta(days=14)

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
    for it, when in zip(d["items"], schedule(len(d["items"]), START)):
        it["pub"] = when

for slug, cfg in DEFER.items():
    d = built.get(slug)
    if not d:
        continue
    base = built.get(cfg["after"])
    teaser = cfg["teaser"]
    for it, when in zip(d["items"][:teaser], schedule(teaser, START)):
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
# 🚨 חכם שכתב כמה חיבורים אינו סדרה אחת ארוכה. "כתבי רמח"ל" הוא אוסף שבתוכו
#    מאמר הויכוח, דעת תבונות, דרך ה' ומסילת ישרים — כמו בתיקייה המקורית של
#    הרב. ספר אחד שמחולק למאמרים (רס"ג, אור השם, מורה נבוכים) נשאר סדרה אחת.
#    הכללים ב-data/collections.json.
#
# 🚨 השכבה הזאת היא **תצוגה בלבד.** קובצי הסדרות ב-site/public/data/<slug>.json
#    לא נגעו — מהם נבנים הפידים, וספוטיפיי מושך מהם. פיצול שהיה נוגע בהם היה
#    משנה פידים שכבר פורסמו.
CFG = json.load(open(f"{D}/collections.json"))
LOOSE = "שיעורים נוספים"

flat = {x["slug"]: x for x in index}
works_out, col_index = {}, []


def works_of(slug):
    """חיבורים של סדרה, לפי המדור העליון — בסדר שבו הם מופיעים בפועל."""
    items = json.load(open(f"{OUT}/{slug}.json"))["items"]
    order, buckets = [], {}
    for it in items:
        k = (it.get("sec") or [LOOSE])[0]
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(it)
    # שיעור בודד בלי מדור הוא דרשת סיום או דברים במסיבת סיום — מקומו בסוף,
    # לא בראש האוסף לפני החיבור הראשון.
    order.sort(key=lambda k: k == LOOSE)
    return [(k, buckets[k]) for k in order]


for slug in CFG["order"]:
    src = flat.get(slug)
    if not src:
        continue
    col = CFG["collections"].get(slug)
    if not col:
        col_index.append({**src, "kind": "series"})
        continue

    works = []
    for wname, wit in works_of(slug):
        wslug = f"{slug}-{len(works) + 1}"
        hours = round(sum(i["secs"] for i in wit) / 3600)
        # 🚨 בתוך עמוד החיבור, רמת המדור הראשונה היא שם החיבור עצמו — היא
        #    כבר בכותרת. השארתה הייתה חוזרת בכל שורה ובכל תיאור.
        wit = [{**i, "sec": (i.get("sec") or [])[1:]} for i in wit]
        for i in wit:
            i["part"] = " · ".join(i["sec"][:2]) if i["sec"] else ""
            i["desc"] = re.sub(r"<p>מתוך: .*?</p>\s*$", "", i["desc"])
            if i["sec"]:
                i["desc"] += f"<p>מתוך: {' · '.join(i['sec'])}</p>"
        works.append({"slug": wslug, "name": CFG["names"].get(wname, wname),
                      "count": len(wit), "hours": hours, "of": slug})
        works_out[wslug] = {"slug": wslug, "name": CFG["names"].get(wname, wname),
                            "collection": col["name"], "col_slug": slug,
                            "cover": slug, "count": len(wit), "hours": hours,
                            "feed_of": slug, "links": LINKS.get(slug, {}),
                            "items": wit}
    for extra in col.get("also", []):
        e = flat.get(extra)
        if not e:
            continue
        works.append({"slug": extra, "name": e["name"], "count": e["count"],
                      "hours": e["hours"], "of": extra, "own": True})

    col_index.append({"slug": slug, "kind": "collection", "name": col["name"],
                      "count": sum(w["count"] for w in works),
                      "hours": sum(w["hours"] for w in works),
                      "works": works, "links": LINKS.get(slug, {})})

# סדרה שהוזכרה כ-"also" כבר יושבת בתוך אוסף — לא מוצגת שוב בשורש
inside = {x for c in CFG["collections"].values() for x in c.get("also", [])}
col_index = [c for c in col_index if c["slug"] not in inside]

for wslug, w in works_out.items():
    json.dump(w, open(f"{OUT}/w-{wslug}.json", "w"), ensure_ascii=False)
json.dump(col_index, open(f"{OUT}/index.json", "w"), ensure_ascii=False)

print(f"\nאוספים: {len([c for c in col_index if c['kind'] == 'collection'])} · "
      f"סדרות עצמאיות: {len([c for c in col_index if c['kind'] == 'series'])} · "
      f"חיבורים בתוך אוספים: {len(works_out)}")
for c in col_index:
    mark = "▸" if c["kind"] == "collection" else " "
    print(f" {mark} {c['name'][:42]:44} {c['count']:5}")
    for w in c.get("works", []):
        print(f"      └ {w['name'][:38]:40} {w['count']:5}"
              + ("  (סדרה עם פיד משלה)" if w.get("own") else ""))
