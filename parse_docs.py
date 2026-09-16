#!/usr/bin/env python3
"""קורא את מסמכי «תוכן השיעורים» של הרב.

התבנית קבועה בכל המסמכים: התאריך העברי והכותרת מודגשים, ואחריהם — לא מודגש —
המיקום המדויק בספר ואז «תקציר:» עם תקציר השיעור. ההדגשה היא המפריד היחיד
שמפריד בין הכותרת למיקום, ולכן אסור לאבד אותה בחילוץ.
"""
import zipfile, re, html, json, os

def paragraphs(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf8', 'ignore')
    for pm in re.finditer(r'<w:p[ >].*?</w:p>', xml, re.S):
        bold, plain = [], []
        for rm in re.finditer(r'<w:r[ >].*?</w:r>', pm.group(0), re.S):
            r = rm.group(0)
            txt = ''.join(html.unescape(t) for t in
                          re.findall(r'<w:t[^>]*>(.*?)</w:t>', r, re.S))
            if not txt: continue
            pr = re.search(r'<w:rPr>.*?</w:rPr>', r, re.S)
            is_b = bool(pr and re.search(r'<w:b/>|<w:b ', pr.group(0)))
            (bold if is_b and not plain else plain).append(txt)
        b, p = ''.join(bold).strip(), ''.join(plain).strip()
        if b or p: yield b, p

DATE = re.compile(r'^([֐-׿"\'׳״]{1,4}\s+[֐-׿"\'׳״]+\s+'
                  r'ה?ת[֐-׿"\'׳״]+)\s*[:\-–]\s*(.*)$')

def entries(path):
    out = []
    for b, p in paragraphs(path):
        if not p and len(b) < 120:            # כותרת מדור (שער / מאמר)
            if b: out.append({"kind": "section", "text": b})
            continue
        m = DATE.match(b)
        date, title = (m.group(1), m.group(2).strip()) if m else (None, b)
        loc, summary = p, ""
        mt = re.search(r'תקציר\s*:\s*', p)
        if mt:
            loc, summary = p[:mt.start()].strip(), p[mt.end():].strip()
        if not (title or summary): continue
        out.append({"kind": "lesson", "date": date, "title": title.strip(' .:-–'),
                    "loc": loc.strip(' .:-–'), "summary": summary})
    return out

if __name__ == "__main__":
    res = {}
    for root, _, fs in os.walk('docs'):
        for f in fs:
            if not f.lower().endswith('.docx'): continue
            rel = os.path.relpath(os.path.join(root, f), 'docs')
            if not re.match(r'^(10|[1-9])[^0-9]', rel): continue
            try: res[rel] = entries(os.path.join(root, f))
            except Exception as e: print("ERR", rel, e)
    json.dump(res, open('data/doc_entries.json', 'w'), ensure_ascii=False, indent=0)
    for k in sorted(res):
        les = [e for e in res[k] if e['kind'] == 'lesson']
        sec = [e for e in res[k] if e['kind'] == 'section']
        wd = sum(1 for e in les if e['date']); ws = sum(1 for e in les if e['summary'])
        print(f"{len(les):4} שיעורים ({wd} עם תאריך, {ws} עם תקציר) · {len(sec):3} כותרות | {k[:78]}")
