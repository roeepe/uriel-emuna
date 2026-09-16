#!/usr/bin/env python3
"""כותב את קובצי הנתונים שהאתר והפידים קוראים."""
import json, os, re, uuid, glob
D = "data"; OUT = "site/public/data"
NS = uuid.UUID("7a3c9d20-0000-4000-8000-757269656c00")
LINKS = json.load(open(f"{D}/links.json"))

def hhmmss(s):
    s = int(s or 0); return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

comp = json.load(open(f"{D}/episodes_composed.json"))
index = []
for slug, s in comp.items():
    repo = f"roeepe/uriel-audio-{slug}"
    items, secs = [], []
    for it in s["items"]:
        if not it.get("ready"):
            continue
        tag = it.get("tag", "audio")
        sec = [x for x in it["section"] if x]
        if sec and (not secs or secs[-1] != sec):
            secs.append(sec)
        items.append({
            "n": it["n"],
            "title": it["title"],
            "desc": it["description_html"],
            "sec": sec,
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
    for sec in secs:
        if sec[0] not in tops: tops.append(sec[0])
    index.append({"slug": slug, "name": s["name"], "count": len(items),
                  "hours": hours, "parts": tops[:8], "links": LINKS.get(slug, {})})

# הכוזרי הוא סדרה עשירית — הוא כבר חי בכתובת משלו, ואנחנו רק מצביעים עליה
kz = json.load(open(os.path.expanduser("~/podcasts/KuzariPod/episodes.json")))
index.insert(0, {"slug": "kuzari", "name": "ספר הכוזרי לרבינו יהודה הלוי",
                 "count": len(kz), "hours": 0, "external": True,
                 "parts": ["הקדמה", "מאמר ראשון", "מאמר שני", "מאמר שלישי",
                           "מאמר רביעי", "מאמר חמישי"],
                 "links": LINKS["kuzari"]})
index[0]["hours"] = round(sum(
    int(e["duration"][:2]) * 3600 + int(e["duration"][3:5]) * 60 for e in kz) / 3600)

json.dump(index, open(f"{OUT}/index.json", "w"), ensure_ascii=False)

# מפתח חיפוש רזה על פני כל הסדרות
search = []
for slug, s in comp.items():
    for it in s["items"]:
        if it.get("ready"):
            search.append([slug, it["n"], it["title"]])
for e in kz:
    search.append(["kuzari", e["n"], e["title"]])
json.dump(search, open(f"{OUT}/search.json", "w"), ensure_ascii=False)

tot = sum(x["count"] for x in index)
print(f"{len(index)} סדרות · {tot} שיעורים · {sum(x['hours'] for x in index)} שעות")
for x in index: print(f"   {x['slug']:11} {x['count']:5} שיעורים {x['hours']:5} שעות  {x['name'][:40]}")
print("search index:", os.path.getsize(f"{OUT}/search.json")//1024, "KB")
