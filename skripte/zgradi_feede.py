#!/usr/bin/env python3
"""Iz originalnega feeda zgradi nove feede: glavnega in po enega za vsako kopijo.

Vse, kar aplikacije uporabljajo za prepoznavo epizod (guid, datum, naslov,
velikost), ostane nespremenjeno. Spremenijo se samo naslovi zvoka, slik in
poglavij ter oznake, vezane na Fireside.

Uporaba:  python3 skripte/zgradi_feede.py
Rezultat: izhod/rss, izhod/rss-r2.xml, izhod/rss-ia.xml, izhod/rss-github.xml
"""

import copy
import json
import os
import xml.etree.ElementTree as ET

from skupno import FEED, KOREN

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PODCAST = "https://podcastindex.org/namespace/1.0"
FIRESIDE = "https://fireside.fm/modules/rss/fireside"
IZHOD = os.path.join(KOREN, "izhod")


def preberi_z_imenskimi_prostori(pot):
    """Prebere XML in ohrani predpone (itunes:, podcast: ...), kot so v izvirniku."""
    for _, (predpona, naslov) in ET.iterparse(pot, events=["start-ns"]):
        ET.register_namespace(predpona, naslov)
    return ET.parse(pot)


def oznaka_epizode(item):
    return (item.findtext("link") or "").rstrip("/").rsplit("/", 1)[-1]


def odstrani(stars, pogoj):
    for otrok in list(stars):
        if pogoj(otrok):
            stars.remove(otrok)


def slika(nastavitve, stari_naslov):
    """Naslov naslovnice na novi domeni. Ena epizoda ima svojo naslovnico."""
    if "/episodes/" in stari_naslov:
        oznaka = stari_naslov.split("/")[-2][:8]
        return f"{nastavitve['domena']}/slike/naslovnica-epizoda-{oznaka}.jpg"
    return f"{nastavitve['domena']}/slike/naslovnica.jpg"


def zgradi(drevo, nastavitve, kopija):
    """kopija je None za glavni feed ali ključ iz nastavitve['kopije']."""
    koren = copy.deepcopy(drevo.getroot())
    kanal = koren.find("channel")
    glavni = kopija is None
    naslov_feeda = nastavitve["glavni_feed"] if glavni else f"{nastavitve['domena']}/rss-{kopija}.xml"
    vzorec = nastavitve["zvok_glavni"] if glavni else nastavitve["kopije"][kopija]["zvok"]

    # Oznake, vezane na Fireside, in stvari, ki jih nova stran ne ponuja.
    je_fireside = lambda e: e.tag.startswith("{" + FIRESIDE + "}")
    odstrani(kanal, je_fireside)
    # Fireside piše imenski prostor Atom s poševnico na koncu, zato primerjamo ohlapno.
    je_atom_link = lambda e: e.tag.endswith("}link") and "/Atom" in e.tag
    odstrani(kanal, lambda e: je_atom_link(e) and e.get("rel") == "hub")
    odstrani(kanal, lambda e: e.tag == f"{{{PODCAST}}}podping")
    lastnik = kanal.find(f"{{{ITUNES}}}owner")
    if lastnik is not None:
        odstrani(lastnik, lambda e: e.tag == f"{{{ITUNES}}}email")

    kanal.find("generator").text = "bitni-arhiv (https://github.com/bizmar/bitni-arhiv)"
    for povezava in kanal:
        if je_atom_link(povezava) and povezava.get("rel") == "self":
            povezava.set("href", naslov_feeda)
    naslovnica = kanal.find(f"{{{ITUNES}}}image")
    naslovnica.set("href", slika(nastavitve, naslovnica.get("href")))

    # Apple po tej oznaki ve, da je feed preseljen.
    nov = ET.Element(f"{{{ITUNES}}}new-feed-url")
    nov.text = nastavitve["glavni_feed"]
    nov.tail = naslovnica.tail
    kanal.insert(list(kanal).index(naslovnica) + 1, nov)

    for item in kanal.findall("item"):
        oznaka = oznaka_epizode(item)
        odstrani(item, je_fireside)
        # <author> v RSS zahteva e-naslov; ime ostane v itunes:author.
        odstrani(item, lambda e: e.tag == "author")
        zvok = item.find("enclosure")
        zvok.set("url", vzorec.format(oznaka=oznaka))
        s = item.find(f"{{{ITUNES}}}image")
        if s is not None:
            s.set("href", slika(nastavitve, s.get("href")))
        poglavja = item.find(f"{{{PODCAST}}}chapters")
        if poglavja is not None:
            ime = poglavja.get("url").rstrip("/").split("/")[-2]
            poglavja.set("url", f"{nastavitve['domena']}/poglavja/{ime}.json")
        if glavni:
            # Aplikacije, ki to podpirajo, lahko same izberejo drug vir.
            for k in nastavitve["kopije"].values():
                alt = ET.SubElement(item, f"{{{PODCAST}}}alternateEnclosure")
                alt.set("type", zvok.get("type"))
                alt.set("length", zvok.get("length"))
                alt.set("title", k["ime"])
                ET.SubElement(alt, f"{{{PODCAST}}}source").set("uri", k["zvok"].format(oznaka=oznaka))
                alt.tail = "\n    "
    return koren


def preveri(izvirnik, nov):
    """Kar aplikacije uporabljajo za prepoznavo epizod, se ne sme spremeniti."""
    stari = izvirnik.getroot().find("channel").findall("item")
    novi = nov.find("channel").findall("item")
    assert len(stari) == len(novi) == 215, (len(stari), len(novi))
    for a, b in zip(stari, novi):
        for polje in ("guid", "title", "pubDate", "link"):
            assert a.findtext(polje) == b.findtext(polje), (polje, a.findtext("guid"))
        za, zb = a.find("enclosure"), b.find("enclosure")
        assert za.get("length") == zb.get("length") and za.get("type") == zb.get("type")
        assert "fireside" not in zb.get("url")
    kanal = nov.find("channel")
    glava = "".join(ET.tostring(e, encoding="unicode") for e in kanal if e.tag != "item")
    assert "fireside" not in glava, "v glavi feeda je ostal naslov Fireside"
    naslovi = [b.find("enclosure").get("url") for b in novi]
    assert len(set(naslovi)) == len(naslovi), "dve epizodi kažeta na isto datoteko"


def main():
    with open(os.path.join(KOREN, "nastavitve.json"), encoding="utf-8") as f:
        nastavitve = json.load(f)
    drevo = preberi_z_imenskimi_prostori(FEED)
    os.makedirs(IZHOD, exist_ok=True)
    for kopija in [None] + list(nastavitve["kopije"]):
        nov = zgradi(drevo, nastavitve, kopija)
        preveri(drevo, nov)
        ime = "rss" if kopija is None else f"rss-{kopija}.xml"
        ET.ElementTree(nov).write(os.path.join(IZHOD, ime), encoding="utf-8", xml_declaration=True)
        print(f"izhod/{ime}: {len(nov.find('channel').findall('item'))} epizod, preverjeno")


if __name__ == "__main__":
    main()
