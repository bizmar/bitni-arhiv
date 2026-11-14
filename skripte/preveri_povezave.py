#!/usr/bin/env python3
"""Preveri, ali se vsak MP3 iz feeda odziva in kako velik je, brez prenosa.

Pošlje en zahtevek HEAD na epizodo, s premorom med zahtevki, in vsako
vrstico takoj zapiše v epizode.csv. Če se prekine, ob naslednjem zagonu
nadaljuje tam, kjer je ostala.

Uporaba:  python3 skripte/preveri_povezave.py [--premor 30]
"""

import argparse
import csv
import os
import time
import urllib.error
import urllib.request

from skupno import KOREN, ODJEMALEC, epizode

CSV = os.path.join(KOREN, "epizode.csv")
POLJA = ["oznaka", "guid", "naslov", "datum", "trajanje", "bajti_feed", "bajti_streznik", "http", "stanje", "url"]


def glava(url):
    zahtevek = urllib.request.Request(url, method="HEAD", headers={"User-Agent": ODJEMALEC})
    with urllib.request.urlopen(zahtevek, timeout=120) as odgovor:
        return odgovor.status, int(odgovor.headers.get("Content-Length") or 0)


def ze_preverjene():
    if not os.path.exists(CSV):
        return set()
    with open(CSV, newline="", encoding="utf-8") as f:
        return {v["oznaka"] for v in csv.DictReader(f) if v["stanje"] != "napaka"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--premor", type=float, default=30, help="sekunde med zahtevki")
    args = p.parse_args()

    narejene = ze_preverjene()
    if not narejene:
        with open(CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=POLJA).writeheader()

    seznam = epizode()
    for i, e in enumerate(seznam, 1):
        if e["oznaka"] in narejene:
            continue
        try:
            status, bajti = glava(e["url"])
        except urllib.error.HTTPError as napaka:
            status, bajti = napaka.code, 0
        except Exception as napaka:  # omrežna napaka: zapišemo in gremo naprej
            status, bajti = type(napaka).__name__, 0
        if status == 200 and bajti == e["bajti_feed"]:
            stanje = "v redu"
        elif status == 200:
            stanje = "velikost se razlikuje"
        else:
            stanje = "napaka"
        with open(CSV, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=POLJA).writerow({**e, "bajti_streznik": bajti, "http": status, "stanje": stanje})
        print(f"{i}/{len(seznam)} {e['oznaka']}: {stanje}", flush=True)
        time.sleep(args.premor)

    print(f"Konec. V epizode.csv je {len(ze_preverjene())} od {len(seznam)} epizod brez napake.")


if __name__ == "__main__":
    main()
