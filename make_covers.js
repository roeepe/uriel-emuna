const { chromium } = require('/srv/graphic-dev/node_modules/.pnpm/playwright@1.49.1/node_modules/playwright');
const fs = require('fs');
const index = JSON.parse(fs.readFileSync('site/public/data/index.json', 'utf8'));

const tpl = (name, sub) => `<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;box-sizing:border-box}
body{width:1500px;height:1500px;display:flex;align-items:center;justify-content:center;
  font-family:"Noto Sans Hebrew",sans-serif;background:#F1EADC;
  background-image:radial-gradient(circle at 30% 20%, #FFFDF8 0%, #F1EADC 55%, #E4D9C0 100%);}
.frame{width:1320px;height:1320px;border:3px solid #C3B08A;border-radius:40px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:90px;text-align:center;position:relative;background:rgba(255,253,248,.55)}
.frame::before,.frame::after{content:"";position:absolute;inset-inline:120px;height:2px;background:#C3B08A}
.frame::before{top:64px}.frame::after{bottom:64px}
.kicker{font-size:40px;font-weight:600;letter-spacing:.22em;color:#8A6D3B;margin-bottom:54px}
h1{font-size:${name.length > 22 ? 96 : name.length > 14 ? 116 : 136}px;font-weight:700;
  line-height:1.18;color:#241F17;letter-spacing:-.02em;max-width:1050px}
.rule{width:170px;height:5px;background:#8A6D3B;border-radius:3px;margin:58px 0}
.by{font-size:52px;font-weight:600;color:#5A5143}
</style></head><body>
<div class="frame">
  <div class="kicker">שיעורי אמונה</div>
  <h1>${name}</h1>
  <div class="rule"></div>
  <div class="by">${sub}</div>
</div></body></html>`;

(async () => {
  const b = await chromium.launch({ args: ['--no-sandbox'] });
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1500 }, locale: 'he-IL' });
  const p = await ctx.newPage();
  for (const s of index) {
    if (s.slug === 'kuzari') continue;
    const name = s.name.replace(/^(כתבי|תורת)\s+/, m => m).trim();
    await p.setContent(tpl(name, 'הרב בן ציון אוריאל'), { waitUntil: 'networkidle' });
    await p.waitForTimeout(700);
    await p.screenshot({ path: `site/public/cover/${s.slug}.png` });
    console.log('cover:', s.slug, '|', name);
  }
  await b.close();
})();
