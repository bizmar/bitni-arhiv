#!/usr/bin/env python3
"""Lokalni predogled strani: python3 skripte/predogled.py, nato http://localhost:8000

Druga mapa (npr. predogled s prepisi): python3 skripte/predogled.py 8001 prepisi-preizkus/splet

Tako kot Cloudflare Pages in GitHub Pages postreže /210 iz datoteke 210.html.
"""

import http.server
import json
import os
import re
import sys

from skupno import KOREN

SPLET = os.path.join(KOREN, "splet")


class Streznik(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SPLET, **kwargs)

    def preusmeritev(self, pot):
        """Pravila iz _redirects (kot Cloudflare): /pot/:ime, /pot/* in točne poti."""
        dat = os.path.join(SPLET, "_redirects")
        if not os.path.exists(dat):
            return None
        for vrstica in open(dat):
            d = vrstica.split()
            if len(d) < 2 or d[0].startswith("#"):
                continue
            vzorec = "^" + re.sub(r":(\w+)", r"(?P<\1>[^/]+)", re.escape(d[0]).replace(r"\:", ":")).replace(r"\*", "(?P<splat>.*)") + "$"
            m = re.match(vzorec, pot)
            if m:
                cilj = d[1]
                for k, v in m.groupdict().items():
                    cilj = cilj.replace(":" + k, v)
                return cilj, int(d[2]) if len(d) > 2 else 301
        return None

    def send_head(self):
        pot = self.path.split("?")[0].split("#")[0]
        if not os.path.exists(os.path.join(SPLET, pot.lstrip("/"))):
            p = self.preusmeritev(pot)
            if p:
                self.send_response(p[1])
                self.send_header("Location", p[0])
                self.end_headers()
                return None
        if not os.path.exists(os.path.join(SPLET, pot.lstrip("/"))) and os.path.exists(os.path.join(SPLET, pot.lstrip("/") + ".html")):
            self.path = pot + ".html"
        return super().send_head()

    # Odgovori lastnika na poročilo o popravkih prepisov (/popravki):
    # GET in POST /odgovori/<oznaka> bere in piše
    # prepisi-preizkus/delo/<oznaka>/popravki-lastnik.json. Samo lokalno.
    def _odgovori(self):
        m = re.fullmatch(r"/odgovori/([\w-]+)", self.path)
        delo = os.path.join(KOREN, "prepisi-preizkus", "delo")
        if not m or not os.path.isdir(os.path.join(delo, m.group(1))):
            return None
        return os.path.join(delo, m.group(1), "popravki-lastnik.json")

    def _poslji(self, koda, telo=b"{}"):
        self.send_response(koda)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(telo)))
        self.end_headers()
        self.wfile.write(telo)

    def do_GET(self):
        if self.path.startswith("/odgovori/"):
            pot = self._odgovori()
            if not pot:
                return self._poslji(404)
            return self._poslji(200, open(pot, "rb").read() if os.path.exists(pot) else b"{}")
        return super().do_GET()

    def do_POST(self):
        pot = self._odgovori()
        if not pot:
            return self._poslji(404)
        podatki = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with open(pot + ".tmp", "w") as f:
            json.dump(podatki, f, ensure_ascii=False, indent=1)
        os.replace(pot + ".tmp", pot)
        self._poslji(200)


if __name__ == "__main__":
    vrata = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    if len(sys.argv) > 2:
        SPLET = os.path.abspath(sys.argv[2])
    print(f"http://localhost:{vrata}")
    http.server.ThreadingHTTPServer(("127.0.0.1", vrata), Streznik).serve_forever()
