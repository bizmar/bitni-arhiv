# Bitni pogovori: arhiv

Selitev arhiva podcasta Bitni pogovori (215 epizod, 2012–2019) s Fireside na
brezplačno statično gostovanje. Feed, domena in povezave do epizod ostanejo
isti. Zvok bo na treh neodvisnih mestih.

## Stanje (14. 11. 2026)

Stran je objavljena na začasnem naslovu
<https://bitni-arhiv.bizmar.workers.dev>. Na domeni in na Fireside se še ni
nič spremenilo.

- [ ] 1. Varnostna kopija vsega s Fireside
  - [x] feed, slike, poglavja, nekaj strani (mapa `izvor/`)
  - [x] preverjene povezave do vseh MP3 (`epizode.csv`): vseh 215 se odziva, velikosti se ujemajo s feedom
  - [ ] lokalna kopija zvoka (`skripte/prenesi_zvok.py`), prenos teče
  - [ ] statistika poslušanja (potrebuje API ključ lastnika računa, ni nujno)
- [x] 2. Oblikovanje strani
- [x] 3. Gradnja strani in feedov
  - [x] skripta za feede (`skripte/zgradi_feede.py`)
  - [x] stran (`skripte/zgradi_stran.py`, rezultat v `splet/`)
  - [x] seznam epizod po letih, z iskanjem in filtrom po voditeljih in gostih
  - [x] logotipi štirih obdobij kot ikone ob epizodah
  - [x] licenca CC BY-NC-SA 4.0 in izjava o glasovih v nogi, `robots.txt`
- [ ] 4. Nalaganje zvoka: Cloudflare R2, Internet Archive, GitHub Releases, torrent
  - [x] skripti za nalaganje in preverjanje (`skripte/nalozi_zvok.py`, `skripte/preveri_kopije.py`)
  - [x] prostor na Cloudflare R2 in račun na Internet Archive
  - [ ] nalaganje (čaka na lokalno kopijo zvoka)
- [x] 5. Objava na začasnem naslovu (Cloudflare Workers, samodejno ob vsaki spremembi na `main`)
- [ ] 6. Preizkus
  - [x] strani, preusmeritve starih naslovov, stran 404, telefon in namizje
  - [ ] feed v validatorju in v podcast aplikacijah, zvok s kopij
- [ ] 7. Preklop domene (december 2026)
- [ ] 8. Preusmeritev feeda v Fireside, Apple Podcasts in Spotify (december 2026)
- [ ] 9. Odpoved Fireside po 3 mesecih

## Kaj je kje

| Pot | Vsebina |
| --- | --- |
| `izvor/feed-2026-11-14.xml` | Originalni feed s Fireside. E-naslov je odstranjen, ker je repozitorij javen. |
| `izvor/slike/` | Naslovnice, sliki voditeljev, ikone |
| `izvor/poglavja/` | Poglavja štirih epizod, ki jih imajo |
| `izvor/stran/` | Nekaj strani obstoječega spletišča, za primerjavo |
| `epizode.csv` | Seznam epizod z velikostmi datotek in rezultatom preverjanja |
| `nastavitve.json` | Domena, naslovi treh kopij zvoka, obdobja logotipov |
| `wrangler.jsonc` | Nastavitve objave na Cloudflare |
| `logotipi/` | Izvirne naslovnice po različicah (1.0, iOS 7, 1.5, 1.6, notch) |
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

## Nalaganje zvoka na kopije

Ko je zvok v mapi `zvok/`, gre na vsako kopijo z enim ukazom. Nalaganje se
lahko prekine in nadaljuje. Z `--poskus` skripta samo izpiše, kaj bi naredila.

```bash
python3 skripte/nalozi_zvok.py ia
```

```bash
python3 skripte/nalozi_zvok.py r2
```

```bash
python3 skripte/nalozi_zvok.py github
```

Ključi se nastavijo kot spremenljivke okolja (imena so na vrhu skripte) in ne
gredo v repozitorij. Torrent naredi Internet Archive sam. Potem se v
`nastavitve.json` vpišejo pravi naslovi kopij in preveri:

```bash
python3 skripte/preveri_kopije.py
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

Epizode so na voljo pod licenco CC BY-NC-SA 4.0. Uporaba posnetkov za učenje
sinteze govora ali posnemanje glasov ni dovoljena brez pisnega soglasja
govorcev.

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
