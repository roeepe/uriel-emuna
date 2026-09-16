// פיד RSS לכל סדרה. נקרא מקובץ הנתונים של אותה סדרה ומייצר XML בזמן הבקשה.
// הכוזרי אינו כאן בכוונה — הוא כבר מוגש מ-kuzari-pod.vercel.app, וספוטיפיי
// מפנה לשם. שכפול שלו היה יוצר תוכנית שנייה עם אותם פרקים.
const fs = require('fs');
const path = require('path');

const AUTHOR = 'הרב בן ציון אוריאל';
const EMAIL = 'roee.pearl@gmail.com';

const cdata = s => `<![CDATA[${String(s == null ? '' : s).replace(/]]>/g, ']]&gt;')}]]>`;
const attr = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

module.exports = (req, res) => {
  const slug = String((req.query && req.query.s) || '').replace(/[^a-z-]/g, '');
  const file = path.join(process.cwd(), 'public', 'data', `${slug}.json`);
  if (!slug || !fs.existsSync(file)) {
    res.status(404).send('לא נמצאה סדרה בשם הזה');
    return;
  }
  const d = JSON.parse(fs.readFileSync(file, 'utf8'));
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const base = `https://${host}`;
  const cover = `${base}/cover/${slug}.jpg`;

  // תאריך לכל פרק: סדרה שנלמדה לאורך שנים מוצגת בסדר הלימוד, ולכן הפרק
  // הראשון הוא הישן ביותר. נותנים לכל פרק יום משלו לאחור מהיום, כדי
  // שאפליקציות פודקאסט ישמרו על הסדר הנכון.
  const day = 86400000;
  const t0 = Date.UTC(2025, 0, 1);
  const items = d.items.map((e, idx) => `    <item>
      <title>${cdata(e.title)}</title>
      <description>${cdata(e.desc || e.title)}</description>
      <itunes:summary>${cdata(e.desc || e.title)}</itunes:summary>
      <guid isPermaLink="false">${attr(e.guid)}</guid>
      <link>${attr(base)}/s/${slug}#ep${e.n}</link>
      <pubDate>${new Date(t0 + idx * day).toUTCString()}</pubDate>
      <enclosure url="${attr(e.url)}" length="${e.size}" type="audio/mpeg"/>
      <itunes:duration>${e.dur}</itunes:duration>
      <itunes:episode>${e.n}</itunes:episode>
      <itunes:author>${cdata(AUTHOR)}</itunes:author>
      <itunes:image href="${attr(cover)}"/>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>`).join('\n');

  const desc = `סדרת שיעורים ב${d.name} מאת ${AUTHOR}. ` +
    `${d.count} שיעורים, ${d.hours} שעות לימוד, לאורך כל הספר.`;

  res.setHeader('Content-Type', 'application/rss+xml; charset=utf-8');
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=120');
  res.status(200).send(`<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>${cdata(d.name + ' — ' + AUTHOR)}</title>
    <description>${cdata(desc)}</description>
    <link>${attr(base)}/s/${slug}</link>
    <language>he</language>
    <copyright>${cdata(AUTHOR)}</copyright>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${attr(base)}/feed/${slug}.xml" rel="self" type="application/rss+xml"/>
    <image><url>${attr(cover)}</url><title>${cdata(d.name)}</title><link>${attr(base)}/s/${slug}</link></image>
    <itunes:author>${cdata(AUTHOR)}</itunes:author>
    <itunes:summary>${cdata(desc)}</itunes:summary>
    <itunes:image href="${attr(cover)}"/>
    <itunes:category text="Religion &amp; Spirituality"><itunes:category text="Judaism"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>serial</itunes:type>
    <itunes:owner><itunes:name>${cdata(AUTHOR)}</itunes:name><itunes:email>${EMAIL}</itunes:email></itunes:owner>
${items}
  </channel>
</rss>
`);
};
