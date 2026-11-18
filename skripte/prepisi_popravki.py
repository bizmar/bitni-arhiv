#!/usr/bin/env python3
"""Popravki napačno prepoznanih izrazov in imen s podagenti (Claude Code).

Postopek:
  1. --pripravi 100 17 …  za vsako epizodo zapiše vhod za podagenta:
     prepisi-preizkus/popravki-vhod/<oznaka>.txt (podatki iz feeda in prepis
     z vrsticami »[mm:ss | z=…] Ime: besedilo«) in kopijo izvoženega prepisa.
  2. Podagent (Sonnet, high) prebere vhod in zapiše
     prepisi-preizkus/delo/<oznaka>/popravki.json: seznam
     {"z", "staro", "novo", "razlog", "gotovost", "povsod"?}.
  3. --preveri 100 17 …  preveri, ali se vsak popravek da uporabiti, in izpiše
     poročilo (prepisi-preizkus/popravki-porocilo.md).
  4. prepisi.py --izvozi popravke uporabi v prepisi/.

Vse ostane lokalno (prepisi-preizkus/ je v .gitignore).
"""

import argparse
import copy
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepisi as P  # noqa: E402

VHOD = os.path.join(P.PREIZKUS, "popravki-vhod")


def besedilo_opomb(h):
    h = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", h or "", flags=re.S)
    h = re.sub(r"<li[^>]*>", "- ", h)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"\n\s*\n+", "\n", html.unescape(h)).strip()


def mmss(s):
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def pripravi(oznaka):
    e = P.podatki_epizode(oznaka)
    pr = P.beri_json(os.path.join(P.KOREN, "prepisi", f"{oznaka}.json"))
    os.makedirs(VHOD, exist_ok=True)
    P.pisi_json(os.path.join(VHOD, f"{oznaka}.json"), pr)
    osebe = ", ".join(f"{o['ime']} ({o['vloga']})" for o in (e.get("osebe") or []))
    vrstice = [
        f"Epizoda {e.get('stevilka') or oznaka}: {e['naslov']}",
        f"Datum: {e['datum']}",
        f"Osebe v feedu: {osebe}",
        "",
        "Opombe iz feeda:",
        besedilo_opomb(e.get("opombe")),
        "",
        "Prepis:",
    ]
    for o in pr["odstavki"]:
        vrstice.append(f"[{mmss(o['z'])} | z={o['z']}] {o['ime']}: {o['t']}")
    pot = os.path.join(VHOD, f"{oznaka}.txt")
    with open(pot, "w") as f:
        f.write("\n".join(vrstice) + "\n")
    print(f"{pot}: {len(pr['odstavki'])} odstavkov")


def preveri(oznake):
    vrstice = ["# Popravki izrazov in imen (podagenti)", ""]
    skupaj = 0
    deli = []
    for oznaka in oznake:
        pot = os.path.join(P.DELO, oznaka, "popravki.json")
        if not os.path.exists(pot):
            vrstice += [f"## {oznaka}", "", "Ni popravkov.", ""]
            continue
        popravki = P.beri_json(pot)
        odstavki = copy.deepcopy(P.beri_json(os.path.join(VHOD, f"{oznaka}.json"))["odstavki"])
        neuporabljeni = P.uporabi_popravke(oznaka, odstavki, izpis=False)
        e = P.podatki_epizode(oznaka)
        vrstice += [f"## {e.get('stevilka') or oznaka}: {e['naslov']}", "",
                    f"{len(popravki)} popravkov, neuporabljenih {len(neuporabljeni)}.", ""]
        for p in sorted(popravki, key=lambda p: float(p["z"])):
            oznake_p = []
            if p in neuporabljeni:
                oznake_p.append("NI UPORABLJEN")
            if p.get("gotovost") != "visoka":
                oznake_p.append(f"preveri ({p.get('gotovost', '?')})")
            if p.get("povsod"):
                oznake_p.append("povsod")
            dodatek = f" **[{', '.join(oznake_p)}]**" if oznake_p else ""
            vrstice.append(f"- {mmss(float(p['z']))} »{p['staro']}« → »{p['novo']}«: {p.get('razlog', '')}{dodatek}")
        vrstice.append("")
        skupaj += len(popravki) - len(neuporabljeni)
        deli.append(html_epizode(oznaka, e, popravki, neuporabljeni))
    vrstice.insert(2, f"Uporabljenih popravkov skupaj: {skupaj}.\n")
    izhod = os.path.join(P.PREIZKUS, "popravki-porocilo.md")
    with open(izhod, "w") as f:
        f.write("\n".join(vrstice))
    print(izhod)
    stran = os.path.join(P.PREIZKUS, "splet", "popravki.html")
    with open(stran, "w") as f:
        f.write(HTML.format(skupaj=skupaj, st=len(oznake), vsebina="\n".join(deli)))
    print(stran, "(predogled: /popravki)")


def html_epizode(oznaka, e, popravki, neuporabljeni):
    esc = html.escape
    vr = []
    for p in sorted(popravki, key=lambda p: float(p["z"])):
        razred = "srednja" if p.get("gotovost") != "visoka" else ""
        if p in neuporabljeni:
            razred += " ni"
        dod = " <span class=zn>povsod</span>" if p.get("povsod") else ""
        vr.append(f'<tr class="{razred}"><td><a href="/{oznaka}?t={p["z"]}">{mmss(float(p["z"]))}</a></td>'
                  f'<td><del>{esc(p["staro"])}</del> → <ins>{esc(p["novo"])}</ins>{dod}</td>'
                  f'<td>{esc(p.get("razlog", ""))}</td></tr>')
    pot = os.path.join(P.DELO, oznaka, "popravki-negotovo.json")
    neg = P.beri_json(pot) if os.path.exists(pot) else []
    nv = "".join(f'<li><a href="/{oznaka}?t={n["z"]}">{mmss(float(n["z"]))}</a> {esc(n["opis"])}</li>'
                 for n in sorted(neg, key=lambda n: float(n["z"])))
    srednjih = sum(p.get("gotovost") != "visoka" for p in popravki)
    return (f'<h2>{esc(str(e.get("stevilka") or oznaka))}: {esc(e["naslov"])}</h2>'
            f'<p>{len(popravki)} popravkov, od tega {srednjih} srednje gotovih (rumeno).</p>'
            + (f'<h3>Preveri na uho</h3><ul>{nv}</ul>' if nv else "")
            + f'<details><summary>Vsi popravki</summary><table>{"".join(vr)}</table></details>')


HTML = """<!doctype html><html lang=sl><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Popravki prepisov</title>
<style>
body{{font:16px/1.5 -apple-system,system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}}
h1{{color:#0e8ef0}} h2{{border-top:1px solid #ddd;padding-top:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}} td{{padding:.25rem .4rem;border-bottom:1px solid #eee;vertical-align:top}}
td:first-child{{white-space:nowrap}} del{{color:#b33}} ins{{color:#171;text-decoration:none;font-weight:600}}
tr.srednja{{background:#fff6d6}} tr.ni{{background:#fdd}} .zn{{font-size:.75rem;background:#e6f2fe;padding:0 .3rem;border-radius:3px}}
summary{{cursor:pointer;color:#0e8ef0}} a{{color:#0e8ef0}}
@media (prefers-color-scheme:dark){{body{{background:#14171c;color:#ddd}} td{{border-color:#2a2f37}}
tr.srednja{{background:#3a3418}} tr.ni{{background:#4a1f1f}} del{{color:#f88}} ins{{color:#7d7}} .zn{{background:#1d3550}}}}
</style>
<h1>Popravki prepisov s podagenti</h1>
<p>Preizkus na {st} epizodah: {skupaj} popravljenih izrazov in imen. Čas odpre epizodo na tem mestu
(stran predogleda, zvok se predvaja od tam). Najprej poslušaj mesta pod »Preveri na uho«, nato rumene vrstice.</p>
{vsebina}
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oznake", nargs="+")
    ap.add_argument("--pripravi", action="store_true")
    ap.add_argument("--preveri", action="store_true")
    a = ap.parse_args()
    if a.pripravi:
        for o in a.oznake:
            pripravi(o)
    if a.preveri:
        preveri(a.oznake)


if __name__ == "__main__":
    main()
