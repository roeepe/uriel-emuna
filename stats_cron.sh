#!/bin/bash
# צילום יומי של מוני ההורדות. ההפרש בין צילומים הוא ההאזנות של אותו יום.
# 🚨 לא מדווח על הצלחה: צילום שהצליח אינו הישג. כישלון כן — הוא נשאר בלוח.
cd "$HOME/uriel-emuna"
if ! python3 stats_collect.py >> stats.log 2>&1; then
  ~/personal-ops/whatsapp/notify.js pending add \
    "איסוף נתוני ההאזנה לשיעורים נכשל היום. המספרים באתר יישארו על מה שהיה אתמול עד שאבדוק." \
    >/dev/null 2>&1
fi
