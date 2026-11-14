#!/usr/bin/env python3
"""Lokalni predogled strani: python3 skripte/predogled.py, nato http://localhost:8000

Druga mapa (npr. predogled s prepisi): python3 skripte/predogled.py 8001 prepisi-preizkus/splet

Tako kot Cloudflare Pages in GitHub Pages postreže /210 iz datoteke 210.html.
"""

import http.server
import os
import sys

from skupno import KOREN

SPLET = os.path.join(KOREN, "splet")


class Streznik(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SPLET, **kwargs)

    def send_head(self):
        pot = self.path.split("?")[0].split("#")[0]
        if not os.path.exists(os.path.join(SPLET, pot.lstrip("/"))) and os.path.exists(os.path.join(SPLET, pot.lstrip("/") + ".html")):
            self.path = pot + ".html"
        return super().send_head()


if __name__ == "__main__":
    vrata = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    if len(sys.argv) > 2:
        SPLET = os.path.abspath(sys.argv[2])
    print(f"http://localhost:{vrata}")
    http.server.ThreadingHTTPServer(("127.0.0.1", vrata), Streznik).serve_forever()
