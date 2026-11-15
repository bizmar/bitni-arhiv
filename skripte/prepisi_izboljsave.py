#!/usr/bin/env python3
"""Izboljšave strojnih prepisov po prvem prehodu.

1. Imena manjkajočih govorcev (--imena). Za vsako gručo brez imena se
   zbirajo glasovi iz več neodvisnih virov:
     - samopredstavitev v lastnem odstavku (»moje ime je …«, »jaz sem …«)  +3
     - predstavitev tik pred odstavkom (»z nami je …«, »to je …«)          +2
     - nagovor tik pred odstavkom (»Dajan, kako …«, »… kaj praviš, Žiga?«) +1
     - nagovor v lastnem odstavku pomeni, da govorec NI ta oseba          -1
     - glas: podobnost z vsemi znanimi vzorci (tudi z osebami, ki jih
       feed ne navaja)                                                  do +3
   Kandidati so osebe iz feeda in imena, ki jih predstavijo v uvodu ali
   zaključku. Ime se dodeli samo ob jasni zmagi (vsaj 3 glasovi in vsaj
   dvakrat več od drugega). Majhne gruče (pod 3 %) so večinoma šum in dobijo
   ime najbližjega glasu v epizodi.
   Rezultat: delo/<oznaka>/imena-izboljsano.json (z viri in točkami).

2. Dvomljivi deli (--dvomljivi). Odstavki z nizko zanesljivostjo se znova
   prepišejo na več načinov (brez namiga, z besednjakom iz opomb epizode,
   z zamaknjenim oknom, z vzorčenjem). Med vsemi različicami, tudi izvirno,
   se izbere tista z najmanjšim pričakovanim odstopanjem od ostalih
   (MBR, »minimum Bayes risk«): statistično najverjetnejše besedilo, ne pa
   zlepek posameznih besed. Če večina različic ne slliši ničesar, je bil
   izvirnik izmišljen in se odstrani.
   Rezultat: delo/<oznaka>/izboljsave.json (vse različice in ocene, za pregled).

Uporaba (okolje kot pri prepisi.py):
  $PY skripte/prepisi_izboljsave.py --imena [oznake …]
  $PY skripte/prepisi_izboljsave.py --dvomljivi [oznake …] [--meja 70]
Brez oznak obdela vse prepisane epizode. Nato prepisi.py --izvozi.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepisi as P  # noqa: E402

VELIKA = "A-ZČŠŽĆĐ"
MALA = "a-zčšžćđ"
IME = rf"([{VELIKA}][{MALA}]+(?:[ -][{VELIKA}][{MALA}]+)?)"
UVOD = re.compile(rf"(?:z nami (?:je |sta )?(?:danes |še |tudi )*|to je |gospod |gospa |gost(?:ja)? (?:je )?|"
                  rf"pozdravljen[aio]? |dobrodošl[aio]? |predstavljam |pridružil[ae]? (?:se )?(?:nam )?(?:je )?){IME}")
SAMO = re.compile(rf"(?:moje ime je|jaz sem|sem pa|tukaj) {IME}")
NE_IMENA = {"Danes", "Dobar", "Dober", "Hvala", "Lep", "Lepo", "Ja", "Ne", "Tako", "Zdaj", "Bitni", "Bitnih",
            "Apple", "Google", "Microsoft", "Samsung", "Twitter", "Facebook", "Skype", "Res", "To", "Ok", "Okej"}


def brez(niz):
    return "".join(z for z in unicodedata.normalize("NFD", niz) if unicodedata.category(z) != "Mn").lower()


def koren(ime):
    """Koren imena za sklanjatve: Žiga/Žigom/Žigi -> 'ziga'[:4]."""
    i = brez(ime.split()[0])
    return i[:max(3, len(i) - 1)]


def omenja(besedilo, ime):
    k = koren(ime)
    return any(b.startswith(k) for b in re.findall(r"\w+", brez(besedilo)))


def nagovor(besedilo, ime):
    """Ali je oseba nagovorjena: ime na začetku stavka z vejico ali na koncu vprašanja."""
    k = koren(ime)
    for stavek in re.split(r"(?<=[.!?])\s+", besedilo):
        s = brez(stavek).strip()
        prva = re.match(r"(\w+),", s)
        zadnja = re.search(r",\s*(\w+)\s*[?!.]$", s)
        if (prva and prva.group(1).startswith(k)) or (zadnja and zadnja.group(1).startswith(k)):
            return True
    return False


def imena_iz_besedila(odstavki, zacetek=240, konec=240):
    """Polna imena, ki jih predstavijo v uvodu ali zaključku."""
    if not odstavki:
        return set()
    t_konec = odstavki[-1]["k"]
    najdena = set()
    for o in odstavki:
        if o["z"] > zacetek and o["z"] < t_konec - konec:
            continue
        for vzorec in (UVOD, SAMO):
            for m in vzorec.finditer(o["t"]):
                ime = m.group(1)
                if ime.split()[0] not in NE_IMENA and len(ime.split()) == 2:
                    najdena.add(ime)
    return najdena


def izboljsaj_imena(oznaka, izpis=True):
    import numpy as np
    e = P.podatki_epizode(oznaka)
    pot = os.path.join(P.DELO, oznaka, "whisper.json")
    if not os.path.exists(pot):
        return None
    gl = P.beri_json(os.path.join(P.DELO, oznaka, "glasovi.json"))
    odstavki = P.brez_izmisljenega(P.beri_json(pot)["odstavki"], e)
    glavna = P.zdruzene(gl)
    im = P.imena(oznaka, e, gl)
    neznane = sorted({glavna[g] for g, i in im.items() if i.startswith("Govorec")})
    rezultat = {g: {"ime": i, "vir": "glas (prvi prehod)"} for g, i in im.items() if not i.startswith("Govorec")}
    if not neznane:
        P.pisi_json(os.path.join(P.DELO, oznaka, "imena-izboljsano.json"), rezultat)
        return rezultat

    zasedena = {v["ime"] for v in rezultat.values()}
    kandidati = ({o["ime"] for o in e["osebe"]} | imena_iz_besedila(odstavki)) - zasedena
    # Isto osebo lahko omenijo s polnim imenom in samo z imenom: obdrži polno.
    kandidati = {k for k in kandidati if not any(k != d and d.startswith(k) for d in kandidati)}

    vzorci = {}
    if os.path.isdir(P.VZORCI):
        for d in os.listdir(P.VZORCI):
            if d.endswith(".npy"):
                v = np.load(os.path.join(P.VZORCI, d))
                vzorci[d[:-4]] = v / np.linalg.norm(v)

    for g in neznane:
        if gl["delezi"][g] < 0.03:
            continue
        tocke, razlogi = {k: 0.0 for k in kandidati}, {k: [] for k in kandidati}
        c = np.array(gl["sredisca"][g])
        c /= np.linalg.norm(c)
        for k in kandidati:
            if k in vzorci:
                s = float(c @ vzorci[k])
                if s > 0.6:
                    tocke[k] += min(3.0, (s - 0.6) * 10)
                    razlogi[k].append(f"glas {s:.2f}")
                elif s < 0.4:
                    tocke[k] -= 2
                    razlogi[k].append(f"drug glas {s:.2f}")
        # Neznane osebe, ki jih feed ne navaja, a imajo znan glas.
        for k, v in vzorci.items():
            if k not in kandidati and k not in zasedena and float(c @ v) > 0.75:
                tocke[k] = 3.0
                razlogi[k] = [f"glas {float(c @ v):.2f} (ni v feedu)"]
        for i, o in enumerate(odstavki):
            if glavna.get(o["g"], o["g"]) != g:
                continue
            prej = odstavki[i - 1] if i and glavna.get(odstavki[i - 1]["g"]) != g else None
            for k in list(tocke):
                if SAMO.search(o["t"]) and any(omenja(m.group(1), k) for m in SAMO.finditer(o["t"])):
                    tocke[k] += 3
                    razlogi[k].append(f"samopredstavitev {P.cas(o['z'])}")
                if nagovor(o["t"], k):
                    tocke[k] -= 1
                    razlogi[k].append(f"sam nagovarja {P.cas(o['z'])}")
                if prej:
                    if any(omenja(m.group(1), k) for m in UVOD.finditer(prej["t"])):
                        tocke[k] += 2
                        razlogi[k].append(f"predstavljen {P.cas(prej['z'])}")
                    if nagovor(prej["t"], k):
                        tocke[k] += 1
                        razlogi[k].append(f"nagovorjen {P.cas(prej['z'])}")
        vrsta = sorted(tocke.items(), key=lambda kv: -kv[1])
        prvi = vrsta[0] if vrsta else (None, 0)
        drugi = vrsta[1][1] if len(vrsta) > 1 else 0
        if prvi[0] and prvi[1] >= 3 and prvi[1] >= 2 * max(drugi, 0.5):
            rezultat[g] = {"ime": prvi[0], "vir": ", ".join(razlogi[prvi[0]][:6]), "tocke": round(prvi[1], 1),
                           "drugi": round(drugi, 1)}
            zasedena.add(prvi[0])
            kandidati.discard(prvi[0])
        if izpis:
            print(f"  {oznaka} {g} ({gl['delezi'][g]:.0%}): " +
                  ", ".join(f"{k} {t:.1f}" for k, t in vrsta[:3]) +
                  (f"  -> {rezultat[g]['ime']}" if g in rezultat else "  -> ostane neznan"))

    # Majhne gruče: ime najbližjega glasu v epizodi (večinoma šum ali kratki vskoki).
    for g in neznane:
        if g in rezultat or gl["delezi"][g] >= 0.03:
            continue
        c = np.array(gl["sredisca"][g])
        najblizji = max(rezultat, key=lambda h: float(np.dot(c, gl["sredisca"][h]) / np.linalg.norm(c) /
                                                     np.linalg.norm(gl["sredisca"][h])), default=None)
        if najblizji:
            rezultat[g] = {"ime": rezultat[najblizji]["ime"], "vir": "majhna gruča, najbližji glas"}
    # Združene gruče dobijo ime glavne.
    for g in gl["sredisca"]:
        if g not in rezultat and glavna[g] in rezultat:
            rezultat[g] = rezultat[glavna[g]]
    P.pisi_json(os.path.join(P.DELO, oznaka, "imena-izboljsano.json"), rezultat)
    return rezultat


# ---------- dvomljivi deli ----------

def besedila_razlika(a, b):
    """Normirana razdalja med besedili po besedah (0 enako, 1 povsem drugače)."""
    from difflib import SequenceMatcher
    x, y = re.findall(r"\w+", brez(a)), re.findall(r"\w+", brez(b))
    if not x and not y:
        return 0.0
    return 1.0 - SequenceMatcher(None, x, y, autojunk=False).ratio()


LATINICA = re.compile(r"^[\w\s.,!?;:'\"()\-–…%€$&/+@#*0-9A-Za-zČŠŽĆĐčšžćđäöüéèáàíóúñß]*$")


def verodostojnost(t, trajanje, e):
    """Utež 0–1: ali je besedilo sploh lahko pravi govor tega odseka."""
    if not t.strip():
        return 0.3                       # tišina je mogoča, a manj verjetna
    if not LATINICA.match(t):
        return 0.0                       # tuja pisava: izmišljeno
    if not P.brez_izmisljenega([{"t": t, "z": 0, "k": 1, "g": "G1"}], e):
        return 0.0                       # odmev namiga ali znana izmišljena fraza
    hitrost = len(t) / max(trajanje, 0.5)  # znakov na sekundo; govor je okoli 10–18
    if hitrost < 3 or hitrost > 30:
        return 0.3
    return 1.0


def mbr(hipoteze):
    """Izbere hipotezo z najmanjšim pričakovanim odstopanjem od drugih,
    utežena z zanesljivostjo vsake. Vrne (indeks, ocene)."""
    ocene = []
    for i, (t, _, _) in enumerate(hipoteze):
        tveganje = sum(w * besedila_razlika(t, u) for j, (u, w, _) in enumerate(hipoteze) if j != i)
        tveganje /= max(1e-9, sum(w for j, (_, w, _) in enumerate(hipoteze) if j != i))
        ocene.append(round(tveganje, 3))
    kandidati = [i for i in range(len(hipoteze)) if hipoteze[i][1] > 0] or list(range(len(hipoteze)))
    return min(kandidati, key=lambda i: (ocene[i], -hipoteze[i][1])), ocene


def besednjak(e):
    """Lastna imena in izrazi iz opomb epizode, za namig modelu."""
    golo = re.sub(r"<[^>]+>", " ", e["opombe"])
    izrazi = re.findall(r"\b[A-Z][\w\-\.]*(?:\s+[A-Z0-9][\w\-\.]*)*", golo)
    vidni = []
    for i in izrazi:
        if i not in vidni and len(i) > 2:
            vidni.append(i)
    return ", ".join(vidni[:40])


def prepisi_odsek(zvok, z, k, jezik, namig, temperatura=0.0):
    import mlx_whisper
    kos = zvok[int(max(0, z) * P.SR):int(k * P.SR)]
    if len(kos) < P.SR * 0.3:
        return "", 0.0
    r = mlx_whisper.transcribe(kos, path_or_hf_repo=P.WHISPER, language=jezik, initial_prompt=namig,
                               condition_on_previous_text=False, word_timestamps=True,
                               temperature=temperatura)
    besede = [b for s in r["segments"] for b in s.get("words", [])]
    t = "".join(b["word"] for b in besede).strip()
    p = sum(b.get("probability", 1) for b in besede) / len(besede) if besede else 0.0
    return t, p


def izboljsaj_dvomljive(oznaka, varuh=None, meja_p=0.6, najdaljsi=28.0):
    """Dvomljivi so odstavki z nizko zanesljivostjo ali s sumljivo malo
    besedila za trajanje govora (izpuščen govor)."""
    e = P.podatki_epizode(oznaka)
    pot = os.path.join(P.DELO, oznaka, "whisper.json")
    if not os.path.exists(pot):
        return None
    izhod = os.path.join(P.DELO, oznaka, "izboljsave.json")
    if os.path.exists(izhod):
        return P.beri_json(izhod)
    odstavki = P.brez_izmisljenega(P.beri_json(pot)["odstavki"], e)
    dvomljivi = [o for o in P.beri_json(pot)["odstavki"] if o["k"] - o["z"] <= najdaljsi and
                 (o.get("p", 1) < meja_p or (o["k"] - o["z"] > 4 and len(o["t"]) / (o["k"] - o["z"]) < 4))]
    zvok = P.nalozi_zvok(oznaka)
    slovar = besednjak(e)
    ljudje = ", ".join(o["ime"] for o in e["osebe"])
    namigi = {
        "sl": ("Bitni pogovori, slovenski podcast o tehnologiji.", f"Bitni pogovori. {slovar}" if slovar else None),
        "en": ("A conversation on Bitni pogovori, a tech podcast.", f"Bitni pogovori. {slovar}" if slovar else None),
    }
    zapisi = []
    for o in dvomljivi:
        jezik = o.get("j", "sl")
        trajanje = o["k"] - o["z"]
        hip = [(o["t"], o.get("p", 0.5) * verodostojnost(o["t"], trajanje, e), "izvirnik")]
        z0, k0 = o["z"] - 0.3, o["k"] + 0.3   # malo rezerve, da besede na robu niso odrezane
        for opis, z, k, namig, temp in (
            ("brez namiga", z0, k0, None, 0.0),
            ("besednjak iz opomb", z0, k0, namigi[jezik][1], 0.0),
            ("kratek namig", z0, k0, namigi[jezik][0], 0.0),
            ("vzorčenje 0,3", z0, k0, namigi[jezik][0], 0.3),
            ("vzorčenje 0,5", z0, k0, None, 0.5),
        ):
            if namig is None and opis == "besednjak iz opomb":
                continue
            t, p = prepisi_odsek(zvok, z, k, jezik, namig, temp)
            hip.append((t, max(p, 0.05) * verodostojnost(t, trajanje, e), opis))
            if varuh:
                varuh.pocakaj()
        izbran, ocene = mbr(hip)
        zapisi.append({"z": o["z"], "k": o["k"], "staro": o["t"], "novo": hip[izbran][0], "izbrana": hip[izbran][2],
                       "hipoteze": [{"t": t, "p": round(p, 2), "nacin": n, "tveganje": r}
                                    for (t, p, n), r in zip(hip, ocene)]})
    P.pisi_json(izhod, zapisi)
    return zapisi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oznake", nargs="*")
    ap.add_argument("--imena", action="store_true")
    ap.add_argument("--dvomljivi", action="store_true")
    ap.add_argument("--meja", type=float, default=70.0, help="ciljna temperatura v °C")
    a = ap.parse_args()
    oznake = a.oznake or sorted(d for d in os.listdir(P.DELO)
                                if os.path.exists(os.path.join(P.DELO, d, "whisper.json")))
    if a.imena:
        for o in oznake:
            izboljsaj_imena(o)
    if a.dvomljivi:
        varuh = P.Varuh(a.meja)
        for o in oznake:
            z = izboljsaj_dvomljive(o, varuh)
            if z is None:
                continue
            spremenjenih = sum(1 for x in z if x["novo"] != x["staro"])
            print(f"{o}: {len(z)} dvomljivih odstavkov, {spremenjenih} spremenjenih")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
