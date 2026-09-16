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
