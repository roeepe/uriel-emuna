#!/usr/bin/env python3
"""מחבר לכל שיעור כותרת ותיאור, מהמקור שבאמת יודע עליו משהו.

סדר העדיפות זהה בכל הסדרות, ומה שמשתנה הוא רק מה קיים בפועל:

  1. נושא שכתוב בשם ההקלטה עצמה — זה מה שהרב כתב, ולכן הוא קודם לכל.
  2. מסמך «תוכן השיעורים» — כותרת, מיקום מדויק בספר ותקציר מלא.
  3. מבנה התיקיות + המיקום בספר — קיים תמיד, גם כשאין כלום אחר.

🚨 אף כותרת אינה מומצאת. כשאין נושא כתוב, הכותרת אומרת איפה בספר אנחנו —
   וזו אמירה נכונה, לא ניחוש של תוכן שלא האזנו לו.
"""
import json, os, re, glob

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "data")

# לאיזו סדרה יש מסמך תוכן, ואיך הוא מתיישר מול ההקלטות
DOCS = {
    "chovot": ["2'תורת חובות הלבבות' לרבנו בחיי/תוכן השיעורים בחובות בלבבות.docx"],
    "ikarim": ["8ספר העיקרים לר' יוסף אלבו/תוכן ההקלטות בספר העיקרים.docx"],
    "ramban": [
        "5כתבי הרמב''ן/1שער הגמול/תוכן השיעורים בשער הגמול.docx",
        "5כתבי הרמב''ן/2ספר הויכוח /נושאי השיעורים בספר הויכוח.docx",
        "5כתבי הרמב''ן/3ספר הגאולה/נושאי השיעורים בספר הגאולה.docx",
        "5כתבי הרמב''ן/4תורת ה' תמימה/תוכן השיעורים בדרשת תורת ה' תמימה.docx",
        "5כתבי הרמב''ן/5דרשת קהלת /נושאי השיעורים בדרשת הרמבן לקהלת.docx",
        "5כתבי הרמב''ן/6דרשה לראש השנה /נושאי השיעורים בדרשה לראש השנה.docx",
    ],
}

def words(s):
    return [w for w in re.split(r"[\s,;]+", s or "") if len(w) > 2 and re.search(r"[א-ת]", w)]

# מילים שפותחות ציון מקום בספר. אחריהן בא סימן — אות בודדת, גימטריה או מספר.
LOC_START = (r"(פרק|פרקים|סעיף|סעיפים|שער|מאמר|דרוש|דרושים|כלל|כללים|חלק|"
             r"לאו|לאוין|עשה|מצוה|מצוות|הלכה|הלכות|הקדמה|פתיחה|סימן|מעלה|מעלות)")

def _ref_tail(s):
    t = s.split()
    return bool(t) and bool(re.fullmatch(r"[א-ת]{1,3}[\"']?\d*", t[-1])
                            or re.fullmatch(r"[\d\-–]+", t[-1]))

def is_topic(s):
    """האם זה נושא שהרב כתב, או רק ציון מקום בספר?

    🚨 הגרסה הראשונה דרשה שלוש מילים עבריות, ולכן «האגרת לתלמיד», «מבוא
       ללימוד» ו«סיכום הדרוש» הודחו ל'מיקום' — והכותרת שלהם נבנתה משם
       התיקייה עם השם האמיתי נגרר אחריו. 97 שיעורים נפגעו ככה. הרב בן ציון
       הוא שתפס את זה ב«קלקל קצת את הכותרות».
    """
    if not s:
        return False
    # «פרק ט2, חתימת הפרק ומקומו» — מיקום, פסיק, ואז הנושא האמיתי
    if "," in s:
        tail = s.split(",", 1)[1].strip()
        if len(words(tail)) >= 2:
            return True
    if len(words(s)) >= 3:
        return True
    if re.search(r"\d", s):                       # «הקדמה1», «ב,כט21-12»
        return False
    if re.match(rf"^{LOC_START}\b", s) and _ref_tail(s):   # «פרק כד», «חלק א»
        return False
    return len(words(s)) >= 2                     # «מבוא ללימוד», «האגרת לתלמיד»

def location_of(it):
    """המיקום בספר כפי שהוא כתוב בשם ההקלטה, בלי שם הסדרה החוזר."""
    r = (it.get("rest") or "").strip()
    if r and not is_topic(r):
        return r
    p = (it.get("pre") or "").strip()
    if p and len(words(p)) >= 2 and not re.fullmatch(r"שיעור מס'?", p):
        return p
    return ""

def doc_entries(paths):
    all_docs = json.load(open(os.path.join(D, "doc_entries.json")))
    out = []
    for p in paths:
        for e in all_docs.get(p, []):
            out.append(e)
    return out

# 🚨 `פרקים?` פירושו «פרקי» ואז מ' אופציונלית — הוא לא תופס «פרק» בכלל,
#    ולכן ההתאמה החזירה 4 מתוך 157. הצורה הנכונה היא `פרק(?:ים)?`.
CHAP = re.compile(r"פרק(?:ים)?\s*([א-ת\"']{1,6}(?:\s*[-–]\s*[א-ת\"']{1,6})?)\s*(\d?)")

def chapter_key(text):
    """מפתח מדויק של מקום בספר: «מאמר ראשון, תחילת פרק יח» ו«פרק יח» -> אותו מפתח."""
    m = CHAP.search(text or "")
    if not m: return None
    # רק אותיות הפרק, בלי הספרה שמציינת חלק: «פרק ב1» ו«תחילת פרק ב» הם
    # אותו פרק, ושני חלקיו נצרכים לפי הסדר מתוך רשומות אותו פרק.
    ref = re.sub(r"[^א-ת-]", "", m.group(1))
    return ref or None


ORD = {"ראשון":1,"שני":2,"שלישי":3,"רביעי":4,"חמישי":5,"שישי":6,"שביעי":7,
       "שמיני":8,"תשיעי":9,"עשירי":10}
LET = {"א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,"י":10}

def maamar_num(text):
    """מספר המאמר, בין אם נכתב «מאמר ראשון» (במסמך) ובין «מאמר א» (בתיקייה)."""
    t = text or ""
    m = re.search(r"מאמר\s+([א-ת]+)", t)
    if not m: return None
    w = m.group(1)
    if w in ORD: return ORD[w]
    if w in LET: return LET[w]
    return None


def align_by_chapter(items, entries):
    """התאמה לפי הפרק שנקוב בשני הצדדים — בלי להסתמך על סדר כלל.

    כשגם שם ההקלטה וגם המסמך אומרים במפורש באיזה פרק מדובר, אין שום סיבה
    לנחש לפי מיקום ברשימה. זה גם מה שמאפשר להתאים כשבמסמך יש שיעורים
    שלא הוקלטו — הם פשוט לא ימצאו בן זוג, וזה בסדר.
    """
    def norm(s): return re.sub(r"[^א-ת]", "", s or "")
    rows = [e for e in entries
            if e["kind"] == "lesson" and (e.get("title") or e.get("summary"))]
    index = {}
    for e in rows:
        ck = chapter_key(e.get("loc", ""))
        if not ck: continue
        index.setdefault((maamar_num(e.get("loc", "")), ck), []).append(e)
    matched = 0
    for it in items:
        ck = chapter_key(it.get("rest", "")) or chapter_key(it.get("stem", ""))
        if not ck: continue
        mn = maamar_num(" ".join(it["section"]))
        cand = None
        for key in ((mn, ck), (None, ck)):
            if index.get(key):
                cand = index[key].pop(0); break
        if cand:
            it["doc"] = cand; matched += 1
    print(f"    הותאמו {matched} רשומות לפי הפרק בספר, מתוך {len(rows)}")
    return items


def align(items, entries):
    """מיישר רשומות מסמך מול הקלטות — לפי המקום בספר, לא לפי סדר עיוור.

    🚨 יישור לפי סדר בלבד מסוכן כאן: במסמך של חובות הלבבות יש 140 רשומות מול
       138 הקלטות, וכל שיעור שלא הוקלט מזיז את כל מה שאחריו ומדביק לשיעור אחד
       את התקציר של שיעור אחר. לכן קודם מזהים לאיזה שער/מאמר שייכת כל רשומה
       (הוא כתוב בשדה המיקום שלה), ורק בתוך אותו שער מיישרים לפי הסדר — כך
       שפער נשאר כלוא בתוך השער שבו הוא קרה.
    """
    def norm(s):
        return re.sub(r"[^א-ת]", "", s or "")

    # שמות המדורים כפי שהם מופיעים בתיקיות
    groups, order = {}, []
    for it in items:
        k = tuple(it["section"])
        if k not in groups: groups[k] = []; order.append(k)
        groups[k].append(it)
    folder_keys = [(k, norm(k[-1] if k else "")) for k in order]

    # רשומה ריקה במסמך אינה שיעור
    rows = [e for e in entries
            if e["kind"] == "lesson" and (e.get("title") or e.get("summary"))]

    # לאיזה מדור שייכת כל רשומה: לפי המיקום שכתוב בה, ואם אין — כמו קודמתה
    buckets, last = {}, None
    for e in rows:
        loc = norm(e.get("loc", ""))
        hit = None
        for k, fk in folder_keys:
            if fk and (fk in loc or loc.startswith(fk[:8]) and len(fk) > 7):
                hit = k; break
        if hit is None: hit = last
        if hit is None: hit = order[0]
        last = hit
        buckets.setdefault(hit, []).append(e)

    # 🚨 מתאימים מדור רק כששתי הספירות זהות בדיוק. אם יש 20 הקלטות מול 31
    #    רשומות, אין שום דרך לדעת אילו 20 מתוך ה-31 הן הנכונות — ויישור «כמה
    #    שאפשר» היה מדביק לשיעור אחד את התקציר של שיעור אחר. תיאור חסר הוא
    #    חיסרון; תיאור שגוי הוא שקר, וגרוע בהרבה.
    matched = skipped = 0
    for k in order:
        gs, bs = groups[k], buckets.get(k, [])
        if not bs: continue
        if len(gs) != len(bs):
            skipped += 1
            print(f"    ⚠ «{' / '.join(k)[:46]}»: {len(gs)} הקלטות מול {len(bs)} רשומות — "
                  f"לא מתאים, כדי לא לשייך תקציר שגוי")
            continue
        for it, e in zip(gs, bs):
            it["doc"] = e; matched += 1
    print(f"    הותאמו {matched} רשומות מסמך מתוך {len(rows)} · {skipped} מדורים דולגו")
    return items


def compose(slug, s):
    items = s["items"]
    if slug == "ikarim":
        align_by_chapter(items, doc_entries(DOCS[slug]))
    elif slug in DOCS:
        align(items, doc_entries(DOCS[slug]))

    for it in items:
        sec = [x for x in it["section"] if x]
        loc = location_of(it)
        doc = it.get("doc")
        rest = (it.get("rest") or "").strip()

        # ---- כותרת ----
        if is_topic(rest):
            title = rest
        elif doc and doc.get("title"):
            title = doc["title"]
        elif is_topic(it.get("pre") or ""):
            title = it["pre"]
        else:
            tail = sec[-1] if sec else s["name"]
            title = f"{tail} — {loc}" if loc else tail
        title = re.sub(r"\s+", " ", title).strip(" -–,.")

        # ---- תיאור ----
        para = []
        if doc and doc.get("loc"):
            para.append(doc["loc"].rstrip(". ") + ".")
        elif loc:
            para.append(loc.rstrip(". ") + ".")
        if doc and doc.get("summary"):
            para.append(doc["summary"])
        if sec:
            para.append("מתוך: " + " · ".join(sec))
        if doc and doc.get("date"):
            para.append(doc["date"])

        it["title"] = f"{title} #{it['n']}"
        it["description_html"] = "".join(f"<p>{p}</p>" for p in para)
        it["source"] = ("filename" if is_topic(rest) else
                        "doc" if doc and doc.get("title") else "structure")
    return items

def main():
    raw = json.load(open(os.path.join(D, "episodes_raw.json")))
    from collections import Counter
    for slug, s in raw.items():
        print(f"=== {slug} — {s['name']}")
        compose(slug, s)
        c = Counter(i["source"] for i in s["items"])
        print(f"    כותרות: משם ההקלטה {c['filename']} · ממסמך {c['doc']} · ממבנה {c['structure']}")
        for i in [s["items"][0], s["items"][len(s['items'])//2]]:
            print(f"    #{i['n']} [{i['source']}] {i['title'][:82]}")
            print(f"        {re.sub('<[^>]+>',' ',i['description_html'])[:130]}")
    json.dump(raw, open(os.path.join(D, "episodes_composed.json"), "w"), ensure_ascii=False)
    tot = sum(len(s["items"]) for s in raw.values())
    print(f"\nסך הכל {tot} שיעורים בתשע סדרות.")

if __name__ == "__main__":
    main()
