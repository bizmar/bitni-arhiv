#!/usr/bin/env python3
"""Zgradi celotno stran arhiva v mapo splet/ iz shranjenega feeda.

Rezultat so navadne datoteke HTML, CSS in ena majhna datoteka JavaScript.
Potrebuje samo Python 3, brez dodatnih paketov.

Uporaba:  python3 skripte/zgradi_stran.py
Predogled: python3 -m http.server --directory splet 8000
"""

import json
import os
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import escape

import zgradi_feede
from skupno import FEED, KOREN

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
PODCAST = "{https://podcastindex.org/namespace/1.0}"
SPLET = os.path.join(KOREN, "splet")
OPIS = "Podcast o Applu, tehnologijah, gadgetih, produktivnosti in sploh vsem."


# ---------- podatki ----------

def brez_stresic(niz):
    return "".join(z for z in unicodedata.normalize("NFD", niz) if unicodedata.category(z) != "Mn")


def v_oznako(ime):
    return re.sub(r"[^a-z0-9]+", "-", brez_stresic(ime).lower()).strip("-")


def trajanje(niz):
    deli = [int(d) for d in niz.split(":")] if niz else []
    while len(deli) < 3:
        deli.insert(0, 0)
    ure, minute, _ = deli
    return f"{ure} h {minute} min" if ure else f"{minute} min"


def ocisti_opombe(html):
    """Opombe so najina vsebina; odstranimo samo tisto, kar na statični strani nima kaj početi."""
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"\son\w+=\"[^\"]*\"", "", html, flags=re.I)
    html = re.sub(r"https://join\.slack\.com/[^\"'<\s]+", "#", html)
    return html.strip()


def golo_besedilo(html):
    besedilo = re.sub(r"<[^>]+>", " ", html)
    for stari, novi in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        besedilo = besedilo.replace(stari, novi)
    return re.sub(r"\s+", " ", besedilo).strip()


def preberi_epizode():
    """Vrne epizode od najnovejše do najstarejše."""
    kanal = ET.parse(FEED).getroot().find("channel")
    epizode = []
    for item in kanal.findall("item"):
        polni_naslov = item.findtext("title")
        ujemanje = re.match(r"Episode ([^:]+): (.*)", polni_naslov)
        zvok = item.find("enclosure")
        datum = parsedate_to_datetime(item.findtext("pubDate"))
        poglavja = item.find(PODCAST + "chapters")
        epizode.append({
            "oznaka": item.findtext("link").rstrip("/").rsplit("/", 1)[-1],
            "stevilka": ujemanje.group(1) if ujemanje else "",
            "naslov": ujemanje.group(2) if ujemanje else polni_naslov,
            "leto": datum.year,
            "datum": f"{datum.day}. {datum.month}. {datum.year}",
            "datum_iso": datum.date().isoformat(),
            "trajanje": trajanje(item.findtext(ITUNES + "duration")),
            "podnaslov": (item.findtext(ITUNES + "subtitle") or "").strip(),
            "opombe": ocisti_opombe(item.findtext(CONTENT + "encoded") or ""),
            "zvok_izvirnik": zvok.get("url"),
            "bajti": int(zvok.get("length") or 0),
            "osebe": [{"ime": o.text.strip(), "vloga": o.get("role"), "oznaka": v_oznako(o.text)}
                      for o in item.findall(PODCAST + "person")],
            "poglavja": poglavja.get("url").rstrip("/").split("/")[-2] if poglavja is not None else None,
        })
    return epizode


# ---------- deli strani ----------

def naslov_zvoka(n, e):
    """Dokler kopije zvoka niso postavljene, stran predvaja z izvirnega naslova."""
    if not kopije_so_postavljene(n):
        return e["zvok_izvirnik"]
    return f"/audio/{e['oznaka']}.mp3"


def kopije_so_postavljene(n):
    return bool(n.get("zvok_nalozen")) and "SE-NI-DOLOCEN" not in json.dumps(n["kopije"])


def glava_html(naslov, opis, pot, n):
    return f"""<!doctype html>
<html lang="sl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape(naslov)}</title>
<meta name="description" content="{escape(opis)}">
<link rel="canonical" href="{n['domena']}{pot}">
<link rel="alternate" type="application/rss+xml" title="Bitni pogovori" href="{n['glavni_feed']}">
<link rel="icon" href="/slike/favicon.png">
<link rel="apple-touch-icon" href="/slike/touch-icon.png">
<meta property="og:title" content="{escape(naslov)}">
<meta property="og:description" content="{escape(opis)}">
<meta property="og:image" content="{n['domena']}/slike/naslovnica.jpg">
<meta name="theme-color" content="#0E86F2">
<link rel="stylesheet" href="/slog.css">
</head>
<body>
"""


def glava_mala(nazaj="/", opis="Nazaj na vstopno stran"):
    return f"""<header class="glava-mala">
<div class="ovoj">
<a class="ime" href="{nazaj}" aria-label="{opis}"><span class="puscica" aria-hidden="true">←</span>bitni <span>pogovori</span></a>
</div>
</header>
"""


def noga(n):
    kopije = ""
    feedi = '<a href="/rss">Glavni feed</a>'
    if kopije_so_postavljene(n):
        kopije = """<div class="stolpec">
<h4 style="color: var(--oranzna)">Arhiv je na treh mestih</h4>
<span>Cloudflare, Internet Archive in GitHub.</span>
<span>Na strani vsake epizode so povezave do vseh treh kopij.</span>
</div>
"""
        feedi += "".join(f'\n<a href="/rss-{k}.xml">Feed: {escape(v["ime"])}</a>' for k, v in n["kopije"].items())
    return f"""<footer class="noga">
<div class="ovoj">
<div class="stolpci">
{kopije}<div class="stolpec">
<h4 style="color: var(--sinja)">Feedi</h4>
{feedi}
</div>
<div class="stolpec">
<h4 style="color: var(--svetlo-modra)">O strani</h4>
<span>Nejc Žorga Dulmin, Mark Bizilj, Alan Rener</span>
<span>Stran in arhiv zgrajena z umetno inteligenco <a href="https://claude.com">Claude</a>.</span>
<span>Brez piškotkov in brez sledenja.</span>
<a href="https://github.com/bizmar/bitni-arhiv">Izvorna koda arhiva</a>
</div>
</div>
<p class="izjava">Epizode so na voljo pod licenco <a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.sl">CC BY-NC-SA 4.0</a>: deljenje in predelava z navedbo avtorjev, nekomercialno, pod enakimi pogoji.</p>
<p class="izjava">Uporaba posnetkov za učenje sinteze govora ali posnemanje glasov ni dovoljena brez pisnega soglasja govorcev. Pravice do besedilnega in podatkovnega rudarjenja so pridržane.</p>
</div>
</footer>
<script src="/stran.js" defer></script>
</body>
</html>
"""


def predvajalnik(n, e):
    return f"""<div class="predvajalnik" data-oznaka="{escape(e['oznaka'])}">
<audio controls preload="none" src="{escape(naslov_zvoka(n, e))}"></audio>
<div class="dodatki" hidden>
<button type="button" class="gumb obroba" data-skok="-15" aria-label="Nazaj 15 sekund">−15</button>
<button type="button" class="gumb obroba" data-skok="30" aria-label="Naprej 30 sekund">+30</button>
<button type="button" class="gumb obroba" data-hitrost aria-label="Hitrost predvajanja">1×</button>
</div>
</div>"""


def obdobje_za(e, obdobja):
    """Obdobje logotipa, v katerem je epizoda izšla (obdobja so od najnovejšega)."""
    for o in sorted(obdobja, key=lambda o: o["od"], reverse=True):
        if e["datum_iso"] >= o["od"]:
            return o
    return obdobja[-1]


def vrstica(e, n):
    podnaslov = f'<span class="tiho">{escape(e["podnaslov"])}</span>' if e["podnaslov"] else ""
    osebe = " ".join(o["oznaka"] for o in e["osebe"])
    slika = obdobje_za(e, n["obdobja"])["slika"]
    return f"""<li class="vrstica" data-oznaka="{escape(e['oznaka'])}" data-osebe="{escape(osebe)}">
<img class="ikona" src="/slike/{slika}" alt="" width="40" height="40" loading="lazy">
<span class="st">{escape(e['stevilka'])}</span>
<div class="opis"><a href="/{escape(e['oznaka'])}">{escape(e['naslov'])}</a>{podnaslov}</div>
<span class="tiho stevilke">{e['datum']} · {e['trajanje']}</span>
</li>"""


def leta(epizode):
    return sorted({e["leto"] for e in epizode}, reverse=True)


# ---------- strani ----------

def vstopna(n, epizode):
    zadnja = epizode[0]
    gumbi = "".join(f'<a class="gumb" href="{escape(g["url"])}">{escape(g["ime"])}</a>\n' for g in n["narocnina"])
    po_letih = "".join(
        f'<a class="gumb obroba" href="/epizode#leto-{l}">{l}</a>\n' for l in leta(epizode))
    oblacek = f'<p class="oblacek temen">{escape(zadnja["podnaslov"])}</p>' if zadnja["podnaslov"] else ""
    return glava_html("Bitni pogovori", OPIS, "/", n) + f"""<header class="glava-velika">
<div class="ovoj">
<img class="logotip" src="/slike/logotip.svg" alt="Bitni pogovori" width="300" height="228">
<div class="klepet">
<p class="oblacek oranzen">{OPIS}</p>
<p class="oblacek bel">{len(epizode)} epizod. 217 ur. Od 2012 do 2019.</p>
<p class="oblacek temen">Ne snemamo več, arhiv pa ostane tukaj.</p>
<div class="gumbi" id="narocnina">
<a class="gumb oranzen" href="/rss">Naroči se (RSS)</a>
{gumbi}</div>
</div>
</div>
</header>
<main class="ovoj">
<section class="razdelek">
<h2>Zadnja epizoda</h2>
<div class="kartica senca zadnja">
<div class="vrh"><span class="stevilka">{escape(zadnja['stevilka'])}</span><a class="naslov" href="/{escape(zadnja['oznaka'])}">{escape(zadnja['naslov'])}</a></div>
<div class="tiho">{zadnja['datum']} · {zadnja['trajanje']}</div>
{oblacek}
{predvajalnik(n, zadnja)}
</div>
</section>
<section class="razdelek">
<h2>Novejše epizode</h2>
<ul class="seznam">
{chr(10).join(vrstica(e, n) for e in epizode[1:8])}
<li><a class="vec" href="/epizode">Vseh {len(epizode)} epizod, z iskanjem in filtrom po voditeljih in gostih</a></li>
</ul>
</section>
<section class="razdelek">
<h2>Po letih</h2>
<div class="filtri">
{po_letih}</div>
</section>
</main>
""" + noga(n)


def seznam_epizod(n, epizode):
    stevci = {}
    for e in epizode:
        for o in e["osebe"]:
            stevci.setdefault(o["oznaka"], {"ime": o["ime"], "stevilo": 0})["stevilo"] += 1
    po_pogostosti = sorted(stevci.items(), key=lambda par: -par[1]["stevilo"])
    gumb = lambda oz, p: f'<button type="button" class="gumb obroba" data-oseba="{oz}" aria-pressed="false">{escape(p["ime"])} ({p["stevilo"]})</button>'
    pogosti = "\n".join(gumb(oz, p) for oz, p in po_pogostosti[:3])
    gostje = "\n".join(gumb(oz, p) for oz, p in po_pogostosti[3:])
    obdobja = ""
    for leto in leta(epizode):
        njene = [e for e in epizode if e["leto"] == leto]
        obdobja += f"""<section class="razdelek" id="leto-{leto}" data-obdobje>
<h2 class="leto">{leto} <span class="tiho">{len(njene)} epizod</span></h2>
<ul class="seznam">
{chr(10).join(vrstica(e, n) for e in njene)}
</ul>
</section>
"""
    return glava_html("Vse epizode · Bitni pogovori", f"Vseh {len(epizode)} epizod podcasta Bitni pogovori.", "/epizode", n) + glava_mala() + f"""<main class="ovoj" data-seznam-epizod>
<section class="razdelek">
<h1 class="naslov-razdelka"><label for="isci">Vse epizode</label></h1>
<div class="filtri-ovoj razdelek" hidden>
<input id="isci" class="iskanje" type="search" placeholder="Išči po naslovu, opisu in povezavah" autocomplete="off">
<div class="filtri">
{pogosti}
<details>
<summary>Gostje ({len(po_pogostosti) - 3})</summary>
<div class="filtri">
{gostje}
</div>
</details>
</div>
<div class="tiho stevec" role="status"></div>
</div>
</section>
{obdobja}</main>
""" + noga(n)


def stran_epizode(n, e, prejsnja, naslednja):
    voditelji = [o for o in e["osebe"] if o["vloga"] == "host"]
    gostje = [o for o in e["osebe"] if o["vloga"] != "host"]
    povezave = lambda osebe: ", ".join(f'<a href="/epizode?oseba={o["oznaka"]}">{escape(o["ime"])}</a>' for o in osebe)
    ljudje = ""
    if voditelji:
        ljudje += f"<span>Vodita: {povezave(voditelji)}</span>" if len(voditelji) > 1 else f"<span>Vodi: {povezave(voditelji)}</span>"
    if gostje:
        ljudje += f"<span>{'Gostje' if len(gostje) > 1 else 'Gost'}: {povezave(gostje)}</span>"

    poglavja = ""
    if e["poglavja"]:
        with open(os.path.join(KOREN, "izvor", "poglavja", e["poglavja"] + ".json"), encoding="utf-8") as f:
            seznam = json.load(f)["chapters"]
        cas = lambda s: f"{int(s) // 3600}:{int(s) % 3600 // 60:02d}:{int(s) % 60:02d}" if s >= 3600 else f"{int(s) // 60}:{int(s) % 60:02d}"
        vrste = "\n".join(f'<li><a href="?t={int(p["startTime"])}" data-cas="{int(p["startTime"])}"><span class="tiho stevilke">{cas(p["startTime"])}</span>{escape(p["title"])}</a></li>' for p in seznam)
        poglavja = f'<section class="razdelek"><h2 style="font-size: 26px">Poglavja</h2><ul class="poglavja">\n{vrste}\n</ul></section>'

    drugi_viri = ""
    if kopije_so_postavljene(n):
        drugi_viri = '<span class="tiho" style="margin-top: 6px">Ista datoteka, drugi viri:</span>\n' + "\n".join(
            f'<a href="{escape(k["zvok"].format(oznaka=e["oznaka"]))}">{escape(k["ime"])}</a>' for k in n["kopije"].values())
    narocnina = "\n".join(f'<a href="{escape(g["url"])}">{escape(g["ime"])}</a>' for g in n["narocnina"])
    sosednje = ""
    sosednje += f'<a href="/{escape(prejsnja["oznaka"])}">← {escape((prejsnja["stevilka"] + ": ") if prejsnja["stevilka"] else "")}{escape(prejsnja["naslov"])}</a>' if prejsnja else "<span></span>"
    sosednje += f'<a href="/{escape(naslednja["oznaka"])}">{escape((naslednja["stevilka"] + ": ") if naslednja["stevilka"] else "")}{escape(naslednja["naslov"])} →</a>' if naslednja else ""
    opis = e["podnaslov"] or golo_besedilo(e["opombe"])[:160] or OPIS
    stevilka = f'<span class="stevilka">{escape(e["stevilka"])}</span>' if e["stevilka"] else ""

    return glava_html(f"{e['naslov']} · Bitni pogovori", opis, "/" + e["oznaka"], n) + glava_mala("/epizode", "Nazaj na vse epizode") + f"""<main class="ovoj">
<div class="epizoda">
<article>
<div class="naslov-epizode">
<div class="razdelek" style="gap: 6px">
{stevilka}
<h1>{escape(e['naslov'])}</h1>
<span class="tiho"><time datetime="{e['datum_iso']}">{e['datum']}</time> · {e['trajanje']}</span>
</div>
<img class="naslovnica" src="/slike/naslovnica-600.webp" alt="" width="280" height="280">
</div>
<div class="kartica senca">
{predvajalnik(n, e)}
</div>
<div class="opombe">
{e['opombe']}
</div>
{poglavja}
<nav class="sosednje" aria-label="Sosednji epizodi">
{sosednje}
</nav>
</article>
<aside>
<img class="naslovnica" src="/slike/naslovnica-600.webp" alt="" width="280" height="280">
<div class="kartica">
<h2 style="color: var(--sinja)">Epizoda</h2>
{ljudje}
<a class="gumb moder" href="{escape(naslov_zvoka(n, e))}" download>Prenesi MP3 ({e['bajti'] / 1e6:.0f} MB)</a>
{drugi_viri}
</div>
<div class="kartica">
<h2 style="color: var(--oranzna)">Naroči se</h2>
<a href="/rss">RSS</a>
{narocnina}
</div>
</aside>
</div>
</main>
""" + noga(n)


def ni_strani(n):
    return glava_html("Ni te strani · Bitni pogovori", OPIS, "/404", n) + glava_mala() + """<main class="ovoj">
<section class="razdelek">
<h1 class="naslov-razdelka">Te strani ni</h1>
<p class="oblacek">Mogoče se je naslov spremenil. Vse epizode so na <a href="/epizode">seznamu epizod</a>.</p>
</section>
</main>
""" + noga(n)


# ---------- gradnja ----------

def zapisi(pot, vsebina):
    with open(os.path.join(SPLET, pot), "w", encoding="utf-8") as f:
        f.write(vsebina)


def main():
    with open(os.path.join(KOREN, "nastavitve.json"), encoding="utf-8") as f:
        n = json.load(f)
    epizode = preberi_epizode()
    oznake = [e["oznaka"] for e in epizode]
    assert len(set(oznake)) == len(oznake) == 215

    shutil.rmtree(SPLET, ignore_errors=True)
    os.makedirs(SPLET)
    viri = os.path.join(KOREN, "viri")
    shutil.copy(os.path.join(viri, "slog.css"), SPLET)
    shutil.copy(os.path.join(viri, "stran.js"), SPLET)
    shutil.copytree(os.path.join(viri, "slike"), os.path.join(SPLET, "slike"))
    shutil.copytree(os.path.join(viri, "pisave"), os.path.join(SPLET, "pisave"))
    shutil.copytree(os.path.join(KOREN, "izvor", "poglavja"), os.path.join(SPLET, "poglavja"))
    # Naslovnici, na kateri kažejo feedi.
    for ime in ("naslovnica.jpg", "naslovnica-epizoda-1e0b8d16.jpg"):
        shutil.copy(os.path.join(KOREN, "izvor", "slike", ime), os.path.join(SPLET, "slike"))

    zapisi("index.html", vstopna(n, epizode))
    zapisi("epizode.html", seznam_epizod(n, epizode))
    zapisi("404.html", ni_strani(n))
    for i, e in enumerate(epizode):
        starejsa = epizode[i + 1] if i + 1 < len(epizode) else None
        novejsa = epizode[i - 1] if i > 0 else None
        zapisi(e["oznaka"] + ".html", stran_epizode(n, e, starejsa, novejsa))

    # Besedilo opomb za iskanje, brez strešic in z malimi črkami.
    zapisi("iskanje.json", json.dumps({e["oznaka"]: brez_stresic(golo_besedilo(e["opombe"]).lower()) for e in epizode},
                                      ensure_ascii=False, separators=(",", ":")))

    # Stari naslovi s Fireside in preusmeritev zvoka na trenutno kopijo.
    preusmeritve = [
        "/episodes /epizode 301",
        "/hosts/* /epizode 301",
        "/guests /epizode 301",
        "/search /epizode 301",
        "/subscribe /#narocnina 301",
        "/contact / 301",
        "/json /rss 301",
    ]
    if kopije_so_postavljene(n):
        # Vir zvoka se zamenja tukaj: ena vrstica, ki kaže na eno od kopij.
        preusmeritve.append("/audio/:datoteka " + n["kopije"]["r2"]["zvok"].replace("{oznaka}.mp3", ":datoteka") + " 302")
    zapisi("_redirects", "\n".join(preusmeritve) + "\n")
    zapisi("_headers", "/rss\n  Content-Type: application/rss+xml; charset=utf-8\n\n/*\n  tdm-reservation: 1\n\n"
           # Začasni naslov naj ne pride v iskalnike; prava domena lahko.
           + (f"{n['zacasni_naslov']}/*\n  X-Robots-Tag: noindex\n" if n.get("zacasni_naslov") else ""))
    # Pajki za učenje modelov niso dobrodošli; iskalniki in podcast aplikacije so.
    pajki = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "anthropic-ai", "Google-Extended",
             "CCBot", "Bytespider", "meta-externalagent", "FacebookBot", "Applebot-Extended", "PerplexityBot",
             "Amazonbot", "cohere-ai", "Diffbot", "ImagesiftBot", "Omgilibot", "AI2Bot", "Timpibot"]
    zapisi("robots.txt", "# Uporaba posnetkov za učenje sinteze govora ali posnemanje glasov ni dovoljena\n"
           "# brez pisnega soglasja govorcev. Pravice do besedilnega in podatkovnega rudarjenja so pridržane.\n\n"
           + "".join(f"User-agent: {p}\n" for p in pajki) + "Disallow: /\n\nUser-agent: *\nAllow: /\n")
    zapisi(".nojekyll", "")

    zgradi_feede.zgradi_vse()
    print(f"splet/: {len(epizode)} strani epizod, vstopna stran, seznam, feedi")


if __name__ == "__main__":
    main()
