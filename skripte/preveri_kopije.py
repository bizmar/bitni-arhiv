#!/usr/bin/env python3
"""Preveri, ali so na kopijah zvoka vse epizode v pravi velikosti.

Uporaba:
  python3 skripte/preveri_kopije.py              vse kopije iz nastavitve.json
  python3 skripte/preveri_kopije.py ia           samo ena
  python3 skripte/preveri_kopije.py ia --vsebina prenese vsako datoteko in jo
                                                 primerja s SHA256SUMS (počasi)

Kopije, ki v nastavitve.json še nimajo pravega naslova, preskoči.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

from skupno import KOREN, ODJEMALEC, epizode


def odpri(url, metoda):
    z = urllib.request.Request(url, method=metoda, headers={"User-Agent": ODJEMALEC})
    return urllib.request.urlopen(z, timeout=120)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kopije", nargs="*")
    p.add_argument("--vsebina", action="store_true")
    p.add_argument("--premor", type=float, default=0.5, help="sekunde med zahtevki")
    args = p.parse_args()

    with open(os.path.join(KOREN, "nastavitve.json"), encoding="utf-8") as f:
        kopije = json.load(f)["kopije"]
    vsote = {}
    if args.vsebina:
        with open(os.path.join(KOREN, "SHA256SUMS"), encoding="utf-8") as f:
            vsote = {v.split()[1]: v.split()[0] for v in f if v.strip()}

    slabo = 0
    for kljuc in args.kopije or kopije:
        vzorec = kopije[kljuc]["zvok"]
        if "SE-NI-DOLOCEN" in vzorec:
            print(f"{kopije[kljuc]['ime']}: naslov še ni določen, preskočeno")
            continue
        napake = []
        for e in epizode():
            url = vzorec.format(oznaka=e["oznaka"])
            try:
                if args.vsebina:
                    h = hashlib.sha256()
                    with odpri(url, "GET") as o:
                        for kos in iter(lambda: o.read(1 << 20), b""):
                            h.update(kos)
                    if h.hexdigest() != vsote.get(e["oznaka"] + ".mp3"):
                        napake.append(f"{e['oznaka']}: vsebina se razlikuje")
                else:
                    with odpri(url, "HEAD") as o:
                        bajti = int(o.headers.get("Content-Length") or -1)
                    if bajti != e["bajti_feed"]:
                        napake.append(f"{e['oznaka']}: {bajti} namesto {e['bajti_feed']} bajtov")
            except Exception as napaka:
                napake.append(f"{e['oznaka']}: {napaka}")
            time.sleep(args.premor)
        print(f"{kopije[kljuc]['ime']}: {215 - len(napake)} od 215 v redu")
        for n in napake:
            print("  " + n)
        slabo += len(napake)
    sys.exit(1 if slabo else 0)


if __name__ == "__main__":
    main()
