"""Prepisi na strani: razdelek na strani epizode, datoteke za podcast
aplikacije (VTT) in statično iskalno kazalo po vseh prepisih.

Končni prepisi so v prepisi/<oznaka>.json (nastanejo z
`prepisi.py --izvozi`). Na stran gredo samo, če gradnjo poženemo z
`zgradi_stran.py --prepisi`. Dokler objava ni odobrena, se tako gradi
samo predogled v drugo mapo (--izhod), nikoli v splet/.

Kazalo: prepisi/kazalo/<prvi dve črki>.json, v vsaki datoteki
{beseda: "epizoda:odstavek,odstavek;epizoda:…"}; besede so brez strešic
in z malimi črkami. Brskalnik naloži samo kose za iskane besede.
"""

import json
import os
import re
import shutil
import unicodedata
from html import escape

from skupno import KOREN

PREPISI = os.path.join(KOREN, "prepisi")


def brez_stresic(niz):
    return "".join(z for z in unicodedata.normalize("NFD", niz) if unicodedata.category(z) != "Mn")


def besede(niz):
    return re.findall(r"[a-z0-9]{2,}", brez_stresic(niz).lower())


def cas(s):
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def vtt_cas(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def nalozi(oznaka):
    pot = os.path.join(PREPISI, f"{oznaka}.json")
    if not os.path.exists(pot):
        return None
    with open(pot, encoding="utf-8") as f:
        return json.load(f)


def vtt(prepis):
    """WebVTT z oznakami govorcev; podcast aplikacije ga prikažejo ob predvajanju."""
    vrstice = ["WEBVTT", ""]
    for o in prepis["odstavki"]:
        # Dolge odstavke razdeli na stavke s približnimi časi (sorazmerno z dolžino).
        stavki = [s for s in re.split(r"(?<=[.!?…])\s+", o["t"]) if s]
        skupaj = sum(len(s) for s in stavki) or 1
        t = o["z"]
        for s in stavki:
            konec = t + (o["k"] - o["z"]) * len(s) / skupaj
            vrstice += [f"{vtt_cas(t)} --> {vtt_cas(max(konec, t + 0.5))}", f"<v {o['ime']}>{s}", ""]
            t = konec
    return "\n".join(vrstice)


def razdelek(oznaka):
    """HTML razdelek s prepisom za stran epizode (prazen niz, če prepisa ni)."""
    p = nalozi(oznaka)
    if not p:
        return ""
    vrstice, govorci = [], {}
    for o in p["odstavki"]:
        # Vsak govorec dobi svojo barvo oblačka, po vrstnem redu, kot se oglasi.
        g = govorci.setdefault(o["ime"], len(govorci) % 4)
        jezik = ' lang="en"' if o.get("j") == "en" else ""
        dvom = ' dvom" title="Strojni prepis tega dela je manj zanesljiv.' if o.get("p", 1) < 0.6 else ""
        vrstice.append(
            f'<p data-z="{o["z"]}"{jezik} class="g{g}{dvom}"><span class="kdo"><b>{escape(o["ime"])}</b> '
            f'<a class="cas" href="?t={int(o["z"])}" data-cas="{int(o["z"])}">{cas(o["z"])}</a></span>'
            f'<span class="t">{escape(o["t"])}</span></p>')
    minut = round(p["odstavki"][-1]["k"] / 60) if p["odstavki"] else 0
    return f"""<link rel="stylesheet" href="/prepis.css">
<details class="razdelek prepis-ovoj">
<summary><span class="oblacek oranzen">Prepis pogovora</span>
<span class="prepis-stanje tiho">{len(govorci)} {'glas' if len(govorci) == 1 else 'glasova' if len(govorci) == 2 else 'glasovi' if len(govorci) in (3, 4) else 'glasov'} · {minut} min ·
<span class="ko-zaprt">pokaži</span><span class="ko-odprt">skrij</span></span></summary>
<p class="prepis-opozorilo" data-opozorilo><span><strong>Strojni prepis.</strong> Lahko vsebuje napake,
za točen citat poslušaj.</span>
<button type="button" hidden aria-label="Skrij opozorilo">Skrij</button></p>
<p class="tiho">Klik na čas začne predvajanje na tem mestu.
Prepis kot <a href="/prepisi/{escape(oznaka)}.vtt">WebVTT</a>.</p>
<div data-prepis>
<div class="prepis-orodja" hidden>
<input type="search" class="prepis-iskanje" placeholder="Išči po prepisu …" aria-label="Išči po prepisu">
<label class="tiho"><input type="checkbox" data-sledi checked> sledi predvajanju</label>
<span class="prepis-stevec tiho"></span>
</div>
<div class="prepis">
{chr(10).join(vrstice)}
</div>
</div>
</details>
<script src="/prepis.js" defer></script>"""


def zgradi(splet, epizode):
    """Kopira prepise (JSON, VTT), zgradi iskalno kazalo in doda iskanje na seznam epizod."""
    cilj = os.path.join(splet, "prepisi")
    os.makedirs(os.path.join(cilj, "kazalo"), exist_ok=True)
    viri = os.path.join(KOREN, "viri")
    shutil.copy(os.path.join(viri, "prepis.js"), splet)
    shutil.copy(os.path.join(viri, "prepis.css"), splet)

    seznam, kazalo = [], {}
    for e in epizode:
        p = nalozi(e["oznaka"])
        if not p:
            continue
        st = len(seznam)
        naslov = (e["stevilka"] + ": " if e["stevilka"] else "") + e["naslov"]
        seznam.append([e["oznaka"], naslov])
        with open(os.path.join(cilj, f"{e['oznaka']}.json"), "w", encoding="utf-8") as f:
            json.dump({"odstavki": [{"z": o["z"], "ime": o["ime"], "t": o["t"]} for o in p["odstavki"]]},
                      f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(cilj, f"{e['oznaka']}.vtt"), "w", encoding="utf-8") as f:
            f.write(vtt(p))
        for i, o in enumerate(p["odstavki"]):
            for b in set(besede(o["t"])):
                kazalo.setdefault(b, {}).setdefault(st, []).append(i)

    kosi = {}
    for b, poj in kazalo.items():
        kosi.setdefault(b[:2], {})[b] = ";".join(f"{e}:{','.join(map(str, o))}" for e, o in poj.items())
    for kljuc, vsebina in kosi.items():
        with open(os.path.join(cilj, "kazalo", f"{kljuc}.json"), "w", encoding="utf-8") as f:
            json.dump(vsebina, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(cilj, "kazalo", "epizode.json"), "w", encoding="utf-8") as f:
        json.dump(seznam, f, ensure_ascii=False, separators=(",", ":"))

    # Seznam epizod: dodaj skripto in slog za iskanje po prepisih.
    pot = os.path.join(splet, "epizode.html")
    with open(pot, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</head>", '<link rel="stylesheet" href="/prepis.css">\n</head>', 1)
    html = html.replace("</body>", '<script src="/prepis.js" defer></script>\n</body>', 1)
    with open(pot, "w", encoding="utf-8") as f:
        f.write(html)
    return len(seznam), len(kazalo), len(kosi)
