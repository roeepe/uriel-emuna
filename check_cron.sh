#!/bin/bash
# בדיקה יומית שהאתר באמת עובד. 🚨 לא מדווח על הצלחה — רק על שבר.
cd "$HOME/uriel-emuna"
out=$(python3 check.py 2>&1)
if [ $? -ne 0 ]; then
  ~/personal-ops/whatsapp/notify.js pending add \
    "משהו באתר השיעורים לא עובד: $(echo "$out" | grep '✗' | head -3 | sed 's/^  ✗ //' | tr '\n' ';')" \
    >/dev/null 2>&1
fi
echo "$(date) $(echo "$out" | tail -1)" >> check.log

# 🚨 פרק שכבר יצא בפיד לא יוחלף בפרק אחר — ראה published_guard.py.
# הוספת שיעורים באמצע סדרה מזיזה את לוח הפרסום של כל מי שאחריהם.
if ! python3 published_guard.py >> check.log 2>&1; then
  ~/personal-ops/whatsapp/notify.js pending add \
    "פרק שכבר יצא באחד הפודקאסטים הוחלף בפרק אחר, וזה אומר שהוא נעלם למי שכבר מנוי. צריך שאבדוק לפני שיוצא פרק נוסף." \
    >/dev/null 2>&1
fi
