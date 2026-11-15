#!/usr/bin/env python3
"""Živi pregled prepisovanja: vsakih 20 s zapiše pregled.json za nadzorno
stran (pregled.html), ob vsaki novi končani epizodi pa posodobi predogled
strani s prepisi. Bere samo dnevnik in datoteke; prepisovanja ne moti.

Uporaba: nohup $PY skripte/prepisi_pregled.py &
Ogled:   python3 skripte/predogled.py 8001 prepisi-preizkus/splet
         nato http://localhost:8001/pregled
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepisi as P  # noqa: E402
import zgradi_stran  # noqa: E402

SPLET = os.path.join(P.PREIZKUS, "splet")
DNEVNIK = os.path.join(P.PREIZKUS, "nocno.log")
ZAKLJUCEK = os.path.join(P.PREIZKUS, "zakljucek.log")
VIR_STRANI = os.path.join(P.KOREN, "viri", "pregled.html")


def temperatura():
    try:
        izhod = subprocess.run(["macmon", "pipe", "-s", "1", "-i", "1000"], capture_output=True, text=True,
                               timeout=10).stdout.splitlines()[0]
        d = json.loads(izhod)
        return {"cpu": round(d["temp"]["cpu_temp_avg"]), "gpu": round(d["temp"]["gpu_temp_avg"]),
                "moc": round(d["all_power"])}
    except Exception:
        return None


def stanje(epizode, trenutna_od):
    done, vrstice = {}, []
    for e in epizode:
        pot = os.path.join(P.DELO, e["oznaka"], "whisper.json")
        if not os.path.exists(pot):
            continue
        d = P.beri_json(pot)
        n = sum(len(o["t"]) for o in d["odstavki"]) or 1
        izb = os.path.join(P.DELO, e["oznaka"], "izboljsave.json")
        done[e["oznaka"]] = {
            "sekund": d["sekund_zvoka"], "obdelava": d["sekund_obdelave"],
            "koncano": os.path.getmtime(pot),
            "dvom": round(100 * sum(len(o["t"]) for o in d["odstavki"] if o.get("p", 1) < 0.6) / n, 1),
            "en": round(100 * sum(len(o["t"]) for o in d["odstavki"] if o.get("j") == "en") / n),
            "izboljsano": len(P.beri_json(izb)) if os.path.exists(izb) else None,
        }
    dnevnik = open(DNEVNIK, encoding="utf-8", errors="replace").read() if os.path.exists(DNEVNIK) else ""
    for vrstica in dnevnik.splitlines():
        if re.match(r"^(NAPAKA|PONOVNI ZAGON|KONEC)", vrstica):
            vrstice.append(vrstica[:200])
    m = re.findall(r"^(\S+): glasovi", dnevnik, re.M)
    trenutna = m[-1] if m and m[-1] not in done else None
    zakljucek = open(ZAKLJUCEK, encoding="utf-8", errors="replace").read() if os.path.exists(ZAKLJUCEK) else ""
    faza = "prepisovanje"
    if "ZAKLJUCEK" in zakljucek:
        faza = "končano"
    elif re.search(r"dvomljivih odstavkov", zakljucek) or ("krog" in zakljucek):
        faza = "izboljšave"
    # Hitrost: zadnjih 8 epizod (realni čas zvoka / čas obdelave).
    zadnje = sorted(done.values(), key=lambda x: x["koncano"])[-8:]
    hitrost = sum(x["sekund"] for x in zadnje) / max(1, sum(x["obdelava"] for x in zadnje)) if zadnje else None
    ostane_zvoka = sum(trajanje(e) for e in epizode if e["oznaka"] not in done)
    tren_trajanje = next((trajanje(e) for e in epizode if e["oznaka"] == trenutna), 0)
    return {
        "cas": time.time(),
        "faza": faza,
        "epizode": [{"o": e["oznaka"], "s": e["stevilka"], "n": e["naslov"], "l": e["leto"],
                     "d": trajanje(e), **({"k": done[e["oznaka"]]} if e["oznaka"] in done else {})}
                    for e in reversed(epizode)],
        "trenutna": trenutna,
        # Trenutna se je začela, ko se je končala zadnja (ločevanje govorcev traja nekaj sekund).
        "trenutna_od": max((x["koncano"] for x in done.values()), default=trenutna_od),
        "trenutna_trajanje": tren_trajanje,
        "hitrost": round(hitrost, 1) if hitrost else None,
        "ostane_sekund": round(ostane_zvoka / hitrost) if hitrost else None,
        "ur_skupaj": round(sum(trajanje(e) for e in epizode) / 3600, 1),
        "ur_narejeno": round(sum(x["sekund"] for x in done.values()) / 3600, 1),
        "temperatura": temperatura(),
        "dogodki": vrstice[-10:],
        "zakljucek": [v for v in zakljucek.splitlines() if v.strip() and "warn" not in v.lower()][-8:],
        "ovoj_tece": subprocess.run(["pgrep", "-f", "prepisi_noc.sh"], capture_output=True).returncode == 0,
    }


def trajanje(e):
    deli = [int(d) for d in re.findall(r"\d+", e["trajanje"])]
    return deli[0] * 3600 + deli[1] * 60 if "h" in e["trajanje"] else deli[0] * 60


def posodobi_predogled():
    py = sys.executable
    subprocess.run([py, os.path.join(P.KOREN, "skripte", "prepisi.py"), "--izvozi"], capture_output=True)
    subprocess.run([py, os.path.join(P.KOREN, "skripte", "zgradi_stran.py"), "--prepisi", "--izhod", SPLET],
                   capture_output=True)


def pisi(stanje_):
    os.makedirs(SPLET, exist_ok=True)
    shutil.copy(VIR_STRANI, os.path.join(SPLET, "pregled.html"))
    zacasna = os.path.join(SPLET, "pregled.json.tmp")
    with open(zacasna, "w", encoding="utf-8") as f:
        json.dump(stanje_, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(zacasna, os.path.join(SPLET, "pregled.json"))


def main():
    epizode = zgradi_stran.preberi_epizode()
    zgrajenih, trenutna_od = -1, time.time()
    while True:
        try:
            s = stanje(epizode, trenutna_od)
            narejenih = sum(1 for e in s["epizode"] if "k" in e)
            if narejenih != zgrajenih:
                posodobi_predogled()
                zgrajenih = narejenih
            pisi(s)
        except Exception as napaka:
            print(f"napaka pregleda: {napaka}", flush=True)
        time.sleep(20)


if __name__ == "__main__":
    main()
