"""Skupne funkcije za skripte arhiva Bitnih pogovorov."""

import os
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(KOREN, "izvor", "feed-2026-11-14.xml")
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
# Splošno ime odjemalca, brez osebnih podatkov.
ODJEMALEC = "bitni-arhiv-backup/1.0"


def epizode(pot=FEED):
    """Vrne seznam epizod iz shranjenega feeda, od najstarejše do najnovejše."""
    kanal = ET.parse(pot).getroot().find("channel")
    seznam = []
    for item in kanal.findall("item"):
        zvok = item.find("enclosure")
        povezava = item.findtext("link") or ""
        seznam.append(
            {
                "oznaka": povezava.rstrip("/").rsplit("/", 1)[-1],
                "guid": item.findtext("guid"),
                "naslov": item.findtext("title"),
                "datum": parsedate_to_datetime(item.findtext("pubDate")).date().isoformat(),
                "trajanje": item.findtext(ITUNES + "duration") or "",
                "bajti_feed": int(zvok.get("length") or 0),
                "url": zvok.get("url"),
            }
        )
    seznam.reverse()
    return seznam
