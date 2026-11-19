#!/bin/sh
# Nočni prepis vseh epizod. Če se proces sesuje, ga čez 30 s znova zažene;
# narejene epizode preskoči. Konča se, ko so vse epizode prepisane.
#
# Uporaba: sh skripte/prepisi_noc.sh [meja_°C] [prednostne oznake ...]
# Primer:  nohup sh skripte/prepisi_noc.sh 70 54 119 &

cd "$(dirname "$0")/.." || exit 1
MEJA=${1:-70}
[ $# -gt 0 ] && shift
PY="$HOME/.cache/bitni-prepisi/.venv/bin/python"
DNEVNIK=prepisi-preizkus/nocno.log
mkdir -p prepisi-preizkus

while true; do
    caffeinate -i "$PY" -u skripte/prepisi.py --vse "$@" --meja "$MEJA" >> "$DNEVNIK" 2>&1
    tail -n 8 "$DNEVNIK" | grep -q "^KONEC" && break
    echo "PONOVNI ZAGON $(date '+%H:%M')" >> "$DNEVNIK"
    sleep 30
done
