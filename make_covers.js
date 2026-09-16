// מייצר עטיפה לכל סדרה מתוך עטיפת הכוזרי המקורית.
//
// לא מציירים עטיפה חדשה: לוקחים את התמונה כמו שהיא, מכסים *רק* את שורת
// הכותרת בטלאי שנחתך מרצועת הקלף הנקייה שמעליה, וכותבים שם את המשפט של
// הסדרה. התצלום, מרקם הקלף והשורה «עם הרב בן ציון אוריאל» נשארים מקוריים
// פיקסל-בפיקסל, ולכן כל עשר העטיפות נראות כמו משפחה אחת.
//
// הגבולות נמדדו מהתמונה עצמה (כהות לפי שורה), לא בעין:
//   2631-2710  רצועת קלף נקייה  <- ממנה נחתך הטלאי
//   2711-2833  שורת הכותרת      <- זה מה שמוחלף
//   2854-      «עם הרב בן ציון אוריאל»
//
// 🚨 המדידה הראשונה נתנה 2727 כתחילת הכותרת, כי היא ספרה שורה כ"טקסט" רק
//    מ-60 פיקסלים כהים ומעלה — וראש הלמ"ד הוא קו דק שלא עבר את הסף. ארבעת
//    הפיקסלים שנשארו חשופים נראו כמו שריטה ליד הכותרת החדשה.
const { chromium } = require('/srv/graphic-dev/node_modules/.pnpm/playwright@1.49.1/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const SIZE = 3000;
const TITLE_TOP = 2711, TITLE_BOT = 2833;
const PATCH_TOP = 2633, PATCH_H = 76;
const COVER_TOP = TITLE_TOP - 6, COVER_BOT = TITLE_BOT + 8;

const titles = JSON.parse(fs.readFileSync('data/cover_titles.json', 'utf8'));
const b64 = f => fs.readFileSync(f).toString('base64');
const BASE = 'data:image/jpeg;base64,' + b64('base.jpg');
const PATCH = 'data:image/png;base64,' + b64('insp/patch.png');

const page = (text) => `<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@700;800;900&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:${SIZE}px;height:${SIZE}px;overflow:hidden}
  .base{position:absolute;inset:0;width:${SIZE}px;height:${SIZE}px}
  /* הטלאי: אותה רצועת קלף, נמתחת אנכית בלבד כדי לשמור על כיוון הסיבים */
  .patch{position:absolute;left:0;top:${COVER_TOP}px;width:${SIZE}px;
         height:${COVER_BOT - COVER_TOP}px;
         background-image:url('${PATCH}');
         background-size:${SIZE}px ${PATCH_H}px;
         background-repeat:repeat-y}
  .title{position:absolute;left:0;top:${COVER_TOP}px;width:${SIZE}px;
         height:${COVER_BOT - COVER_TOP}px;
         display:flex;align-items:center;justify-content:center;
         font-family:'Heebo',sans-serif;font-weight:800;color:#1E1A15;
         letter-spacing:-0.005em;white-space:nowrap;line-height:1}
</style></head><body>
  <img class="base" src="${BASE}">
  <div class="patch"></div>
  <div class="title"><span id="t">${text}</span></div>
</body></html>`;

(async () => {
  const b = await chromium.launch({ args: ['--no-sandbox'] });
  const ctx = await b.newContext({ viewport: { width: SIZE, height: SIZE }, locale: 'he-IL' });
  const p = await ctx.newPage();
  fs.mkdirSync('covers', { recursive: true });

  for (const [slug, text] of Object.entries(titles)) {
    await p.setContent(page(text), { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    // גודל אחיד לכל המשפחה, ומתכווץ רק אם המשפט באמת ארוך מדי
    // 🚨 למדוד את הטקסט, לא את המיכל: המיכל הוא flex ברוחב 3000, ולכן
    //    scrollWidth שלו תמיד 3000 והכותרת הצטמצמה למינימום בכל הסדרות.
    const size = await p.evaluate((maxW) => {
      const el = document.getElementById('t');
      const box = el.parentElement;
      let fs = 150;
      box.style.fontSize = fs + 'px';
      while (el.getBoundingClientRect().width > maxW && fs > 100) {
        fs -= 2; box.style.fontSize = fs + 'px';
      }
      return fs;
    }, 2280);
    await p.waitForTimeout(250);
    await p.screenshot({ path: `covers/${slug}.png` });
    console.log(`${slug.padEnd(11)} ${String(size).padStart(3)}px  ${text}`);
  }
  await b.close();
})();
