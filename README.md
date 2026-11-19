# Bitni pogovori: arhiv

Selitev arhiva podcasta Bitni pogovori (215 epizod, 2012–2019) s Fireside na
brezplačno statično gostovanje. Feed, domena in povezave do epizod ostanejo
isti. Zvok je na treh neodvisnih mestih.

## Stanje (19. 11. 2026)

Stran je objavljena na začasnem naslovu
<https://bitni-arhiv.bizmar.workers.dev> in zvok že predvaja z nove kopije.
Na domeni in na Fireside se še ni nič spremenilo; preklop čaka na december.

- [x] 1. Varnostna kopija vsega s Fireside
  - [x] feed, slike, poglavja, nekaj strani (mapa `izvor/`)
  - [x] preverjene povezave do vseh MP3 (`epizode.csv`): vseh 215 se odziva, velikosti se ujemajo s feedom
  - [x] lokalna kopija zvoka: vseh 215 MP3 (8,6 GB) prenesenih
  - [ ] statistika poslušanja (potrebuje API ključ lastnika računa, ni nujno)
- [x] 2. Oblikovanje strani
- [x] 3. Gradnja strani in feedov
  - [x] skripta za feede (`skripte/zgradi_feede.py`)
  - [x] stran (`skripte/zgradi_stran.py`, rezultat v `splet/`)
  - [x] seznam epizod po letih, z iskanjem in filtrom po voditeljih in gostih
  - [x] logotipi štirih obdobij kot ikone ob epizodah
  - [x] licenca CC BY-NC-SA 4.0 in izjava o glasovih v nogi, `robots.txt`
  - [x] lepljiv predvajalnik na strani epizode
  - [x] Alan Rener kot sovoditelj do epizode 147, pozneje posebni gost
  - [x] predavanji CryptoParty nista na strani (v feedu ostaneta zaradi gladke predaje)
- [x] 4. Nalaganje zvoka na tri kopije, vsaka preverjena s prstnimi odtisi SHA-256 (`SHA256SUMS`)
  - [x] GitHub Releases: 215 od 215
  - [x] Internet Archive (<https://archive.org/details/bitni-pogovori>): 215 od 215, torrent naredi sam
  - [x] Cloudflare R2: 215 od 215, glavni vir predvajanja
- [x] 5. Objava na začasnem naslovu (Cloudflare Workers, samodejno ob vsaki spremembi na `main`)
- [ ] 6. Preizkus
  - [x] strani, preusmeritve starih naslovov, stran 404, telefon in namizje
  - [x] zvok s kopij (predvajanje in previjanje prek R2)
  - [ ] feed v validatorju in v podcast aplikacijah (potreben ločen preizkusni feed)
- [ ] 7. Preklop domene (december 2026)
- [ ] 8. Preusmeritev feeda v Fireside, Apple Podcasts in Spotify (december 2026)
- [ ] 9. Odpoved Fireside po 3 mesecih

**Prepisi (dodatno):** strojni prepisi vseh epizod so narejeni lokalno in se
še izboljšujejo (popravki izrazov in imen). Na stran še niso objavljeni;
objava čaka na odločitev obeh voditeljev.

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

Po prenosu preveri, da so datoteke enake kot na kopijah:

```bash
cd zvok && shasum -a 256 -c ../SHA256SUMS | grep -v ': OK$'; cd ..
```

Brez izpisa pomeni, da je vseh 215 v redu.

## Kopije zvoka

| Kopija | Naslov datoteke |
| --- | --- |
| Cloudflare R2 (glavna) | `https://pub-b2c25dd3ebfc45c1881bc21b9000b3ec.r2.dev/<oznaka>.mp3` |
| Internet Archive | `https://archive.org/download/bitni-pogovori/<oznaka>.mp3` |
| GitHub Releases | `https://github.com/bizmar/bitni-arhiv/releases/download/zvok/<oznaka>.mp3` |

Stran in feed kažeta na `/audio/<oznaka>.mp3`, ki ga ena vrstica v
`splet/_redirects` preusmeri na glavno kopijo. Če kopija odpove, se v
`skripte/zgradi_stran.py` zamenja ta vrstica, stran se zgradi znova in
objavi.

Preverjanje vseh kopij (velikost; z `--vsebina` tudi prstni odtis):

```bash
python3 skripte/preveri_kopije.py
```

Nalaganje na kopijo, če bi bilo kdaj treba znova (ključi kot spremenljivke
okolja, imena so na vrhu skripte; nikoli v repozitorij):

```bash
python3 skripte/nalozi_zvok.py r2
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
- **Opozorilo, če kopija zvoka odpove.** Tedensko samodejno preverjanje
  (`skripte/preveri_kopije.py`), ki ob napaki pošlje e-pošto. Možnosti:
  GitHub Actions v tem repozitoriju ali zunanji brezplačni nadzornik
  dosegljivosti. Preklop vira ostane ročen.
- **Vse tri kopije vidne na strani.** Ko je zvok naložen, stran epizode in
  noga že izpišeta povezave do vseh treh kopij in feedov zanje. Dodati še
  torrent in kratko stran »Kako oživiti arhiv«.
- **Rezervna kopija strani na GitHub Pages.** Deluje samo z domeno (stran
  uporablja naslove od korena), zato se postavi ob preklopu domene ali ko bi
  Cloudflare odpovedal.
- **YouTube.** Vseh 215 epizod kot podcast na YouTubu. Načrt:
  - *Nalaganje.* Najmanj dela je uvoz iz feeda RSS v YouTube Studiu (YouTube
    sam naredi videe z naslovnico in zvokom); preveriti, ali je na voljo za
    naš kanal, in narediti šele po preklopu domene, da bere novi feed. Rezerva:
    videe naredimo sami (`ffmpeg`, naslovnica obdobja in zvok) in naložimo
    prek API-ja; omejitev je okoli 6 videov na dan, projekt brez Googlovega
    pregleda pa lahko nalaga samo zasebne videe.
  - *Opisi.* Opis epizode iz feeda, na vrhu en stavek povzetka in povezava
    na stran epizode, spodaj licenca in izjava o glasovih.
  - *Poglavja.* YouTube jih prebere iz opisa: seznam časov, prvi `0:00`,
    vsaj tri poglavja, vsako vsaj 10 sekund. Naredi jih skripta iz
    `izvor/poglavja/`; za epizode brez poglavij lahko nastanejo iz prepisov.
  - *Prepisi.* Naložijo se kot podnapisi (VTT, jezik slovenščina) namesto
    samodejnih. Velja isti pogoj kot za stran: pregled in soglasje gostov.
  - *Iskanje (SEO).* Naslov »Naslov epizode | Bitni pogovori 151«, prvi dve
    vrstici opisa s ključnimi besedami, jezik videa slovenščina, kategorija
    Znanost in tehnologija, seznam predvajanja označen kot podcast, seznami
    po letih, sličica s številko epizode in logotipom obdobja, podnapisi,
    urejen opis kanala s povezavo na stran.
  - *Odprto.* Čigav bo kanal; licenca (YouTube pozna samo standardno in
    CC BY, zato standardna, CC BY-NC-SA pa v opisu); izvirni datum izida gre
    v opis, ker YouTube pokaže datum nalaganja; komentarji in oglasi.
