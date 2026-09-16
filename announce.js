#!/usr/bin/env node
/**
 * מודיע בוואטסאפ על השיעורים שעלו היום — קבוצה לכל פודקאסט.
 *
 * 🚨 אין כאן מודל ואין AI. זה חישוב דטרמיניסטי: לוח הפרסום ידוע מראש
 *    (`pub` לכל שיעור), ולכן הסקריפט רק שואל "אילו שיעורים עברו את הזמן
 *    שלהם היום, ועל אילו עוד לא הודענו" — ושולח. אותו קלט תמיד ייתן אותו פלט.
 *
 * מריצים אותו מה-cron בערב. אם לא רץ יום אחד, הריצה הבאה תשלים את מה
 * שהוחמץ עד גיל `MAX_AGE_DAYS`, ולא תציף בכל ההיסטוריה.
 *
 * כתובת ההאזנה: אם לסדרה יש קישורי ספוטיפיי לכל פרק — הם קודמים. עד שיהיו,
 * מקשרים לעמוד השיעור באתר, שם אפשר גם להאזין וגם להוריד.
 */
const fs = require('fs');
const path = require('path');
const wa = require(path.join(process.env.HOME, 'personal-ops/whatsapp/lib.js'));

const BASE = path.join(process.env.HOME, 'uriel-emuna');
const DATA = path.join(BASE, 'site', 'public', 'data');
const SITE = 'https://uriel-emuna.vercel.app';
const STATE = path.join(BASE, 'data', 'announced.json');
const GROUPS = path.join(BASE, 'data', 'wa_groups.json');
const MAX_AGE_DAYS = 3;

const DRY = process.argv.includes('--dry');

function todayIL() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' });
}
function dayOf(iso) {
  return new Date(iso).toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' });
}

function load(f, d) {
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; }
}

(async () => {
  const groups = load(GROUPS, {});          // slug -> מפתח יעד ב-allowlist
  const done = load(STATE, {});             // slug -> [מספרי פרקים שכבר הוכרזו]
  const now = Date.now();
  const cutoff = now - MAX_AGE_DAYS * 86400000;
  let sent = 0, skipped = 0;

  for (const [slug, target] of Object.entries(groups)) {
    if (!target) { skipped++; continue; }    // קבוצה שעוד לא נפתחה
    const d = load(path.join(DATA, `${slug}.json`), null);
    if (!d) { console.error(`אין נתונים לסדרה ${slug}`); continue; }

    // 🚨 קבוצה שנפתחה עכשיו לא צריכה לקבל את כל מה שכבר עלה. בריצה
    //    הראשונה מסמנים את כל מה שכבר פורסם כ"הוכרז", וההודעות מתחילות
    //    מהשיעור הבא. בלי זה כל קבוצה חדשה הייתה נפתחת בהצפה.
    if (!done[slug]) {
      done[slug] = d.items.filter((i) => i.pub && new Date(i.pub).getTime() <= now)
                          .map((i) => i.n);
      console.log(`${slug}: קבוצה חדשה — ${done[slug].length} שיעורים שכבר עלו סומנו, ` +
                  `ההודעות יתחילו מהשיעור הבא`);
      if (!DRY) fs.writeFileSync(STATE, JSON.stringify(done));
      continue;
    }
    const already = new Set(done[slug]);
    const fresh = d.items.filter((i) => {
      if (!i.pub || already.has(i.n)) return false;
      const t = new Date(i.pub).getTime();
      return t <= now && t >= cutoff;
    });
    if (!fresh.length) continue;

    for (const i of fresh) {
      const link = i.spotify || `${SITE}/s/${slug}#ep${i.n}`;
      const where = i.spotify ? 'להאזנה בספוטיפיי' : 'להאזנה ולהורדה';
      const body =
        `*${d.name}*\n` +
        `עלה שיעור חדש: ${i.title}\n\n` +
        `${where}:\n${link}`;
      if (DRY) {
        console.log(`--- [${slug}] -> ${target}\n${body}\n`);
      } else {
        await wa.sendText(target, body);
      }
      already.add(i.n);
      sent++;
    }
    done[slug] = [...already].sort((a, b) => a - b).slice(-400);
  }

  if (!DRY) fs.writeFileSync(STATE, JSON.stringify(done));
  console.log(`נשלחו ${sent} הודעות · ${skipped} סדרות בלי קבוצה עדיין`);
})().catch((e) => { console.error('announce: ' + e.message); process.exit(1); });
