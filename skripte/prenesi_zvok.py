#!/usr/bin/env python3
"""Prenese vse MP3 iz feeda v mapo zvok/ in preveri vsako datoteko.

- Datoteka dobi ime po oznaki epizode, na primer zvok/151.mp3.
- Že prenesene datoteke s pravilno velikostjo preskoči, zato se prenos
  lahko prekine in nadaljuje.
- Med prenosi počaka, da ne obremenjuje strežnika.
- Na koncu zapiše zvok/SHA256SUMS za poznejše preverjanje kopij.

Uporaba:  python3 skripte/prenesi_zvok.py [--premor 5] [--mapa zvok]
Potrebuje samo Python 3, brez dodatnih paketov. Skupaj okoli 8,6 GB.
"""

import argparse
import hashlib
import os
import time
import urllib.request

from skupno import KOREN, ODJEMALEC, epizode


def prenesi(url, cilj):
    """Prenese v začasno datoteko in vrne število bajtov, ki jih je napovedal strežnik."""
    zahtevek = urllib.request.Request(url, headers={"User-Agent": ODJEMALEC})
    zacasna = cilj + ".del"
    with urllib.request.urlopen(zahtevek, timeout=120) as odgovor, open(zacasna, "wb") as f:
        napovedano = int(odgovor.headers.get("Content-Length") or 0)
        while True:
            kos = odgovor.read(1 << 20)
            if not kos:
                break
            f.write(kos)
    dejansko = os.path.getsize(zacasna)
    if napovedano and dejansko != napovedano:
        os.remove(zacasna)
        raise IOError(f"nepopoln prenos: {dejansko} od {napovedano} bajtov")
    os.replace(zacasna, cilj)
    return dejansko


def sha256(pot):
    h = hashlib.sha256()
    with open(pot, "rb") as f:
        for kos in iter(lambda: f.read(1 << 20), b""):
            h.update(kos)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--premor", type=float, default=5, help="sekunde med prenosi")
    p.add_argument("--mapa", default=os.path.join(KOREN, "zvok"))
    args = p.parse_args()
    os.makedirs(args.mapa, exist_ok=True)

    seznam = epizode()
    napake = []
    for i, e in enumerate(seznam, 1):
        cilj = os.path.join(args.mapa, e["oznaka"] + ".mp3")
        if os.path.exists(cilj) and os.path.getsize(cilj) > 0:
            print(f"{i}/{len(seznam)} {e['oznaka']}: že prenesena", flush=True)
            continue
        for poskus in range(1, 4):
            try:
                bajti = prenesi(e["url"], cilj)
                print(f"{i}/{len(seznam)} {e['oznaka']}: {bajti / 1e6:.1f} MB", flush=True)
                break
            except Exception as napaka:
                print(f"{i}/{len(seznam)} {e['oznaka']}: poskus {poskus} ni uspel ({napaka})", flush=True)
                time.sleep(30 * poskus)
        else:
            napake.append(e["oznaka"])
        time.sleep(args.premor)

    with open(os.path.join(args.mapa, "SHA256SUMS"), "w", encoding="utf-8") as f:
        for e in seznam:
            cilj = os.path.join(args.mapa, e["oznaka"] + ".mp3")
            if os.path.exists(cilj):
                f.write(f"{sha256(cilj)}  {e['oznaka']}.mp3\n")

    if napake:
        print("Ni uspelo: " + ", ".join(napake) + ". Poženi skripto znova.")
    else:
        print(f"Vseh {len(seznam)} epizod je prenesenih.")


if __name__ == "__main__":
    main()
