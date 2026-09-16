#!/bin/bash
# הודעה בערב על השיעורים שעלו היום, קבוצה לכל פודקאסט.
# 🚨 דטרמיניסטי לגמרי — אין כאן מודל. רץ רק אם הוגדרו קבוצות.
cd "$HOME/uriel-emuna"
if ! grep -q '": *"[^"]' data/wa_groups.json 2>/dev/null; then exit 0; fi
if ! node announce.js >> announce.log 2>&1; then
  ~/personal-ops/whatsapp/notify.js pending add \
    "ההודעות היומיות על השיעורים החדשים לא נשלחו הערב. צריך בדיקה." >/dev/null 2>&1
fi
