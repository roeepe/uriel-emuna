#!/usr/bin/env python3
"""בונה את רשימת הפרקים לכל סדרה.

המידע על כל שיעור יושב במקום אחר בכל סדרה, ולכן לכל סדרה כלל משלה:

  * שם ההקלטה נושא את הנושא  — מהר"ל, רמח"ל, רמב"ן, וחלק מהרמב"ם
  * מסמך «תוכן השיעורים»     — חובות הלבבות, ספר העיקרים, רמב"ן
  * רק המיקום בספר           — רס"ג, דרשות הר"ן, אור השם

מה שמשותף לכולן הוא שֵם התיקייה: הרב סידר את ההקלטות לפי מבנה הספר, ולכן
מסלול התיקיות הוא כותרת המדור — וזה נכון גם כשאין שום מידע אחר.
"""
import json, os, re, unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "data")

AUD = (".mp3", ".m4a", ".wav", ".3gp")


def clean(s):
    """שם תיקייה/קובץ כפי שהוא אמור להיקרא: בלי מספר סידורי בתחילתו,
    ובלי הגרש הכפול שהדרייב שם במקום גרשיים."""
    s = s.replace("''", '"').replace("``", '"')
    s = re.sub(r"^\s*\d+\s*[-–.]?\s*(?=[א-ת\"'(])", "", s)   # «1מאמר ראשון», «0 מבוא» -> בלי המספר
    return re.sub(r"\s+", " ", s).strip(" -–,.")


def sort_key(name):
    """תיקיות ממוספרות נשמרות בסדר שלהן, לא בסדר אלפביתי."""
    m = re.match(r"^\s*(\d+)", name)
    return (0, int(m.group(1)), name) if m else (1, 0, name)


NUM = re.compile(r"(\d+)")

def parse_stem(stem):
    """מפרק שם הקלטה לשלושה חלקים: מה שלפני המספר, המספר, ומה שאחריו.

    🚨 חייבים לשמור גם את מה שלפני המספר. ב«דרשות הר"ן - דרוש ו5» כל המידע
       יושב דווקא שם, ואם זורקים אותו נשאר שם ריק. ב«תפארת42 - פרק ט2, ...»
       להפך: הקידומת היא רק שם הספר, והנושא הוא מה שאחרי.
    """
    s = stem.replace("''", '"')
    m = re.search(r"(\d{1,4})(?![\d])", s)
    if not m:
        return s.strip(" -–,.;:"), None, ""
    pre = s[:m.start()].strip(" -–,.;:")
    num = int(m.group(1))
    rest = s[m.end():].strip(" -–,.;:")
    return re.sub(r"\s+", " ", pre), num, re.sub(r"\s+", " ", rest)


def hebrew_words(s):
    return [w for w in re.split(r"[\s,;]+", s) if len(w) > 2 and re.search(r"[א-ת]", w)]


MAIN_ROOT = "1CRxSrjs0ec_fTHfhlyNvUZZgVexI0Tgr"

def load_rows():
    """כל ההקלטות, מהמניפסט.

    🚨 לא מ-tree.json: שיעורי הרמח"ל הנוספים יושבים בתיקיית דרייב אחרת לגמרי,
       ולכן הם פשוט לא היו שם. במניפסט יש לכל שורה גם `root`, ולפיו יודעים אם
       הנתיב מתחיל בשם הסדרה (התיקייה הראשית) או ישר בחלק שלה (התיקייה השנייה).
    """
    rows = []
    for r in json.load(open(os.path.join(D, "manifest.json"))):
        parts = r["path"].split("/")
        folders = parts[1:-1] if r.get("root", MAIN_ROOT) == MAIN_ROOT else parts[:-1]
        rows.append((r["series"], r["path"], folders, parts[-1], r))
    return rows


def main():
    series = json.load(open(os.path.join(D, "series.json")))
    manifest = {r["path"]: r for r in json.load(open(os.path.join(D, "manifest.json")))}
    # קובץ שאינו שמע (ראה data/not_audio.json) אינו שיעור — יורד כאן, כדי
    # שלא ייספר בכותרות ובמספור הרץ של הסדרה.
    _na = os.path.join(D, "not_audio.json")
    skip = set(json.load(open(_na))["paths"]) if os.path.exists(_na) else set()
    meta = {}
    import glob
    for f in glob.glob(os.path.join(D, "audio_meta_*.json")):
        try: meta.update(json.load(open(f)))
        except Exception: pass

    out = {}
    for snum, info in series.items():
        slug = info["slug"]
        rows = [r for r in load_rows() if r[0] == int(snum)]
        items = []
        for _, path, folders, fname, _row in rows:
            if path in skip:
                continue
            stem = re.sub(r"\.(mp3|m4a|wav|3gp)$", "", fname, flags=re.I)
            pre, num, rest = parse_stem(stem)
            items.append({
                "path": path,
                "folders": folders,
                "section": [clean(f) for f in folders],
                "pre": pre,
                "num": num,
                "rest": rest,
                "stem": stem,
            })
        items.sort(key=lambda it: (
            [sort_key(f) for f in it["folders"]],
            it["num"] if it["num"] is not None else 10 ** 6,
            it["stem"],
        ))
        for i, it in enumerate(items, 1):
            it["n"] = i
            a = manifest.get(it["path"])
            it["asset"] = a["asset"] if a else None
            it["ready"] = bool(a and a["asset"] in meta)
            if it["ready"]:
                m = meta[a["asset"]]
                it["size"], it["duration"], it["tag"] = m["size"], m["duration"], m.get("tag", "audio")
        out[slug] = {"name": info["name"], "series": int(snum), "items": items}

    json.dump(out, open(os.path.join(D, "episodes_raw.json"), "w"), ensure_ascii=False)
    for slug, s in out.items():
        rich = sum(1 for i in s["items"] if len(hebrew_words(i["rest"])) >= 3)
        ready = sum(1 for i in s["items"] if i["ready"])
        depth = max(len(i["section"]) for i in s["items"])
        print(f"{slug:11} {len(s['items']):5} שיעורים · {ready:5} עם שמע · "
              f"{rich:5} שם עשיר · עומק {depth}")
        for i in s["items"][:2]:
            print(f"      #{i['n']:<4} {' / '.join(i['section'])[:60]:60} | {i['rest'][:45]}")


if __name__ == "__main__":
    main()
