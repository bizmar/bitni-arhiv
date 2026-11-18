#!/usr/bin/env python3
"""Govorci po stavkih: natančnejša delitev prepisa med osebe.

Prvotno ločevanje govorcev (prepisi.py, okna 1,5 s z glajenjem) kratke
vmesne odzive pripiše tistemu, ki govori okoli njih, meje med govorci pa so
včasih za stavek ali dva zamaknjene. Ta korak besedila ne spreminja:
  1. obstoječe besedilo (z izboljšavami) Whisper poravna z zvokom in dobi
     čase stavkov (forced alignment, brez novega prepisa);
  2. vsak stavek, dolg vsaj MIN_S sekund in MIN_BESED besed, dobi glasovni
     odtis ECAPA in se primerja z glasovi oseb v epizodi; govorca zamenja
     samo ob jasni razliki (MEJA). Krajši odzivi (»ja«, »aha«) ostanejo
     pri okoliškem govorcu;
  3. rezultat je delo/<oznaka>/stavki.json; prepisi.py --izvozi ga uporabi.

Uporaba:
  PY=~/.cache/bitni-prepisi/.venv/bin/python
  $PY skripte/govorci_stavki.py 100        # izračuna in pokaže spremembe
"""

import hashlib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepisi as P  # noqa: E402

MIN_S, MIN_BESED, MEJA = 1.2, 3, 0.06


def odtis(odstavki):
    return hashlib.sha1(json.dumps([(o["z"], o["g"], o["t"]) for o in odstavki],
                                   ensure_ascii=False).encode()).hexdigest()[:16]


def stavki_odstavka(t):
    return [s for s in re.split(r"(?<=[.!?…])\s+", t.strip()) if s]


class Poravnava:
    def __init__(self):
        from mlx_whisper.load_models import load_model
        from mlx_whisper.tokenizer import get_tokenizer
        self.model = load_model(P.WHISPER)
        self.tok = {j: get_tokenizer(True, num_languages=self.model.num_languages, language=j, task="transcribe")
                    for j in ("sl", "en")}

    def __call__(self, zvok, a, b, stavki, jezik):
        """Vrne [(z, k)] za vsak stavek (absolutni časi) ali None."""
        import mlx.core as mx
        from mlx_whisper.audio import HOP_LENGTH, N_FRAMES, log_mel_spectrogram, pad_or_trim
        from mlx_whisper.timing import find_alignment
        tok = self.tok.get(jezik, self.tok["sl"])
        tokeni, meje = [], []
        for s in stavki:
            t = tok.encode(" " + s)
            meje.append((len(tokeni), len(tokeni) + len(t)))
            tokeni += t
        if not tokeni or len(tokeni) > 440:
            return None
        kos = zvok[int(a * P.SR):int(b * P.SR)]
        mel = log_mel_spectrogram(mx.array(kos), n_mels=self.model.dims.n_mels)
        okvirjev = min(mel.shape[0], N_FRAMES)
        mel = pad_or_trim(mel, N_FRAMES, axis=-2).astype(mx.float16)
        besede = find_alignment(self.model, tok, tokeni, mel, okvirjev)
        # Beseda pripada stavku, v katerem je njen prvi token.
        casi, i = [], 0
        for z0, k0 in meje:
            v = []
            while i < len(besede):
                st = sum(len(x.tokens) for x in besede[:i])
                if st >= k0:
                    break
                v.append(besede[i])
                i += 1
            casi.append((a + float(v[0].start), a + float(v[-1].end)) if v else None)
        return casi


def poravnaj(oznaka, odstavki, zvok):
    por = Poravnava()
    izhod = []
    for n, o in enumerate(odstavki):
        st = stavki_odstavka(o["t"])
        dolz = [len(s) + 1 for s in st]
        trajanje = max(0.5, o["k"] - o["z"])
        ocena = []
        x = 0
        for d in dolz:
            ocena.append((o["z"] + trajanje * x / sum(dolz), o["z"] + trajanje * (x + d) / sum(dolz)))
            x += d
        kazalec, i = max(0.0, o["z"] - 0.3), 0
        while i < len(st):
            j = i
            while j + 1 < len(st) and ocena[j + 1][1] - kazalec <= 24:
                j += 1
            konec = o["k"] + 0.7 if j == len(st) - 1 else ocena[j][1] + 2.5
            b = min(kazalec + 29.5, max(konec, kazalec + 1.0))
            casi = por(zvok, kazalec, b, st[i:j + 1], o.get("j", "sl")) or [None] * (j + 1 - i)
            for s, c, oc in zip(st[i:j + 1], casi, ocena[i:j + 1]):
                z, k = c if c else oc
                izhod.append({"z": round(z, 2), "k": round(max(k, z + 0.1), 2), "t": s, "g0": o["g"],
                              "j": o.get("j", "sl"), "p": o.get("p", 1), "o": n, "izb": o.get("izb", 0)})
            zadnji = next((c for c in reversed(casi) if c), None)
            kazalec = max(kazalec + 1.0, zadnji[1] - 0.1) if zadnji else ocena[j][1]
            i = j + 1
        if n % 50 == 0:
            print(f"  poravnava {n}/{len(odstavki)}", flush=True)
    return izhod


def zdruzeni(stavki):
    """Stavek, ki ga je prvotna delitev presekala (del brez končnega ločila,
    naslednji del pri drugem govorcu takoj za njim), spet združi v enega;
    prvotni govorec je tisti z več besedila."""
    izhod = []
    for s in stavki:
        z = izhod[-1] if izhod else None
        if z and not z["t"].rstrip().endswith((".", "?", "!", "…")) and s["o"] != z["o_zadnji"] \
                and s["z"] - z["k"] < 1.0 and z["j"] == s["j"]:
            dolz = z["_d"]
            dolz[s["g0"]] = dolz.get(s["g0"], 0) + len(s["t"])
            z["g0"] = max(dolz, key=dolz.get)
            n = len(z["t"]), len(s["t"])
            z["p"] = round((z["p"] * n[0] + s["p"] * n[1]) / sum(n), 2)
            z["t"] += " " + s["t"]
            z["k"] = max(z["k"], s["k"])
            z["o_zadnji"] = s["o"]
            z["izb"] = max(z["izb"], s["izb"])
        else:
            izhod.append({**s, "o_zadnji": s["o"], "_d": {s["g0"]: len(s["t"])}})
    for s in izhod:
        del s["_d"], s["o_zadnji"]
    return izhod


def dolocene(stavki, zvok):
    import numpy as np
    import torch
    enc = P.kodirnik()
    odt = {}
    for i, s in enumerate(stavki):
        if s["k"] - s["z"] < 0.8:
            continue
        kos = zvok[int(s["z"] * P.SR):int(s["k"] * P.SR)]
        with torch.no_grad():
            v = enc.encode_batch(torch.tensor(kos)[None]).squeeze().cpu().numpy()
        odt[i] = v / np.linalg.norm(v)
    oznake = {i: s["g0"] for i, s in enumerate(stavki)}
    for _ in range(2):
        sred = {}
        for g in set(s["g0"] for s in stavki):
            vz = [odt[i] for i in odt if oznake[i] == g and stavki[i]["k"] - stavki[i]["z"] >= 2.5]
            if len(vz) >= 5:
                c = np.mean(vz, axis=0)
                sred[g] = c / np.linalg.norm(c)
        for i, s in enumerate(stavki):
            if i not in odt or s["g0"] not in sred:
                continue
            if s["k"] - s["z"] < MIN_S or len(s["t"].split()) < MIN_BESED:
                continue
            pod = {g: float(odt[i] @ c) for g, c in sred.items()}
            naj = max(pod, key=pod.get)
            oznake[i] = naj if naj != s["g0"] and pod[naj] - pod[s["g0"]] > MEJA else s["g0"]
            s["pod"] = {g: round(v, 3) for g, v in pod.items()}
    for i, s in enumerate(stavki):
        s["g"] = oznake[i]
    return stavki


def v_odstavke(stavki, najdaljsi=60.0):
    """Zaporedni stavki istega govorca in jezika v odstavke (kot prepisi.v_odstavke)."""
    izhod = []
    for s in stavki:
        z = izhod[-1] if izhod else None
        if z and z["g"] == s["g"] and z["j"] == s["j"] and s["z"] - z["z"] <= najdaljsi:
            n = len(z["t"]), len(s["t"])
            z["p"] = round((z["p"] * n[0] + s["p"] * n[1]) / sum(n), 2)
            z["t"] += " " + s["t"]
            z["k"] = max(z["k"], s["k"])
            z["izb"] = max(z.get("izb", 0), s.get("izb", 0))
        else:
            izhod.append({"z": s["z"], "k": s["k"], "g": s["g"], "j": s["j"], "t": s["t"], "p": s["p"],
                          "izb": s.get("izb", 0)})
    for o in izhod:
        if not o["izb"]:
            del o["izb"]
    return izhod


def primerjava(oznaka, stavki, im):
    mmss = P.cas
    vr = []
    for s in stavki:
        if s["g"] != s["g0"]:
            vr.append(f'<tr><td><a href="/{oznaka}?t={s["z"]}">{mmss(s["z"])}</a></td>'
                      f'<td>{html.escape(im.get(s["g0"], s["g0"]))} → <b>{html.escape(im.get(s["g"], s["g"]))}</b></td>'
                      f'<td>{html.escape(s["t"])}</td></tr>')
    pot = os.path.join(P.PREIZKUS, "splet", f"govorci-{oznaka}.html")
    with open(pot, "w") as f:
        f.write(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Govorci {oznaka}</title><style>body{{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#222;background:#fff}}
td{{padding:.3rem .4rem;border-bottom:1px solid #eee;vertical-align:top}} td:first-child,td:nth-child(2){{white-space:nowrap}} a{{color:#0e8ef0}}
@media (prefers-color-scheme:dark){{body{{background:#14171c;color:#ddd}} td{{border-color:#2a2f37}}}}</style>
<h1>Epizoda {oznaka}: zamenjani govorci</h1>
<p>{len(vr)} od {len(stavki)} stavkov je dobilo drugega govorca. Čas odpre epizodo na tem mestu.</p>
<table>{''.join(vr)}</table>""")
    return pot


def main():
    for oznaka in sys.argv[1:]:
        e = P.podatki_epizode(oznaka)
        odstavki = P.ocisceni(oznaka, e)
        zvok = P.nalozi_zvok(oznaka)
        print(f"{oznaka}: {len(odstavki)} odstavkov, poravnava …", flush=True)
        stavki = dolocene(zdruzeni(poravnaj(oznaka, odstavki, zvok)), zvok)
        P.pisi_json(os.path.join(P.DELO, oznaka, "stavki.json"), {"izvor": odtis(odstavki), "stavki": stavki})
        gl = P.beri_json(os.path.join(P.DELO, oznaka, "glasovi.json"))
        im = P.imena(oznaka, e, gl)
        sprem = sum(s["g"] != s["g0"] for s in stavki)
        print(f"{oznaka}: {len(stavki)} stavkov, govorec zamenjan pri {sprem}; {primerjava(oznaka, stavki, im)}")


if __name__ == "__main__":
    main()
