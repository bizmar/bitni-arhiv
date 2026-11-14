#!/usr/bin/env python3
"""Naloži zvok iz mape zvok/ na eno od treh kopij.

Uporaba:
  python3 skripte/nalozi_zvok.py r2      [--poskus]
  python3 skripte/nalozi_zvok.py ia      [--poskus]
  python3 skripte/nalozi_zvok.py github  [--poskus]

--poskus samo izpiše, kaj bi naložil. Datoteke, ki so na cilju že v pravi
velikosti, preskoči, zato se nalaganje lahko prekine in nadaljuje.

Ključi se berejo iz okolja in se NIKOLI ne zapišejo v repozitorij:

  r2:      R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
  ia:      IA_ACCESS_KEY, IA_SECRET_KEY, IA_OZNAKA   (ključi: archive.org/account/s3.php)
           neobvezno IA_LICENCA (privzeto CC BY-NC-SA 4.0)
  github:  brez ključev, potrebuje nameščen in prijavljen ukaz `gh`

Potrebuje samo Python 3, brez dodatnih paketov.
"""

import argparse
import datetime
import hashlib
import hmac
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from skupno import KOREN, ODJEMALEC, epizode

PRAZNO = hashlib.sha256(b"").hexdigest()
REPO = "bizmar/bitni-arhiv"
IZDAJA = "zvok"
LICENCA = "https://creativecommons.org/licenses/by-nc-sa/4.0/"


def okolje(*imena):
    manjka = [i for i in imena if not os.environ.get(i)]
    if manjka:
        sys.exit("Manjkajo spremenljivke okolja: " + ", ".join(manjka))
    return [os.environ[i] for i in imena]


# ---------- podpis AWS SigV4 (Cloudflare R2 govori protokol S3) ----------

def podpisi(metoda, gostitelj, pot, glave, kljuc_id, skrivnost, regija, cas, vsebina_sha):
    """Vrne glave zahtevka z dodanim podpisom."""
    datum = cas.strftime("%Y%m%d")
    glave = {k.lower(): v for k, v in glave.items()}
    glave.update(
        {"host": gostitelj, "x-amz-date": cas.strftime("%Y%m%dT%H%M%SZ"), "x-amz-content-sha256": vsebina_sha}
    )
    imena = ";".join(sorted(glave))
    kanonicno = "\n".join(
        [metoda, urllib.parse.quote(pot, safe="/-_.~"), ""]
        + [f"{k}:{glave[k].strip()}" for k in sorted(glave)]
        + ["", imena, vsebina_sha]
    )
    obseg = f"{datum}/{regija}/s3/aws4_request"
    za_podpis = "\n".join(
        ["AWS4-HMAC-SHA256", glave["x-amz-date"], obseg, hashlib.sha256(kanonicno.encode()).hexdigest()]
    )
    k = ("AWS4" + skrivnost).encode()
    for del_ in (datum, regija, "s3", "aws4_request"):
        k = hmac.new(k, del_.encode(), hashlib.sha256).digest()
    podpis = hmac.new(k, za_podpis.encode(), hashlib.sha256).hexdigest()
    glave["authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={kljuc_id}/{obseg}, SignedHeaders={imena}, Signature={podpis}"
    )
    return glave


def poslji(gostitelj, metoda, pot, glave, datoteka=None):
    """Pošlje zahtevek; datoteko pretaka, da ne gre cela v pomnilnik."""
    zveza = http.client.HTTPSConnection(gostitelj, timeout=600)
    try:
        zveza.putrequest(metoda, urllib.parse.quote(pot, safe="/-_.~"), skip_host=True, skip_accept_encoding=True)
        for k, v in glave.items():
            zveza.putheader(k, v)
        zveza.endheaders()
        if datoteka:
            with open(datoteka, "rb") as f:
                for kos in iter(lambda: f.read(1 << 20), b""):
                    zveza.send(kos)
        odgovor = zveza.getresponse()
        telo = odgovor.read()
        return odgovor.status, dict(odgovor.getheaders()), telo
    finally:
        zveza.close()


# ---------- Cloudflare R2 ----------

def r2(datoteke, poskus):
    racun, kljuc_id, skrivnost, vedro = okolje(
        "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"
    )
    gostitelj = f"{racun}.r2.cloudflarestorage.com"

    def zahtevek(metoda, ime, dodatno=None, datoteka=None, sha=PRAZNO):
        glave = podpisi(
            metoda, gostitelj, f"/{vedro}/{ime}", dodatno or {}, kljuc_id, skrivnost, "auto",
            datetime.datetime.now(datetime.timezone.utc), sha,
        )
        return poslji(gostitelj, metoda, f"/{vedro}/{ime}", glave, datoteka)

    def velikost(ime):
        stanje, glave, _ = zahtevek("HEAD", ime)
        if stanje == 200:
            return int(glave.get("Content-Length", -1))
        if stanje == 404:
            return None
        sys.exit(f"R2 je zavrnil preverjanje ({stanje}). Preveri ključe in ime vedra.")

    def nalozi(ime, pot):
        stanje, _, telo = zahtevek(
            "PUT", ime,
            {"content-type": "audio/mpeg", "content-length": str(os.path.getsize(pot)),
             "cache-control": "public, max-age=31536000, immutable"},
            pot, "UNSIGNED-PAYLOAD",
        )
        if stanje != 200:
            raise IOError(f"{stanje} {telo[:200]!r}")

    zanka(datoteke, velikost, nalozi, poskus)


# ---------- Internet Archive ----------

def ia(datoteke, poskus):
    kljuc, skrivnost, oznaka = okolje("IA_ACCESS_KEY", "IA_SECRET_KEY", "IA_OZNAKA")
    gostitelj = "s3.us.archive.org"
    na_cilju = {}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"https://archive.org/metadata/{oznaka}/files", headers={"User-Agent": ODJEMALEC}),
            timeout=60,
        ) as o:
            for f in json.load(o).get("result", []):
                na_cilju[f["name"]] = int(f.get("size", -1))
    except Exception:
        pass  # zapis še ne obstaja

    def meta(vrednost):
        return "uri(" + urllib.parse.quote(vrednost) + ")"

    opis = {
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        "x-archive-keep-old-version": "0",
        "x-archive-size-hint": str(sum(os.path.getsize(p) for _, p in datoteke)),
        "x-archive-meta-mediatype": "audio",
        "x-archive-meta-collection": "opensource_audio",
        "x-archive-meta-title": meta("Bitni pogovori: arhiv podcasta 2012–2019"),
        "x-archive-meta-creator": meta("Bitni pogovori"),
        "x-archive-meta-language": "slv",
        "x-archive-meta-date": "2012/2019",
        "x-archive-meta-subject": meta("podcast;tehnologija;slovenščina"),
        "x-archive-meta-description": meta(
            "Celoten arhiv slovenskega tehnološkega podcasta Bitni pogovori, 215 epizod. "
            "Stran in feed: https://www.bitnipogovori.si"
        ),
    }
    opis["x-archive-meta-licenseurl"] = os.environ.get("IA_LICENCA") or LICENCA

    def nalozi(ime, pot):
        glave = dict(opis)
        glave.update(
            {"host": gostitelj, "authorization": f"LOW {kljuc}:{skrivnost}", "user-agent": ODJEMALEC,
             "content-type": "audio/mpeg", "content-length": str(os.path.getsize(pot))}
        )
        stanje, _, telo = poslji(gostitelj, "PUT", f"/{oznaka}/{ime}", glave, pot)
        if stanje != 200:
            raise IOError(f"{stanje} {telo[:200]!r}")

    zanka(datoteke, na_cilju.get, nalozi, poskus)


# ---------- GitHub Releases ----------

def github(datoteke, poskus):
    def gh(*ukaz, preveri=True):
        r = subprocess.run(["gh", *ukaz, "--repo", REPO], capture_output=True, text=True)
        if preveri and r.returncode:
            raise IOError(r.stderr.strip())
        return r

    na_cilju = {}
    r = gh("release", "view", IZDAJA, "--json", "assets", preveri=False)
    if r.returncode == 0:
        na_cilju = {a["name"]: a["size"] for a in json.loads(r.stdout)["assets"]}
    elif not poskus:
        gh("release", "create", IZDAJA, "--title", "Zvok vseh epizod",
           "--notes", "Kopija zvoka vseh 215 epizod. Stran in feed: https://www.bitnipogovori.si")

    def nalozi(ime, pot):
        gh("release", "upload", IZDAJA, pot, "--clobber")

    zanka(datoteke, na_cilju.get, nalozi, poskus)


# ---------- skupna zanka ----------

def zanka(datoteke, velikost_na_cilju, nalozi, poskus):
    napake = []
    for i, (ime, pot) in enumerate(datoteke, 1):
        predpona = f"{i}/{len(datoteke)} {ime}"
        if velikost_na_cilju(ime) == os.path.getsize(pot):
            print(f"{predpona}: že na cilju", flush=True)
            continue
        if poskus:
            print(f"{predpona}: bi naložil {os.path.getsize(pot) / 1e6:.1f} MB", flush=True)
            continue
        for n in range(1, 4):
            try:
                nalozi(ime, pot)
                print(f"{predpona}: naloženo {os.path.getsize(pot) / 1e6:.1f} MB", flush=True)
                break
            except Exception as napaka:
                print(f"{predpona}: poskus {n} ni uspel ({napaka})", flush=True)
                time.sleep(20 * n)
        else:
            napake.append(ime)
    if napake:
        sys.exit("Ni uspelo: " + ", ".join(napake) + ". Poženi še enkrat.")
    print("Končano.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kopija", choices=["r2", "ia", "github"])
    p.add_argument("--poskus", action="store_true", help="samo izpiši, nič ne nalagaj")
    p.add_argument("--mapa", default=os.path.join(KOREN, "zvok"))
    args = p.parse_args()

    datoteke, manjka = [], []
    for e in epizode():
        pot = os.path.join(args.mapa, e["oznaka"] + ".mp3")
        if not os.path.exists(pot):
            manjka.append(e["oznaka"])
        elif os.path.getsize(pot) != e["bajti_feed"]:
            sys.exit(f"{pot}: velikost se ne ujema s feedom. Najprej popravi lokalno kopijo.")
        else:
            datoteke.append((e["oznaka"] + ".mp3", pot))
    if manjka:
        sys.exit(f"V {args.mapa} manjka {len(manjka)} epizod. Najprej poženi skripte/prenesi_zvok.py.")

    {"r2": r2, "ia": ia, "github": github}[args.kopija](datoteke, args.poskus)


if __name__ == "__main__":
    main()
