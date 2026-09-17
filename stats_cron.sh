#!/bin/bash
# צילום יומי של מוני ההורדות, סינון סריקות, ורענון הנתונים באתר.
# 🚨 לא מדווח על הצלחה: צילום שהצליח אינו הישג. כישלון כן — הוא נשאר בלוח.
cd "$HOME/uriel-emuna" || exit 1

fail() {
  ~/personal-ops/whatsapp/notify.js pending add "$1" >/dev/null 2>&1
  exit 1
}

python3 stats_collect.py >> stats.log 2>&1 \
  || fail "איסוף נתוני ההאזנה לשיעורים נכשל היום. המספרים באתר יישארו על מה שהיה אתמול עד שאבדוק."

python3 stats_build.py >> stats.log 2>&1 \
  || fail "חישוב נתוני ההאזנה נכשל. דף הנתונים יציג את המספרים של אתמול."

python3 make_site_data.py >> stats.log 2>&1 \
  || fail "בניית נתוני האתר נכשלה ברענון היומי של ההאזנות."

# 🚨 השער שמונע מפרק שכבר יצא להיעלם או להתחלף. אם הוא נופל — לא פורסים.
if ! python3 published_guard.py >> stats.log 2>&1; then
  ~/personal-ops/whatsapp/notify.js pending add \
    "הרענון היומי זיהה שפרק שכבר יצא באחד הפודקאסטים נעלם או הוחלף. לא פרסתי כלום, וצריך שאבדוק." \
    >/dev/null 2>&1
  exit 1
fi

set -a; . "$HOME/personal-ops/vercel.env"; set +a
vercel deploy --prod --yes --token "$VERCEL_TOKEN" --cwd site >> stats.log 2>&1 \
  || fail "רענון נתוני ההאזנה נבנה אבל הפריסה לאתר נכשלה. הוא יעלה ברענון הבא."

echo "$(date '+%F %T') רענון הושלם" >> stats.log
