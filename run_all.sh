#!/bin/bash
# כל הסדרות, שתיים במקביל ובעדיפות נמוכה. המכונה מריצה גם את חדר הבקרה,
# ממשק קלוד והמאזין לוואטסאפ — עבודה כבדה כאן לא אמורה להאט אותם.
cd "$HOME/uriel-emuna"
export URIEL_ENC=2 URIEL_UP=3 URIEL_DL=5 URIEL_CHUNK=40
printf '%s\n' ikarim chovot ramban saadia haran or-hashem ramchal maharal rambam \
  | xargs -P 2 -I{} sh -c 'nice -n 15 ionice -c3 python3 pipeline.py {} > logs-{}.log 2>&1'
echo "=== ALL DONE $(date) ==="
