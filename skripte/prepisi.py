#!/usr/bin/env python3
"""Strojni prepis epizod z ločevanjem govorcev. Vse teče lokalno.

Postopek za eno epizodo:
  1. zvok   MP3 iz zvok/ pretvori v 16 kHz mono WAV.
  2. glasovi  razdeli posnetek po glasovih (ECAPA + gručenje; število
              govorcev vzame iz podatkov o epizodi).
  3. imena  gruče poveže z imeni: z glasovnimi vzorci voditeljev, če
            obstajajo, sicer ostanejo »Govorec 1, 2 …«.
  4. prepis  z izbranim modelom: whisper (large-v3, MLX) ali rsdo
             (slovenski Conformer PROTOVERB + model za ločila).
  5. odstavki  besedilo razdeli na odstavke po govorcih s časi.

Vmesni rezultati so v prepisi-preizkus/delo/<oznaka>/ in se ne ponavljajo.
Ta mapa se ne commita: prepisi gredo v javni repozitorij šele po odobritvi.
Glasovni vzorci (biometrični podatki) so samo v ~/.cache/bitni-prepisi/.

Okolje (enkrat):
  uv venv --python 3.11 ~/.cache/bitni-prepisi/.venv
  uv pip install --python ~/.cache/bitni-prepisi/.venv mlx-whisper \
      speechbrain scikit-learn soundfile "nemo_toolkit[asr,nlp]"

Uporaba:
  PY=~/.cache/bitni-prepisi/.venv/bin/python
  $PY skripte/prepisi.py 90 29 --model whisper
  $PY skripte/prepisi.py 90 29 --model rsdo
  $PY skripte/prepisi.py --imena 90 G1="Mark Bizilj" G2="Alan Rener"
  $PY skripte/prepisi.py --vzorci 90        # shrani glasovne vzorce
  $PY skripte/prepisi.py --primerjava       # stran za primerjavo
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from html import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skupno import KOREN  # noqa: E402

ZVOK = os.path.join(KOREN, "zvok")
PREIZKUS = os.path.join(KOREN, "prepisi-preizkus")
DELO = os.path.join(PREIZKUS, "delo")
PREDPOMNILNIK = os.path.expanduser("~/.cache/bitni-prepisi")
VZORCI = os.path.join(PREDPOMNILNIK, "glasovi")
MODELI = os.path.join(PREDPOMNILNIK, "modeli")
WHISPER = os.path.join(os.path.expanduser("~/.cache/bitni-prepisi/modeli"), "whisper-large-v3")  # mlx-community/whisper-large-v3-mlx
SR = 16000

# Okno za glasovne odtise: 1,5 s, vsakih 0,5 s.
OKNO, KORAK = 1.5, 0.5


def podatki_epizode(oznaka):
    import zgradi_stran
    for e in zgradi_stran.preberi_epizode():
        if e["oznaka"] == oznaka:
            return e
    raise SystemExit(f"Epizode {oznaka} ni v feedu.")


def mapa(oznaka):
    pot = os.path.join(DELO, oznaka)
    os.makedirs(pot, exist_ok=True)
    return pot


def beri_json(pot):
    with open(pot, encoding="utf-8") as f:
        return json.load(f)


def pisi_json(pot, podatki):
    """Atomarno: najprej začasna datoteka, nato preimenovanje (varno ob prekinitvi)."""
    zacasna = pot + ".tmp"
    with open(zacasna, "w", encoding="utf-8") as f:
        json.dump(podatki, f, ensure_ascii=False, indent=1)
    os.replace(zacasna, pot)


# ---------- 1. zvok ----------

def wav(oznaka):
    pot = os.path.join(mapa(oznaka), "zvok.wav")
    if not os.path.exists(pot):
        mp3 = os.path.join(ZVOK, f"{oznaka}.mp3")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), pot], check=True)
    return pot


def nalozi_zvok(oznaka):
    import soundfile as sf
    podatki, sr = sf.read(wav(oznaka), dtype="float32")
    assert sr == SR
    return podatki


# ---------- 2. glasovi ----------

def kodirnik():
    from speechbrain.inference.speaker import EncoderClassifier
    return EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb",
                                          savedir=os.path.join(MODELI, "ecapa"))


def glasovi(oznaka, st_govorcev):
    pot = os.path.join(mapa(oznaka), "glasovi.json")
    if os.path.exists(pot):
        return beri_json(pot)
    import numpy as np
    import torch
    from sklearn.cluster import SpectralClustering

    zvok = nalozi_zvok(oznaka)
    dolzina, korak = int(OKNO * SR), int(KORAK * SR)
    zacetki = list(range(0, max(1, len(zvok) - dolzina), korak))
    glasnost = np.array([np.sqrt(np.mean(zvok[z:z + dolzina] ** 2)) for z in zacetki])
    govor = glasnost > 0.25 * np.median(glasnost)

    enc = kodirnik()
    odtisi = []
    izbrani = [z for z, g in zip(zacetki, govor) if g]
    for i in range(0, len(izbrani), 128):
        paket = torch.tensor(np.stack([zvok[z:z + dolzina] for z in izbrani[i:i + 128]]))
        with torch.no_grad():
            odtisi.append(enc.encode_batch(paket).squeeze(1).cpu().numpy())
    odtisi = np.concatenate(odtisi)
    odtisi /= np.linalg.norm(odtisi, axis=1, keepdims=True)

    podobnost = np.clip(odtisi @ odtisi.T, 0, 1)
    # Obdrži samo najmočnejše povezave vsakega okna (zmanjša šum).
    meja = np.percentile(podobnost, 90, axis=1, keepdims=True)
    podobnost = np.where(podobnost >= meja, podobnost, 0)
    podobnost = (podobnost + podobnost.T) / 2
    oznake = SpectralClustering(n_clusters=st_govorcev, affinity="precomputed",
                                random_state=0).fit_predict(podobnost)

    # Gladenje: večina v sosedstvu 5 oken.
    gladke = oznake.copy()
    for i in range(len(oznake)):
        okolica = oznake[max(0, i - 2):i + 3]
        gladke[i] = np.bincount(okolica).argmax()

    # Odseki: zaporedna okna istega glasu.
    casi = [z / SR + OKNO / 2 for z in izbrani]
    odseki = []
    for t, g in zip(casi, gladke):
        g = f"G{g + 1}"
        if odseki and odseki[-1]["g"] == g and t - odseki[-1]["k"] < 1.5:
            odseki[-1]["k"] = t + KORAK / 2
        else:
            odseki.append({"z": round(t - KORAK / 2, 2), "k": round(t + KORAK / 2, 2), "g": g})

    sredisca = {f"G{k + 1}": odtisi[oznake == k].mean(axis=0).tolist() for k in range(st_govorcev)}
    deleži = {f"G{k + 1}": round(float((oznake == k).mean()), 3) for k in range(st_govorcev)}
    rezultat = {"odseki": odseki, "sredisca": sredisca, "delezi": deleži}
    pisi_json(pot, rezultat)
    return rezultat


# ---------- 3. imena ----------

def zdruzene(gl, meja=0.7):
    """Gruče z zelo podobnim glasom so ista oseba (gruč je toliko kot oseb,
    tudi če kdo skoraj ne govori). Vrne preslikavo gruča -> glavna gruča."""
    import numpy as np
    gruce = sorted(gl["sredisca"], key=lambda g: -gl["delezi"][g])
    v = {g: np.array(gl["sredisca"][g]) / np.linalg.norm(gl["sredisca"][g]) for g in gruce}
    glavna = {}
    for g in gruce:
        glavna[g] = next((h for h in gruce if h in glavna and glavna[h] == h and float(v[g] @ v[h]) > meja), g)
    return glavna


def imena(oznaka, e, gl):
    """Poveže gruče z imeni. Ročna izbira (imena.json) ima prednost."""
    rocno = os.path.join(mapa(oznaka), "imena.json")
    glavna = zdruzene(gl)
    izboljsano = os.path.join(mapa(oznaka), "imena-izboljsano.json")
    if not os.path.exists(rocno) and os.path.exists(izboljsano):
        # Izboljšave (prepisi_izboljsave.py --imena) dopolnijo samodejna imena.
        im = {g: v["ime"] for g, v in beri_json(izboljsano).items()}
        gl2 = {**gl, "sredisca": {g: c for g, c in gl["sredisca"].items() if glavna[g] == g}}
        osnovno = _imena(e, gl2)
        return {g: im.get(g, osnovno.get(glavna[g], g)) for g in gl["sredisca"]}
    if os.path.exists(rocno):
        im = beri_json(rocno)
        return {g: im.get(glavna[g], im.get(g, g)) for g in gl["sredisca"]}
    gl = {**gl, "sredisca": {g: s for g, s in gl["sredisca"].items() if glavna[g] == g}}
    preslikava = _imena(e, gl)
    return {g: preslikava[glavna[g]] for g in glavna}


def _imena(e, gl):
    import numpy as np
    osebe = [o["ime"] for o in e["osebe"]]
    vzorci = {}
    for ime in osebe:
        pot = os.path.join(VZORCI, ime + ".npy")
        if os.path.exists(pot):
            vzorci[ime] = np.load(pot)
    preslikava, prosti = {}, [o for o in osebe if o not in vzorci]
    if vzorci:
        from scipy.optimize import linear_sum_assignment
        gruce = list(gl["sredisca"])
        znani = list(vzorci)
        S = np.array([[float(np.dot(gl["sredisca"][g], vzorci[i]) /
                             np.linalg.norm(gl["sredisca"][g]) / np.linalg.norm(vzorci[i]))
                       for i in znani] for g in gruce])
        for a, b in zip(*linear_sum_assignment(-S)):
            if S[a, b] > 0.5:
                preslikava[gruce[a]] = znani[b]
            # Oseba z znanim glasom, ki se ne ujema z nobeno gručo, v epizodi ne govori.
    neznane = [g for g in gl["sredisca"] if g not in preslikava]
    if len(neznane) == 1 and len(prosti) == 1:
        preslikava[neznane[0]] = prosti[0]
    for i, g in enumerate(neznane):
        preslikava.setdefault(g, f"Govorec {i + 1}")
    return preslikava


def shrani_imena(oznaka, pari):
    preslikava = dict(p.split("=", 1) for p in pari)
    pisi_json(os.path.join(mapa(oznaka), "imena.json"), preslikava)
    print(f"{oznaka}: {preslikava}")


def shrani_vzorce(oznaka):
    """Sredisča gruč z ročno potrjenimi imeni postanejo glasovni vzorci."""
    import numpy as np
    os.makedirs(VZORCI, exist_ok=True)
    gl = beri_json(os.path.join(mapa(oznaka), "glasovi.json"))
    for g, ime in beri_json(os.path.join(mapa(oznaka), "imena.json")).items():
        if ime.startswith("Govorec"):
            continue
        pot = os.path.join(VZORCI, ime + ".npy")
        nov = np.array(gl["sredisca"][g])
        if os.path.exists(pot):
            nov = (np.load(pot) + nov) / 2
        np.save(pot, nov)
        print(f"Vzorec: {ime}")


def govorec_ob(odseki, t):
    najblizji, razdalja = odseki[0]["g"], 1e9
    for o in odseki:
        if o["z"] <= t <= o["k"]:
            return o["g"]
        d = min(abs(t - o["z"]), abs(t - o["k"]))
        if d < razdalja:
            najblizji, razdalja = o["g"], d
    return najblizji


# ---------- 4. prepis ----------

def namig(e):
    # Brez seznama imen: Whisper ga je na nejasnih mestih ponovil namesto
    # pravega govora (preizkus 15. 11. 2026: okoli 4 % zvoka izgubljenega).
    return "Bitni pogovori, slovenski podcast o tehnologiji in Applu."


SLOVANSKI = ("sl", "hr", "bs", "sr")  # Whisper slovenščino rad zamenja s sosednjimi jeziki.


def verjetnost_en(model, kos):
    """Verjetnost, da je odsek v angleščini (proti slovenščini in sosednjim jezikom)."""
    from mlx_whisper.audio import N_FRAMES, log_mel_spectrogram, pad_or_trim
    from mlx_whisper.decoding import detect_language
    mel = pad_or_trim(log_mel_spectrogram(kos, n_mels=model.dims.n_mels), N_FRAMES, axis=-2)
    _, verjetnosti = detect_language(model, mel)
    v = verjetnosti[0] if isinstance(verjetnosti, list) else verjetnosti
    en, sl = v.get("en", 0), sum(v.get(j, 0) for j in SLOVANSKI)
    return en / max(en + sl, 1e-9)


def okna(kosi, najvec=28.0):
    """Zaporedne kose (lahko različnih govorcev) združi v okna do 28 s.
    Whisper vsako okno obdela kot 30 s zvoka, zato je manj oken hitreje."""
    skupine = []
    for kos in kosi:
        if skupine and kos[1] - skupine[-1][0][0] <= najvec and kos[0] - skupine[-1][-1][1] < 2.0:
            skupine[-1].append(kos)
        else:
            skupine.append([kos])
    return skupine


def prevladujoci(skupina):
    trajanja = {}
    for z, k, g in skupina:
        trajanja[g] = trajanja.get(g, 0) + k - z
    return max(trajanja, key=trajanja.get)


def prepis_whisper(oznaka, e, gl, varuh=None):
    """Prepis v oknih do 28 s s časi besed; vsaka beseda dobi govorca po času.
    Jezik se določi za vsako okno: angleščina samo ob močnem znaku ali če
    prevladujoči govorec okna sicer govori angleško (gostje iz tujine)."""
    import mlx_whisper
    from mlx_whisper.load_models import load_model
    model = load_model(WHISPER)
    zvok = nalozi_zvok(oznaka)
    namigi = {"sl": namig(e), "en": "A conversation on Bitni pogovori, a tech podcast."}
    skupine = okna(kosi_odsekov(zvok, gl["odseki"], najvec=28.0))
    glavna = zdruzene(gl)

    # 1. krog: jezik. Najprej 12 vzorčnih oken (najdaljša, razpršena po govorcih);
    # če nikjer ni angleščine, je vsa epizoda slovenska in nadaljnja zaznava odpade.
    def p_okna(sk):
        z, k = sk[0][0], sk[-1][1]
        return verjetnost_en(model, zvok[int(z * SR):int(k * SR)]) if k - z >= 3 else None

    po_govorcih = {}
    for i, sk in enumerate(skupine):
        po_govorcih.setdefault(glavna[prevladujoci(sk)], []).append(i)
    vzorec = []
    for indeksi in po_govorcih.values():
        vzorec += sorted(indeksi, key=lambda i: skupine[i][0][0] - skupine[i][-1][1])[:4]
    vzorec = sorted(set(vzorec), key=lambda i: skupine[i][0][0] - skupine[i][-1][1])[:12]
    p_en = [None] * len(skupine)
    for i in vzorec:
        p_en[i] = p_okna(skupine[i])
    if any(p is not None and p > 0.5 for p in p_en):
        for i, sk in enumerate(skupine):
            if i not in vzorec:
                p_en[i] = p_okna(sk)
                if varuh:
                    varuh.pocakaj()
    else:
        p_en = [0.0 if p is None else p for p in p_en]
        p_en = [p if i in vzorec else 0.0 for i, p in enumerate(p_en)]
    delez = {}
    for sk, p in zip(skupine, p_en):
        if p is not None:
            delez.setdefault(glavna[prevladujoci(sk)], []).append(p > 0.5)
    angleski = {g for g, d in delez.items() if len(d) >= 3 and sum(d) / len(d) > 0.5}

    # 2. krog: prepis.
    besede = []
    for sk, p in zip(skupine, p_en):
        z, k = sk[0][0], sk[-1][1]
        g = glavna[prevladujoci(sk)]
        en = (p is not None and p > 0.9) or (g in angleski and (p is None or p > 0.3))
        jezik = "en" if en else "sl"
        kos = zvok[int(z * SR):int(k * SR)]
        r = mlx_whisper.transcribe(kos, path_or_hf_repo=WHISPER, language=jezik,
                                   initial_prompt=namigi[jezik], condition_on_previous_text=False,
                                   word_timestamps=True, temperature=(0.0, 0.2, 0.4))
        # Varovalka: za toliko govora sumljivo malo besedila -> še enkrat brez namiga,
        # obdrži daljšo različico (izgubljen govor je hujša napaka kot odvečna beseda).
        govor = sum(b - a for a, b, _ in sk)
        dolzina = len("".join(s_["text"] for s_ in r["segments"]).strip())
        if govor >= 4 and dolzina / govor < 4:
            r2 = mlx_whisper.transcribe(kos, path_or_hf_repo=WHISPER, language=jezik, initial_prompt=None,
                                        condition_on_previous_text=False, word_timestamps=True,
                                        temperature=(0.0, 0.2, 0.4))
            if len("".join(s_["text"] for s_ in r2["segments"]).strip()) > dolzina * 1.5:
                r = r2
        for seg in r["segments"]:
            for b in seg.get("words", []):
                t0, t1 = z + b["start"], z + b["end"]
                besede.append({"z": t0, "k": t1, "t": b["word"], "j": jezik, "p": b.get("probability", 1.0),
                               "g": glavna[govorec_ob(gl["odseki"], (t0 + t1) / 2)]})
        if varuh:
            varuh.pocakaj()
    return v_odstavke(besede)


class Varuh:
    """Drži temperaturo okoli ciljne: če procesor ali grafika preseže mejo,
    počaka, da se ohladi. Temperaturo bere macmon (brez gesla)."""

    def __init__(self, meja=70.0, histereza=4.0):
        import threading
        self.meja, self.histereza, self.temp = meja, histereza, 0.0
        self.cakanje = 0.0
        threading.Thread(target=self._beri, daemon=True).start()

    def _beri(self):
        while True:
            try:
                p = subprocess.Popen(["macmon", "pipe", "-i", "2000"], stdout=subprocess.PIPE, text=True)
                for vrstica in p.stdout:
                    t = json.loads(vrstica)["temp"]
                    self.temp = max(t["cpu_temp_avg"], t["gpu_temp_avg"])
            except Exception:
                self.temp = 0.0
            time.sleep(5)

    def pocakaj(self):
        """Sorazmeren premor: 3 s za vsako stopinjo nad mejo, največ 20 s.
        Temperatura se tako ustali okoli meje, grafika pa dela večino časa."""
        cez = self.temp - self.meja
        if cez > 0:
            premor = min(20.0, 3.0 * cez)
            time.sleep(premor)
            self.cakanje += premor


def kosi_odsekov(zvok, odseki, najvec=20.0):
    """Odseke enega glasu razreže na kose do 20 s, rez je na najtišjem mestu."""
    import numpy as np
    kosi = []
    for o in odseki:
        z, k = o["z"], o["k"]
        while k - z > najvec:
            od, do = int((z + 12) * SR), int((z + najvec) * SR)
            okvir = int(0.1 * SR)
            energija = [np.sum(zvok[i:i + okvir] ** 2) for i in range(od, do, okvir)]
            rez = z + 12 + 0.1 * int(np.argmin(energija)) + 0.05
            kosi.append((z, rez, o["g"]))
            z = rez
        if k - z > 0.3:
            kosi.append((z, k, o["g"]))
    return kosi


def razpakiraj(ime, datoteka):
    cilj = os.path.join(MODELI, ime)
    if not os.path.isdir(cilj):
        os.makedirs(cilj)
        subprocess.run(["tar", "--zstd", "-xf", os.path.join(MODELI, datoteka), "-C", cilj], check=True)
    for koren, _, datoteke in os.walk(cilj):
        for d in datoteke:
            if d.endswith(".nemo"):
                return os.path.join(koren, d)
    raise SystemExit(f"V {cilj} ni datoteke .nemo")


def prepis_rsdo(oznaka, e, gl):
    import soundfile as sf
    import tempfile
    from nemo.collections.asr.models import ASRModel

    zvok = nalozi_zvok(oznaka)
    kosi = kosi_odsekov(zvok, gl["odseki"])
    asr = ASRModel.restore_from(razpakiraj("protoverb", "protoverb.tar.zst"), map_location="cpu")
    asr.eval()
    with tempfile.TemporaryDirectory() as tmp:
        poti = []
        for i, (z, k, _) in enumerate(kosi):
            p = os.path.join(tmp, f"{i:05d}.wav")
            sf.write(p, zvok[int(z * SR):int(k * SR)], SR)
            poti.append(p)
        izhod = asr.transcribe(poti, batch_size=16)
    if isinstance(izhod, tuple):
        izhod = izhod[0]
    # Model označi premore in šume s posebnimi znaki; v prepisu jih ne želimo.
    besedila = [" ".join((h.text if hasattr(h, "text") else str(h)).replace("▩", " ").replace("▲", " ").split())
                for h in izhod]

    # Zaporedne kose istega govorca združi, šele nato doda ločila.
    odstavki = []
    for (z, k, g), t in zip(kosi, besedila):
        if not t.strip():
            continue
        if odstavki and odstavki[-1]["g"] == g and len(odstavki[-1]["t"]) < 1200:
            odstavki[-1]["k"] = k
            odstavki[-1]["t"] += " " + t.strip()
        else:
            odstavki.append({"z": z, "k": k, "g": g, "t": t.strip()})
    del asr
    locila = Locila()
    for o in odstavki:
        o["t"] = locila(o["t"])
        o["z"], o["k"] = round(o["z"], 2), round(o["k"], 2)
    return odstavki


class Locila:
    """Model RSDO-DS2-P&C 3.6 (SloBERTa) naložen brez NeMo, ki za NLP
    potrebuje Megatron. Za vsako besedo napove ločilo za njo in veliko črko."""

    LOCILA = ["", "!", ",", ".", "?"]

    def __init__(self):
        import glob
        import torch
        from transformers import CamembertConfig, CamembertModel, CamembertTokenizer
        razpakiraj("locila", "pc.tar.zst")
        mapa_x = os.path.join(MODELI, "locila", "v3.6", "x")
        if not os.path.isdir(mapa_x):
            os.makedirs(mapa_x)
            subprocess.run(["tar", "-xf", os.path.join(MODELI, "locila", "v3.6", "nlp_tc_pc.nemo"), "-C", mapa_x], check=True)
        self.tok = CamembertTokenizer(glob.glob(os.path.join(mapa_x, "*sentencepiece.bpe.model"))[0])
        sd = torch.load(os.path.join(mapa_x, "model_weights.ckpt"), map_location="cpu")
        cfg = CamembertConfig(vocab_size=sd["bert_model.embeddings.word_embeddings.weight"].shape[0],
                              max_position_embeddings=514, type_vocab_size=1)
        self.bert = CamembertModel(cfg, add_pooling_layer=False)
        self.bert.load_state_dict({k[len("bert_model."):]: v for k, v in sd.items()
                                   if k.startswith("bert_model.") and "position_ids" not in k}, strict=False)
        self.bert.eval()
        self.p = torch.nn.Linear(768, 5)
        self.p.load_state_dict({"weight": sd["punct_classifier.mlp.layer0.weight"],
                                "bias": sd["punct_classifier.mlp.layer0.bias"]})
        self.c = torch.nn.Linear(768, 2)
        self.c.load_state_dict({"weight": sd["capit_classifier.mlp.layer0.weight"],
                                "bias": sd["capit_classifier.mlp.layer0.bias"]})
        self.torch = torch

    def __call__(self, besedilo, okno=150):
        besede = besedilo.lower().split()
        izhod = []
        for i in range(0, len(besede), okno):
            izhod += self._okno(besede[i:i + okno])
        if izhod:
            izhod[0] = izhod[0][:1].upper() + izhod[0][1:]
            if izhod[-1][-1] not in ".?!":
                izhod[-1] += "."
        return " ".join(izhod)

    def _okno(self, besede):
        ids, prvi = [self.tok.cls_token_id], []
        for b in besede:
            deli = self.tok.encode(b, add_special_tokens=False) or [self.tok.unk_token_id]
            prvi.append(len(ids))
            ids += deli
        ids.append(self.tok.sep_token_id)
        with self.torch.no_grad():
            h = self.bert(input_ids=self.torch.tensor([ids])).last_hidden_state[0]
            p = self.p(h).argmax(-1).tolist()
            c = self.c(h).argmax(-1).tolist()
        rezultat = []
        for b, j in zip(besede, prvi):
            if c[j] == 1:
                b = b[:1].upper() + b[1:]
            rezultat.append(b + self.LOCILA[p[j]])
        # Velika začetnica po koncu stavka.
        for k in range(1, len(rezultat)):
            if rezultat[k - 1][-1] in ".?!":
                rezultat[k] = rezultat[k][:1].upper() + rezultat[k][1:]
        return rezultat


# ---------- 5. odstavki ----------

def v_odstavke(besede, najdaljsi=60.0):
    odstavki = []
    for b in besede:
        zadnji = odstavki[-1] if odstavki else None
        konec_stavka = zadnji and zadnji["t"].rstrip().endswith((".", "?", "!"))
        if zadnji and zadnji["g"] == b["g"] and zadnji.get("j") == b.get("j") \
                and not (konec_stavka and b["z"] - zadnji["z"] > najdaljsi):
            zadnji["t"] += b["t"]
            zadnji["k"] = b["k"]
            zadnji["_p"].append(b.get("p", 1.0))
        else:
            odstavki.append({"z": b["z"], "k": b["k"], "g": b["g"], "j": b.get("j", "sl"), "t": b["t"],
                             "_p": [b.get("p", 1.0)]})
    for o in odstavki:
        o["t"] = o["t"].strip()
        o["z"], o["k"] = round(o["z"], 2), round(o["k"], 2)
        # Zanesljivost: povprečna verjetnost besed (0–1); nizka pomeni dvomljiv del.
        o["p"] = round(sum(o["_p"]) / len(o["_p"]), 2)
        del o["_p"]
    return [o for o in odstavki if o["t"]]


IZMISLJENO = {"thank you.", "thanks for watching!", "thanks for watching.", "thank you for watching.", "hvala.", "hvala za ogled.", "hvala lepa.",
              "hvala, da ste pripravljeni.", "hvala, da ste", "thank you for joining us."}


def _zanke(t):
    """Poišče zanke: enota 1–8 besed, ponovljena zapored (ena beseda vsaj 6-krat,
    daljša vsaj 3-krat). Vrne seznam (začetek, n, ponovitev) v besedah."""
    w = t.split()
    k = [re.sub(r"[^\w]", "", x.lower()) for x in w]
    najdene, i = [], 0
    while i < len(w):
        najboljsa = None
        for n in range(1, 9):
            if not any(k[i:i + n]):
                continue
            r = 1
            while k[i + r * n:i + (r + 1) * n] == k[i:i + n]:
                r += 1
            if r >= (6 if n == 1 else 3) and (najboljsa is None or r * n > najboljsa[1] * najboljsa[2]):
                najboljsa = (i, n, r)
        if najboljsa:
            najdene.append(najboljsa)
            i += najboljsa[1] * najboljsa[2]
        else:
            i += 1
    return najdene


def zanka(t):
    return bool(_zanke(t))


def brez_zank(t):
    """Whisper se včasih zacikla (»ne, ne, ne, …« 50-krat, isti stavek 20-krat).
    Zanko skrajša na dve ponovitvi (eno besedo na tri), kar je še lahko pravi govor."""
    zanke = _zanke(t)
    if not zanke:
        return t
    w, izhod, i = t.split(), [], 0
    for z, n, r in zanke:
        izhod += w[i:z] + w[z:z + n * (3 if n == 1 else 2)]
        i = z + n * r
    return " ".join(izhod + w[i:])


def brez_izmisljenega(odstavki, e):
    """Whisper na tišini ali glasbi rad ponovi namig ali napiše »Thank you.«.
    Odstrani stavke, ki so del namiga, in znane izmišljene fraze."""
    import re
    from difflib import SequenceMatcher
    imena = {o["ime"].lower() for o in e["osebe"]}
    ocisceni = []
    for o in odstavki:
        stavki = re.split(r"(?<=[.!?])\s+", o["t"])
        ostanek = []
        for s in stavki:
            mali = s.strip().lower()
            deli = [d.strip(" .,") for d in mali.split(",") if d.strip(" .,")]
            podobna_imenom = sum(1 for d in deli
                                 if max((SequenceMatcher(None, d, i).ratio() for i in imena), default=0) > 0.7)
            if mali in IZMISLJENO or not re.search(r"\w", mali) or (len(deli) > 1 and podobna_imenom >= len(deli) - (1 if len(deli) >= 3 else 0)):
                continue
            if "bitni pogovori, " in mali and ("podcast" in mali):
                continue
            if mali.startswith(("pogovarjajo se", "speakers:")):
                continue
            if len(deli) == 1 and len(mali) < 40 and \
                    max((SequenceMatcher(None, deli[0], i).ratio() for i in imena), default=0) > 0.85:
                continue
            ostanek.append(s)
        t = brez_zank(" ".join(ostanek).strip())
        if t:
            ocisceni.append({**o, "t": t})
    return ocisceni


def obdelaj(oznaka, model, varuh=None):
    e = podatki_epizode(oznaka)
    pot = os.path.join(mapa(oznaka), f"{model}.json")
    if os.path.exists(pot):
        print(f"{oznaka} {model}: že narejeno")
        return
    zacetek = time.time()
    gl = glasovi(oznaka, max(2, len(e["osebe"])))
    print(f"{oznaka}: glasovi {time.time() - zacetek:.0f} s, deleži {gl['delezi']}")
    t = time.time()
    if model == "whisper":
        odstavki = prepis_whisper(oznaka, e, gl, varuh)
    else:
        odstavki = prepis_rsdo(oznaka, e, gl)
    odstavki = brez_izmisljenega(odstavki, e)
    trajalo = time.time() - t
    dolzina = os.path.getsize(wav(oznaka)) / 2 / SR
    pisi_json(pot, {"oznaka": oznaka, "model": model, "sekund_zvoka": round(dolzina),
                    "sekund_obdelave": round(trajalo), "sekund_hlajenja": round(varuh.cakanje) if varuh else 0,
                    "odstavki": odstavki})
    if varuh:
        varuh.cakanje = 0.0
    print(f"{oznaka} {model}: {len(odstavki)} odstavkov, {trajalo:.0f} s za {dolzina / 60:.0f} min zvoka "
          f"({dolzina / trajalo:.1f}× hitreje od realnega časa)")


# ---------- stran za primerjavo ----------

def cas(s):
    s = int(s)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


STIL = """
body{font:16px/1.5 -apple-system,system-ui,sans-serif;margin:0;background:#0f1b2d;color:#e8eef6}
header{position:sticky;top:0;background:#0f1b2d;padding:12px 16px;border-bottom:1px solid #2a3b55;z-index:1}
h1{font-size:18px;margin:0 0 8px} audio{width:100%} input{width:100%;padding:6px;margin-top:8px;font:inherit;
background:#182a44;color:inherit;border:1px solid #2a3b55;border-radius:4px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;padding:16px}
@media(max-width:800px){main{grid-template-columns:1fr}}
h2{font-size:15px;color:#8fb3dd;margin:0 0 8px}
p{margin:0 0 10px;padding:6px 8px;border-radius:4px;cursor:pointer}
p:hover{background:#182a44} p.zdaj{background:#21406b}
.g{font-weight:600;color:#ff8a24;margin-right:6px} .c{color:#7d93b0;font-size:13px;margin-right:6px}
mark{background:#ffd54a;color:#000} p.dvom .t{color:#b9a27a;border-bottom:1px dotted #b9a27a} .skrij{display:none} a{color:#8fb3dd}
"""

SKRIPTA = """
const a=document.querySelector('audio'),ps=[...document.querySelectorAll('p[data-z]')];
ps.forEach(p=>p.onclick=()=>{a.currentTime=+p.dataset.z;a.play()});
a.ontimeupdate=()=>{const t=a.currentTime;ps.forEach(p=>{const on=t>=+p.dataset.z&&t<+p.dataset.k;
 if(on&&!p.classList.contains('zdaj')&&document.getElementById('sledi').checked)p.scrollIntoView({block:'center',behavior:'smooth'});
 p.classList.toggle('zdaj',on)})};
const q=document.querySelector('input[type=search]');
ps.forEach(p=>p.dataset.html=p.innerHTML);
q.oninput=()=>{const s=q.value.trim().toLowerCase();ps.forEach(p=>{p.innerHTML=p.dataset.html;
 const besedilo=p.querySelector('.t');if(!s){p.classList.remove('skrij');return}
 const ok=besedilo.textContent.toLowerCase().includes(s);p.classList.toggle('skrij',!ok);
 if(ok)besedilo.innerHTML=besedilo.textContent.replace(new RegExp(s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&'),'gi'),m=>'<mark>'+m+'</mark>')})};
const h=location.hash.match(/t=(\\d+)/);if(h)a.currentTime=+h[1];
"""


DVOM = ' class="dvom" title="nizka zanesljivost"'


def z_imeni(odstavki, im, najvec=1200):
    """Doda imena in združi zaporedne odstavke iste osebe v istem jeziku."""
    izhod = []
    for o in odstavki:
        ime = im.get(o["g"], o["g"])
        z = izhod[-1] if izhod else None
        if z and z["ime"] == ime and z.get("j") == o.get("j") and o["z"] - z["k"] < 3 and len(z["t"]) < najvec:
            n = len(z["t"]), len(o["t"])
            z["p"] = round((z.get("p", 1) * n[0] + o.get("p", 1) * n[1]) / max(1, sum(n)), 2)
            z["t"] += " " + o["t"]
            z["k"] = o["k"]
        else:
            izhod.append({**o, "ime": ime})
    return izhod


def primerjava():
    oznake = sorted(d for d in os.listdir(DELO) if os.path.isdir(os.path.join(DELO, d)))
    vrstice = []
    for oznaka in oznake:
        e = podatki_epizode(oznaka)
        stolpci = []
        for model in ("whisper", "rsdo", "whisper-kosi"):
            pot = os.path.join(DELO, oznaka, f"{model}.json")
            if not os.path.exists(pot):
                continue
            p = beri_json(pot)
            p["odstavki"] = brez_izmisljenega(p["odstavki"], e)
            gl =beri_json(os.path.join(DELO, oznaka, "glasovi.json"))
            im = imena(oznaka, e, gl)
            hitrost = p["sekund_zvoka"] / max(1, p["sekund_obdelave"])
            odst = "\n".join(
                f'<p data-z="{o["z"]}" data-k="{o["k"]}"{" lang=en" if o.get("j") == "en" else ""}'
                f'{DVOM if o.get("p", 1) < 0.6 else ""}>'
                f'<span class="c">{cas(o["z"])}{" · EN" if o.get("j") == "en" else ""}</span>'
                f'<span class="g">{escape(o["ime"])}</span><span class="t">{escape(o["t"])}</span></p>'
                for o in z_imeni(p["odstavki"], im))
            stolpci.append(f'<section><h2>{model} · {hitrost:.1f}× realni čas · {len(p["odstavki"])} odstavkov</h2>{odst}</section>')
        stran = f"""<!doctype html><html lang="sl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Prepis {escape(oznaka)}</title>
<style>{STIL}</style><header><h1><a href="index.html">←</a> {escape(oznaka)}: {escape(e['naslov'])}</h1>
<audio controls preload="metadata" src="../zvok/{escape(oznaka)}.mp3"></audio>
<input type="search" placeholder="Išči po prepisu …">
<label><input type="checkbox" id="sledi" checked style="width:auto"> sledi predvajanju</label></header>
<main>{''.join(stolpci)}</main><script>{SKRIPTA}</script></html>"""
        with open(os.path.join(PREIZKUS, f"{oznaka}.html"), "w", encoding="utf-8") as f:
            f.write(stran)
        vrstice.append(f'<li><a href="{escape(oznaka)}.html">{escape(oznaka)}: {escape(e["naslov"])}</a></li>')
    with open(os.path.join(PREIZKUS, "index.html"), "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><meta charset="utf-8"><title>Preizkus prepisov</title><style>{STIL}'
                f'body{{padding:16px}}</style><h1>Preizkus prepisov</h1><ul>{"".join(vrstice)}</ul>')
    print(os.path.join(PREIZKUS, "index.html"))


def vse(model, meja, prednost):
    """Nočni način: vse epizode po vrsti, napaka pri eni ne ustavi ostalih."""
    import traceback
    import zgradi_stran
    varuh = Varuh(meja)
    vse_oznake = [e["oznaka"] for e in reversed(zgradi_stran.preberi_epizode())]
    vrsta = prednost + [o for o in vse_oznake if o not in prednost]
    for oznaka in vrsta:
        if not os.path.exists(os.path.join(ZVOK, f"{oznaka}.mp3")):
            continue
        if os.path.exists(os.path.join(DELO, oznaka, f"{model}.json")):
            continue
        try:
            obdelaj(oznaka, model, varuh)
            os.remove(wav(oznaka))  # 115 MB na uro; ponovno nastane iz MP3, če je treba
        except Exception:
            print(f"NAPAKA {oznaka}:\n{traceback.format_exc()}")
        sys.stdout.flush()
    print("KONEC")


def vsi_glasovi(meja):
    """Ločevanje govorcev za vse epizode vnaprej (procesor, nizka prednost)."""
    import traceback
    import zgradi_stran
    os.nice(15)
    varuh = Varuh(meja)
    for e in reversed(zgradi_stran.preberi_epizode()):
        oznaka = e["oznaka"]
        if os.path.exists(os.path.join(DELO, oznaka, "glasovi.json")) or \
                not os.path.exists(os.path.join(ZVOK, f"{oznaka}.mp3")):
            continue
        varuh.pocakaj()
        try:
            glasovi(oznaka, max(2, len(e["osebe"])))
            print(f"{oznaka}: glasovi")
        except Exception:
            print(f"NAPAKA {oznaka}:\n{traceback.format_exc()}")
        sys.stdout.flush()
    print("KONEC")


def gostje(meja_podobnosti=0.6):
    """Glasovne vzorce razširi na goste. Začne z ročno potrjenimi (imena.json);
    nato v krogih: kjer v epizodi ostane ena neznana gruča in ena oseba brez
    vzorca, je to ta oseba. Vsak novi vzorec pomaga v naslednjem krogu.
    Rezultat so vzorci v ~/.cache/bitni-prepisi/glasovi/ (samo lokalno)."""
    import numpy as np
    import zgradi_stran
    epizode = {e["oznaka"]: e for e in zgradi_stran.preberi_epizode()}
    gl_vse = {}
    for oznaka in epizode:
        pot = os.path.join(DELO, oznaka, "glasovi.json")
        if os.path.exists(pot):
            gl = beri_json(pot)
            glavna = zdruzene(gl)
            gl_vse[oznaka] = {g: np.array(c) / np.linalg.norm(c) for g, c in gl["sredisca"].items()
                              if glavna[g] == g and gl["delezi"][g] >= 0.03}
    vsote, stevci, viri = {}, {}, {}

    def dodaj(ime, vektor, oznaka):
        vsote[ime] = vsote.get(ime, 0) + vektor
        stevci[ime] = stevci.get(ime, 0) + 1
        viri.setdefault(ime, []).append(oznaka)

    for oznaka in gl_vse:
        rocno = os.path.join(DELO, oznaka, "imena.json")
        if os.path.exists(rocno):
            for g, ime in beri_json(rocno).items():
                if g in gl_vse[oznaka] and not ime.startswith("Govorec"):
                    dodaj(ime, gl_vse[oznaka][g], oznaka)
    dodeljeno = {o: {} for o in gl_vse}
    for krog in range(10):
        novi = 0
        vzorci = {i: v / np.linalg.norm(v) for i, v in vsote.items()}
        for oznaka, gruce in gl_vse.items():
            osebe = [o["ime"] for o in epizode[oznaka]["osebe"]]
            znani = [i for i in osebe if i in vzorci]
            # Najboljša dodelitev znanih oseb gručam.
            from scipy.optimize import linear_sum_assignment
            imena_gruc = list(gruce)
            zasedene, preslikava = set(), {}
            if znani and imena_gruc:
                S = np.array([[float(gruce[g] @ vzorci[i]) for i in znani] for g in imena_gruc])
                for a, b in zip(*linear_sum_assignment(-S)):
                    if S[a, b] > meja_podobnosti:
                        preslikava[imena_gruc[a]] = znani[b]
            prosti_g = [g for g in imena_gruc if g not in preslikava]
            prosti_o = [i for i in osebe if i not in preslikava.values() and i not in vzorci]
            if len(prosti_g) == 1 and len(prosti_o) == 1 and prosti_o[0] not in dodeljeno[oznaka].values():
                ime = prosti_o[0]
                dodaj(ime, gruce[prosti_g[0]], oznaka)
                dodeljeno[oznaka][prosti_g[0]] = ime
                novi += 1
        print(f"krog {krog + 1}: {novi} novih dodelitev")
        if not novi:
            break
    os.makedirs(VZORCI, exist_ok=True)
    for ime, v in vsote.items():
        np.save(os.path.join(VZORCI, ime + ".npy"), v / stevci[ime])
    pisi_json(os.path.join(VZORCI, "viri.json"), viri)
    for ime in sorted(stevci, key=lambda i: -stevci[i]):
        print(f"{stevci[ime]:4d}  {ime}")


def izvozi():
    """Končni prepisi v prepisi/<oznaka>.json: z imeni, brez izmišljenih stavkov,
    zaporedni odstavki iste osebe združeni. Iz teh datotek se gradi stran."""
    import datetime
    cilj = os.path.join(KOREN, "prepisi")
    os.makedirs(cilj, exist_ok=True)
    st = 0
    for oznaka in sorted(os.listdir(DELO)):
        pot = os.path.join(DELO, oznaka, "whisper.json")
        if not os.path.exists(pot):
            continue
        e = podatki_epizode(oznaka)
        p = beri_json(pot)
        gl = beri_json(os.path.join(DELO, oznaka, "glasovi.json"))
        surovi = p["odstavki"]
        # Izboljšave dvomljivih delov (prepisi_izboljsave.py --dvomljivi), pred filtrom.
        izb = os.path.join(DELO, oznaka, "izboljsave.json")
        if os.path.exists(izb):
            nova = {x["z"]: x for x in beri_json(izb) if x["izbrana"] != "izvirnik"}
            surovi = [{**o, "t": nova[o["z"]]["novo"], "p": max(h["p"] for h in nova[o["z"]]["hipoteze"]
                                                              if h["t"] == nova[o["z"]]["novo"]), "izb": 1}
                      if o["z"] in nova else o for o in surovi]
            surovi = [o for o in surovi if o["t"].strip()]
        odstavki = z_imeni(brez_izmisljenega(surovi, e), imena(oznaka, e, gl))
        for o in odstavki:
            o.pop("g", None)
            if o.get("j") == "sl":
                del o["j"]
        pisi_json(os.path.join(cilj, f"{oznaka}.json"), {
            "oznaka": oznaka, "model": "whisper-large-v3 (MLX), ločevanje govorcev ECAPA",
            "nastalo": datetime.date.fromtimestamp(os.path.getmtime(pot)).isoformat(),
            "odstavki": odstavki})
        st += 1
    print(f"prepisi/: {st} epizod")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oznake", nargs="*")
    ap.add_argument("--model", choices=["whisper", "rsdo"])
    ap.add_argument("--imena", action="store_true", help="prva oznaka, nato G1=Ime …")
    ap.add_argument("--vzorci", action="store_true")
    ap.add_argument("--primerjava", action="store_true")
    ap.add_argument("--vse", action="store_true", help="vse epizode (nočni način)")
    ap.add_argument("--glasovi", action="store_true", help="samo ločevanje govorcev za vse epizode")
    ap.add_argument("--gostje", action="store_true", help="razširi glasovne vzorce na goste")
    ap.add_argument("--izvozi", action="store_true", help="končni prepisi v prepisi/")
    ap.add_argument("--meja", type=float, default=70.0, help="ciljna temperatura v °C")
    a = ap.parse_args()
    if a.imena:
        shrani_imena(a.oznake[0], a.oznake[1:])
    elif a.vzorci:
        for o in a.oznake:
            shrani_vzorce(o)
    elif a.primerjava:
        primerjava()
    elif a.izvozi:
        izvozi()
    elif a.gostje:
        gostje()
    elif a.glasovi:
        vsi_glasovi(a.meja)
    elif a.vse:
        vse(a.model or "whisper", a.meja, a.oznake)
    else:
        for o in a.oznake:
            obdelaj(o, a.model)


if __name__ == "__main__":
    main()
