#!/usr/bin/env python3
"""Preveri, ali se vsak MP3 iz feeda odziva in kako velik je, brez prenosa.

Pošlje en zahtevek HEAD na epizodo, s premorom med zahtevki, in rezultat
zapiše v epizode.csv v korenu repozitorija.

Uporaba:  python3 skripte/preveri_povezave.py [--premor 2.5]
"""

import argparse
import csv
import os
import time
import urllib.error
import urllib.request

from skupno import KOREN, ODJEMALEC, epizode


def glava(url):
    zahtevek = urllib.request.Request(url, method="HEAD", headers={"User-Agent": ODJEMALEC})
    with urllib.request.urlopen(zahtevek, timeout=60) as odgovor:
        return odgovor.status, int(odgovor.headers.get("Content-Length") or 0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--premor", type=float, default=2.5, help="sekunde med zahtevki")
    args = p.parse_args()

    vrstice = []
    seznam = epizode()
    for i, e in enumerate(seznam, 1):
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
        vrstice.append({**e, "bajti_streznik": bajti, "http": status, "stanje": stanje})
        print(f"{i}/{len(seznam)} {e['oznaka']}: {stanje}", flush=True)
        time.sleep(args.premor)

    polja = ["oznaka", "guid", "naslov", "datum", "trajanje", "bajti_feed", "bajti_streznik", "http", "stanje", "url"]
    with open(os.path.join(KOREN, "epizode.csv"), "w", newline="", encoding="utf-8") as f:
        pisec = csv.DictWriter(f, fieldnames=polja)
        pisec.writeheader()
        pisec.writerows(vrstice)

    slabe = [v for v in vrstice if v["stanje"] != "v redu"]
    print(f"Preverjenih {len(vrstice)}, težav {len(slabe)}.")


if __name__ == "__main__":
    main()
