#!/bin/sh
# Govorci po stavkih za vse epizode (govorci_stavki.py --vse). Ob sesutju se
# čez 30 s znova zažene, narejene epizode preskoči. Na koncu izvoz prepisov
# in predogled s prepisi.
#
# Uporaba (ločeno od aplikacije Claude, glej CLAUDE.md):
#   sh skripte/govorci_noc.sh [meja_°C]

cd "$(dirname "$0")/.." || exit 1
MEJA=${1:-70}
PY="$HOME/.cache/bitni-prepisi/.venv/bin/python"
DNEVNIK=prepisi-preizkus/govorci.log

while true; do
    caffeinate -i "$PY" -u skripte/govorci_stavki.py --vse "$MEJA" 2>&1 | grep -v Warning >> "$DNEVNIK"
    tail -n 1 "$DNEVNIK" | grep -q "^KONEC" && break
    echo "--- ponovni zagon $(date '+%H:%M')" >> "$DNEVNIK"
    sleep 30
done
"$PY" skripte/prepisi.py --izvozi >> "$DNEVNIK" 2>&1
"$PY" skripte/zgradi_stran.py --prepisi --izhod prepisi-preizkus/splet >> "$DNEVNIK" 2>&1
"$PY" skripte/prepisi_popravki.py --preveri 17 54 100 150 205 >> "$DNEVNIK" 2>&1
echo "ZAKLJUCEK $(date '+%d. %m. %H:%M')" >> "$DNEVNIK"
