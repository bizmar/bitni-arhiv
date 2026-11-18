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
            if (p["z"], p["staro"]) in {(x["z"], x["staro"]) for x in neuporabljeni}:
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
        if (p["z"], p["staro"]) in {(x["z"], x["staro"]) for x in neuporabljeni}:
            razred += " ni"
        dod = " <span class=zn>povsod</span>" if p.get("povsod") else ""
        kljuc = esc(f'{p["z"]}|{p["staro"]}')
        vr.append(f'<tr class="{razred}" data-k="{kljuc}"><td><a href="/{oznaka}?t={p["z"]}">{mmss(float(p["z"]))}</a></td>'
                  f'<td><del>{esc(p["staro"])}</del> → <ins>{esc(p["novo"])}</ins>{dod}'
                  f'<div class=raz>{esc(p.get("razlog", ""))}</div></td>'
                  f'<td class=odl><button type=button class=ne title="Napačen popravek, pusti izvirnik">✗</button>'
                  f'<input class=drugo placeholder="pravilno je …"></td></tr>')
    pot = os.path.join(P.DELO, oznaka, "popravki-negotovo.json")
    neg = P.beri_json(pot) if os.path.exists(pot) else []
    nv = "".join(f'<li data-n="{i}"><a href="/{oznaka}?t={n["z"]}">{mmss(float(n["z"]))}</a> {esc(n["opis"])}'
                 f'<div class=vnos><input class=staro placeholder="napačno (kot v prepisu)">'
                 f' → <input class=novo placeholder="pravilno"></div></li>'
                 for i, n in enumerate(neg))
    srednjih = sum(p.get("gotovost") != "visoka" for p in popravki)
    moji = [x for x in neuporabljeni if x.get("lastnik")]
    opozorilo = ("<p class=ni>Teh tvojih popravkov ni bilo mogoče najti v prepisu (preveri, da je napačni del "
                 "prepisan točno, in čas): " + "; ".join(f"{mmss(float(x['z']))} »{esc(x['staro'])}«" for x in moji)
                 + "</p>") if moji else ""
    return (f'<section data-o="{esc(oznaka)}"><h2>{esc(str(e.get("stevilka") or oznaka))}: {esc(e["naslov"])}'
            f' <span class=stanje></span></h2>'
            f'<p>{len(popravki)} popravkov, od tega {srednjih} srednje gotovih (rumeno).</p>' + opozorilo
            + (f'<h3>Preveri na uho</h3><ul class=negotovo>{nv}</ul>' if nv else "")
            + '<h3>Moji popravki</h3><table class=dodatni></table>'
              '<button type=button class=dodaj>+ dodaj popravek</button>'
            + f'<h3>Popravki podagenta</h3><table class=agent>{"".join(vr)}</table></section>')


HTML = """<!doctype html><html lang=sl><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Popravki prepisov</title>
<style>
body{{font:16px/1.5 -apple-system,system-ui,sans-serif;max-width:62rem;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}}
h1{{color:#0e8ef0}} h2{{border-top:1px solid #ddd;padding-top:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}} td{{padding:.3rem .4rem;border-bottom:1px solid #eee;vertical-align:top}}
td:first-child{{white-space:nowrap}} del{{color:#b33}} ins{{color:#171;text-decoration:none;font-weight:600}}
.raz{{color:#777;font-size:.8rem}} td.odl{{white-space:nowrap;width:15rem}}
tr.srednja{{background:#fff6d6}} tr.ni,p.ni{{background:#fdd}} .zn{{font-size:.75rem;background:#e6f2fe;padding:0 .3rem;border-radius:3px}}
tr.zavrnjen ins{{text-decoration:line-through;color:#999}} tr.zavrnjen button.ne{{background:#c33;color:#fff;border-color:#c33}}
tr.drugace ins{{text-decoration:line-through;color:#999}}
button{{font:inherit;border:1px solid #bbb;background:#f4f4f4;border-radius:4px;padding:0 .5rem;cursor:pointer}}
input{{font:inherit;font-size:.85rem;padding:.1rem .3rem;border:1px solid #ccc;border-radius:3px;width:11rem}}
.negotovo li{{margin-bottom:.5rem}} .vnos{{margin-top:.15rem}}
.stanje{{font-size:.8rem;font-weight:normal;color:#171}} a{{color:#0e8ef0}}
@media (prefers-color-scheme:dark){{body{{background:#14171c;color:#ddd}} td{{border-color:#2a2f37}}
tr.srednja{{background:#3a3418}} tr.ni{{background:#4a1f1f}} del{{color:#f88}} ins{{color:#7d7}} .zn{{background:#1d3550}}
button{{background:#252a31;color:#ddd;border-color:#444}} input{{background:#1c2026;color:#ddd;border-color:#444}} .stanje{{color:#7d7}}}}
</style>
<h1>Popravki prepisov s podagenti</h1>
<p>Preizkus na {st} epizodah: {skupaj} popravljenih izrazov in imen. Čas odpre epizodo na tem mestu.
Vse se shrani samo od sebe (lokalno, v <code>delo/&lt;oznaka&gt;/popravki-lastnik.json</code>).</p>
<ul>
<li><b>Popravki podagenta:</b> nič ne naredi, če je prav. ✗ = napačen, ostane izvirnik.
Če je pravilno nekaj tretjega, vpiši v polje »pravilno je …«.</li>
<li><b>Preveri na uho:</b> če je treba popraviti, vpiši napačni del, kot je v prepisu, in pravilno besedilo. Sicer pusti prazno.</li>
<li><b>Moji popravki:</b> karkoli drugega opaziš: čas (npr. 12:34), napačno, pravilno.</li>
</ul>
{vsebina}
<script>
document.querySelectorAll("section[data-o]").forEach(function (sec) {{
  var o = sec.dataset.o, stanje = sec.querySelector(".stanje"), cakam = null;
  function cas(t) {{ var d = t.trim().split(":").map(Number); return d.reduce(function (a, b) {{ return a * 60 + b; }}, 0); }}
  function mmss(s) {{ s = Math.round(s); var h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, x = s % 60;
    return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0"); }}
  function vrstica(d) {{
    var tr = document.createElement("tr");
    tr.innerHTML = '<td><input class=cas placeholder="mm:ss" style="width:5rem"></td><td><input class=staro placeholder="napačno (kot v prepisu)" style="width:100%"></td>' +
      '<td><input class=novo placeholder="pravilno" style="width:100%"></td><td><button type=button class=brisi>✕</button></td>';
    if (d) {{ tr.querySelector(".cas").value = mmss(d.z); tr.querySelector(".staro").value = d.staro; tr.querySelector(".novo").value = d.novo; }}
    tr.querySelector(".brisi").onclick = function () {{ tr.remove(); shrani(); }};
    sec.querySelector(".dodatni").appendChild(tr);
    return tr;
  }}
  function zberi() {{
    var s = {{popravki: {{}}, negotovo: {{}}, dodatni: []}};
    sec.querySelectorAll("tr[data-k]").forEach(function (tr) {{
      var ne = tr.classList.contains("zavrnjen"), dr = tr.querySelector(".drugo").value.trim();
      tr.classList.toggle("drugace", !!dr && !ne);
      if (ne) s.popravki[tr.dataset.k] = {{ne: true}}; else if (dr) s.popravki[tr.dataset.k] = {{novo: dr}};
    }});
    sec.querySelectorAll("li[data-n]").forEach(function (li) {{
      var st = li.querySelector(".staro").value.trim(), nv = li.querySelector(".novo").value.trim();
      if (st) s.negotovo[li.dataset.n] = {{staro: st, novo: nv}};
    }});
    sec.querySelectorAll(".dodatni tr").forEach(function (tr) {{
      var c = tr.querySelector(".cas").value, st = tr.querySelector(".staro").value.trim();
      if (c && st) s.dodatni.push({{z: cas(c), staro: st, novo: tr.querySelector(".novo").value.trim()}});
    }});
    return s;
  }}
  function shrani() {{
    clearTimeout(cakam); stanje.textContent = "…";
    cakam = setTimeout(function () {{
      fetch("/odgovori/" + o, {{method: "POST", body: JSON.stringify(zberi())}})
        .then(function (r) {{ stanje.textContent = r.ok ? "shranjeno" : "napaka pri shranjevanju"; }})
        .catch(function () {{ stanje.textContent = "napaka: strežnik predogleda ne teče"; }});
    }}, 500);
  }}
  sec.querySelectorAll("button.ne").forEach(function (b) {{ b.onclick = function () {{ b.closest("tr").classList.toggle("zavrnjen"); shrani(); }}; }});
  sec.querySelector(".dodaj").onclick = function () {{ vrstica().querySelector(".cas").focus(); }};
  sec.addEventListener("input", shrani);
  fetch("/odgovori/" + o).then(function (r) {{ return r.json(); }}).then(function (s) {{
    Object.keys(s.popravki || {{}}).forEach(function (k) {{
      var tr = Array.prototype.find.call(sec.querySelectorAll("tr[data-k]"), function (t) {{ return t.dataset.k === k; }});
      if (!tr) return;
      if (s.popravki[k].ne) tr.classList.add("zavrnjen");
      if (s.popravki[k].novo) {{ tr.querySelector(".drugo").value = s.popravki[k].novo; tr.classList.add("drugace"); }}
    }});
    Object.keys(s.negotovo || {{}}).forEach(function (n) {{
      var li = sec.querySelector('li[data-n="' + n + '"]');
      if (li) {{ li.querySelector(".staro").value = s.negotovo[n].staro; li.querySelector(".novo").value = s.negotovo[n].novo; }}
    }});
    (s.dodatni || []).forEach(vrstica);
  }}).catch(function () {{}});
}});
</script>
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
