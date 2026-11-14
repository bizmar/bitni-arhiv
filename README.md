# Bitni pogovori: arhiv

Selitev arhiva podcasta Bitni pogovori (215 epizod, 2012–2019) s Fireside na
brezplačno statično gostovanje. Feed, domena in povezave do epizod ostanejo
isti. Zvok bo na treh neodvisnih mestih.

## Stanje

- [ ] 1. Varnostna kopija vsega s Fireside
  - [x] feed, slike, poglavja, nekaj strani (mapa `izvor/`)
  - [ ] preverjene povezave do vseh MP3 (`epizode.csv`, preverjanje teče počasi)
  - [ ] lokalna kopija zvoka (`skripte/prenesi_zvok.py`)
  - [ ] statistika poslušanja (potrebuje API ključ lastnika računa, ni nujno)
- [ ] 2. Oblikovanje strani
- [ ] 3. Gradnja strani in feedov
  - [x] skripta za feede (`skripte/zgradi_feede.py`), naslovi kopij še niso določeni
  - [x] stran (`skripte/zgradi_stran.py`, rezultat v `splet/`)
  - [ ] prava leta obdobij in retro logotipi
- [ ] 4. Nalaganje zvoka: Cloudflare R2, Internet Archive, GitHub Releases, torrent
- [ ] 5. Objava na začasnem naslovu
- [ ] 6. Preizkus
- [ ] 7. Preklop domene
- [ ] 8. Preusmeritev feeda v Fireside, Apple Podcasts in Spotify
- [ ] 9. Odpoved Fireside po 3 mesecih

## Kaj je kje

| Pot | Vsebina |
| --- | --- |
| `izvor/feed-2026-11-14.xml` | Originalni feed s Fireside. E-naslov je odstranjen, ker je repozitorij javen. |
| `izvor/slike/` | Naslovnice, sliki voditeljev, ikone |
| `izvor/poglavja/` | Poglavja štirih epizod, ki jih imajo |
| `izvor/stran/` | Nekaj strani obstoječega spletišča, za primerjavo |
| `epizode.csv` | Seznam epizod z velikostmi datotek in rezultatom preverjanja |
| `nastavitve.json` | Domena in naslovi treh kopij zvoka |
| `viri/` | Slog, JavaScript, slike in pisava strani |
| `splet/` | Zgrajena stran, pripravljena za objavo. Ne urejaj ročno, zgradi jo skripta. |
| `skripte/` | Skripte za preverjanje, prenos in gradnjo |

Zvok ne gre v git. Skripta ga prenese v mapo `zvok/`, ki je git ne spremlja.

## Lokalna kopija zvoka

Potrebuješ samo Python 3. Prenos je okoli 8,6 GB in ga lahko prekineš ter
nadaljuješ.

```bash
python3 skripte/prenesi_zvok.py
```

Skripta med prenosi počaka nekaj sekund, da ne obremenjuje Fireside, in na
koncu zapiše `zvok/SHA256SUMS`, s katerim se pozneje preveri vsaka kopija.

Za zelo počasen prenos čez cel vikend (ena epizoda na 12 minut):

```bash
python3 skripte/prenesi_zvok.py --premor 720
```

## Gradnja strani in feedov

```bash
python3 skripte/zgradi_stran.py
```

Zgradi celotno stran in feede v mapo `splet/`. Za predogled:

```bash
python3 skripte/predogled.py
```

Feedi nastanejo iz originalnega feeda: glavni in po eden za vsako kopijo. Skripta sama preveri, da so `guid`, datumi, naslovi in velikosti
enaki kot v izvirniku, sicer se ustavi.

## Kaj je javno in kaj ne

Repozitorij je javen, ker je del arhiva: iz njega se da stran in feede
zgraditi na novo, tudi če naju ni zraven.

Javno, v repozitoriju:

- originalni feed, slike, poglavja, opisi epizod,
- koda strani in skripte,
- načrt in stanje selitve.

Nikoli v repozitoriju:

- gesla, API ključi in žetoni (Cloudflare, Internet Archive, Fireside, registrar),
- e-naslovi in drugi osebni podatki,
- povabila v zaprte skupine (povabilo v Slack je iz shranjenih strani odstranjeno),
- statistika poslušanja, dokler se ne odločiva drugače,
- zvok (je na treh kopijah, ne v gitu).

Dostopi do računov so zapisani v upravitelju gesel, ne tukaj. Najpomembnejši
je račun pri registrarju domene: dvostopenjska prijava, samodejno podaljšanje,
dostop imata oba.

## Ideje za naprej

- **Opisi epizod (shownotes).** Nekatere zgodnje epizode nimajo opisa. Vsaka
  epizoda lahko dobi datoteko `epizode/<oznaka>.md`, ki dopolni ali zamenja
  opis iz feeda. Sprememba opisa ne vpliva na naročnine, ker `guid` ostane.
- **Prepisi (transcripts).** 217 ur zvoka se da prepisati strojno. Prepisi bi
  omogočili iskanje po vsebini epizod na strani, v feed pa gredo z oznako
  `podcast:transcript`. Odprto: kakovost prepisa slovenščine, pregled pred
  objavo in soglasje gostov, ker postane njihov govor iskljiv po imenu.
- **Poglavja** za epizode, ki jih še nimajo; lahko nastanejo iz prepisov.
