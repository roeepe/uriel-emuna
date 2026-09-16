#!/bin/bash
# עצירה נקייה של צינור השמע.
#
# 🚨 אסור להעביר את התבנית בשורת הפקודה של הקורא: `pgrep -f` תופס גם את התהליך
#    ששואל, וכך כבר הרגנו פעמיים את ה-shell של עצמנו. הפתרון הוא שהתבנית תחיה
#    רק בתוך הקובץ הזה, ושהזיהוי ייעשה לפי שם התוכנית ואז סינון על הארגומנטים,
#    תוך דילוג מפורש על עצמנו ועל ההורים שלנו.
SELF=$$
SKIP=" $SELF $PPID "
p=$PPID
for _ in 1 2 3 4; do p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' '); [ -n "$p" ] || break; SKIP="$SKIP$p "; done

kill_matching() {
  local prog="$1" pat="$2" pid
  pgrep -x "$prog" -a 2>/dev/null | grep -E "$pat" | awk '{print $1}' | while read -r pid; do
    case "$SKIP" in *" $pid "*) continue;; esac
    kill "$pid" 2>/dev/null
  done
}

kill_matching bash  'uriel-emuna/run_all'
kill_matching xargs 'pipeline'
kill_matching sh    'pipeline'
kill_matching python3 'pipeline'
sleep 3
pkill -x ffmpeg 2>/dev/null
pkill -x rclone 2>/dev/null
sleep 2
echo "python3: $(pgrep -x python3 -a 2>/dev/null | grep -c pipeline)"
echo "ffmpeg : $(pgrep -xc ffmpeg 2>/dev/null || echo 0)"
echo "rclone : $(pgrep -xc rclone 2>/dev/null || echo 0)"
