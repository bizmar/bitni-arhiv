# Bitni pogovori: arhiv

Selitev arhiva podcasta Bitni pogovori (215 epizod, 2012–2019) s Fireside na
brezplačno statično gostovanje. Feed, domena in povezave do epizod ostanejo
isti. Zvok bo na treh neodvisnih mestih.

## Stanje

- [ ] 1. Varnostna kopija vsega s Fireside
  - [x] feed, slike, poglavja, nekaj strani (mapa `izvor/`)
  - [x] preverjene povezave do vseh MP3 (`epizode.csv`)
  - [ ] lokalna kopija zvoka (`skripte/prenesi_zvok.py`)
  - [ ] statistika poslušanja (potrebuje API ključ lastnika računa, ni nujno)
- [ ] 2. Oblikovanje strani
- [ ] 3. Gradnja strani in feedov
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
| `skripte/` | Skripte za preverjanje in prenos |

Zvok ne gre v git. Skripta ga prenese v mapo `zvok/`, ki je git ne spremlja.

## Lokalna kopija zvoka

Potrebuješ samo Python 3. Prenos je okoli 8,6 GB in ga lahko prekineš ter
nadaljuješ.

```bash
python3 skripte/prenesi_zvok.py
```

Skripta med prenosi počaka nekaj sekund, da ne obremenjuje Fireside, in na
koncu zapiše `zvok/SHA256SUMS`, s katerim se pozneje preveri vsaka kopija.
