# Zapiski za nadaljevanje dela

Ta datoteka je za Claude in za vsakogar, ki delo nadaljuje. Repozitorij je
javen: sem ne sodijo gesla, ključi, e-naslovi, povezave do zasebnih dokumentov
ali njihova vsebina. Pregled za ljudi je v `README.md`.

## Kaj je projekt

Selitev arhiva podcasta Bitni pogovori (215 epizod, 2012–2019, 217 ur, 8,6 GB
MP3) s Fireside na brezplačno statično gostovanje. Cilji po pomembnosti:

1. Obstoječe naročnine delujejo naprej (isti `guid`, preusmeritev feeda).
2. Obstojnost 10 do 20 let z minimalnim vzdrževanjem. Edini stalni strošek je
   domena `bitnipogovori.si`.
3. Zvok na treh neodvisnih mestih: Cloudflare R2, Internet Archive, GitHub
   Releases. Dodatno torrent in lokalni kopiji.
4. Stran: navaden HTML in CSS, videz spleta okoli 2017, zgled lmnt.me.

## Kako delamo

- Odgovori v slovenščini, kratko in pregledno, brez tehničnega žargona, kjer
  ni potreben.
- Načrt gre korak za korakom; vsak korak lastnik odobri, preden se začne.
- Fireside beri nežno in počasi (premori med zahtevki, en zahtevek naenkrat).
- Po vsaki spremembi commit in push na `main`.
- Nič se ne objavi na splet in nič se ne spremeni na Fireside ali domeni brez
  izrecne odobritve.
- Lastnik repozitorija je sodelavec na Fireside, ne lastnik računa. Lastnik
  računa Fireside (in verjetno domene) je sovoditelj Nejc.

## Stanje po korakih (14. 11. 2026)

1. **Varnostna kopija:** feed, slike, poglavja in nekaj strani so v `izvor/`.
   Vseh 215 povezav do MP3 je preverjenih (`epizode.csv`, vse v redu).
   Manjka: lokalna kopija zvoka (lastnik požene `skripte/prenesi_zvok.py`
   doma; star arhiv zvoka ima na disku, ki ni priklopljen) in neobvezna
   statistika (potrebuje API ključ lastnika računa Fireside; odloženo).
2. **Oblikovanje:** osnutek potrjen na prvi pogled. Temno modra tema.
3. **Gradnja:** narejeno. `skripte/zgradi_stran.py` zgradi `splet/` (stran in
   feedi). Preizkušeno v brskalniku na namizni in telefonski širini.
4. **Nalaganje zvoka:** skripti sta pripravljeni (`skripte/nalozi_zvok.py`
   za R2, Internet Archive in GitHub; `skripte/preveri_kopije.py`). Podpis
   za R2 je preverjen z uradnim primerom AWS, pravo nalaganje še ni bilo
   preizkušeno. Čaka na lokalno kopijo zvoka, račune (Cloudflare, Internet
   Archive).
5. **Objava na začasnem naslovu:** narejeno. Cloudflare Workers (statične
   datoteke) na `https://bitni-arhiv.bizmar.workers.dev`, povezano z
   repozitorijem: vsak push na `main` se objavi sam. Nastavitve so v
   `wrangler.jsonc`. Začasni naslov ima glavo `noindex`.
6.–9. Preizkus, preklop domene, preusmeritev feeda, odpoved Fireside: ni
   začeto; koraki 7 do 9 čakajo na Nejca (december 2026).

**Prepisi (dodatno, začeto 14. 11. 2026).** Lokalno na lastnikovem Macu
(M2 Pro), brezplačno. Zvok vseh 215 epizod je v `zvok/` (ni v gitu).
- Metoda: Whisper large-v3 (MLX) v oknih do 28 s s časi besed; govorci z
  glasovnimi odtisi ECAPA (speechbrain) in gručenjem, število gruč = število
  oseb v feedu, zelo podobne gruče se združijo; angleščina se zazna po oknih
  (najprej vzorec 12 oken). Imena: glasovni vzorci voditeljev (ročno potrjeni
  v `imena.json`), gostje po izločanju (`--gostje`). Vzorci so biometrični
  podatki in so samo v `~/.cache/bitni-prepisi/glasovi/`, nikoli v gitu.
- Preizkušeno tudi: slovenski model RSDO/PROTOVERB (CLARIN.SI) + model za
  ločila. Hitrejši, a tehnične izraze in angleščino popači (»Gookle Rier«),
  zato je izbran Whisper.
- Okolje: `~/.cache/bitni-prepisi/.venv` (Python 3.11), modeli v
  `~/.cache/bitni-prepisi/modeli/`. Navodila v glavi `skripte/prepisi.py`.
- Nočno delo: `nohup sh skripte/prepisi_noc.sh 70 &` (meja 70 °C, ob
  sesutju se znova zažene, narejeno preskoči). Pri 70 °C okoli 2× hitreje od
  realnega časa. Dnevnik `prepisi-preizkus/nocno.log`.
- Živi pregled: `nohup $PY skripte/prepisi_pregled.py &` in
  `python3 skripte/predogled.py 8001 prepisi-preizkus/splet`, nato
  http://localhost:8001/pregled (napredek, hitrost, ocena konca, temperatura;
  predogled s prepisi se ob vsaki končani epizodi posodobi sam).
- Vmesni rezultati so v `prepisi-preizkus/delo/` (v .gitignore), končni v
  `prepisi/` (`--izvozi`, tudi v .gitignore, dokler objava ni odobrena).
- Izboljšave (`skripte/prepisi_izboljsave.py`): `--imena` doda manjkajoča
  imena z glasovanjem (samopredstavitev, predstavitev v uvodu, nagovor, glas;
  najde tudi goste, ki jih feed ne navaja), `--dvomljivi` dvomljive in
  sumljivo kratke odstavke prepiše na 5 načinov in izbere različico z
  najmanjšim pričakovanim odstopanjem (MBR). Teče samodejno po glavnem
  prepisu (`prepisi-preizkus/zakljucek.log`).
- Namig modelu je brez imen: s seznamom imen je Whisper na nejasnih mestih
  ponovil imena namesto govora (okoli 4 % zvoka v prvih 54 epizodah; to
  popravi `--dvomljivi`).
- Na strani: `zgradi_stran.py --prepisi --izhod prepisi-preizkus/splet`
  zgradi predogled (razdelek Prepis, sledenje predvajanju, iskanje po vseh
  prepisih, VTT). Brez `--izhod` gradnja s prepisi zavrne delo, da prepisi
  ne pridejo v `splet/` (ta se ob pushu sam objavi).

## Sprejete odločitve

- Vir zvoka se preklaplja **ročno**: ena vrstica v `splet/_redirects`
  (`/audio/:datoteka` na trenutno kopijo). Brez funkcij in rednega preverjanja.
- Glavni feed ostane na `https://www.bitnipogovori.si/rss`. Fireside po
  preklopu ostane vklopljen še 3 mesece zaradi preusmeritve.
- Namesto strani voditeljev in gostov je iskanje s filtrom po osebah.
- Seznam epizod je ena lista, razdeljena po letih. Logotipi obdobij niso
  kategorije, ampak majhna ikona ob vsaki epizodi (logotip, ki je veljal ob
  izidu).
- Povezave na Slack ni nikjer na strani.
- V nogi (stolpec »O strani«) piše, da sta stran in arhiv zgrajena z umetno
  inteligenco Claude. Trditve »ročno napisan« ni.
- Glava vstopne strani: modri preliv s subtilno mrežo ikon tem v krogcih
  (iz pasice za Twitter 2014).
- Pisava naslovov: Futura (sistemska na Applovih napravah), rezerva Jost
  (priložena, licenca OFL). Logotip je po oblikah črk najverjetneje Futura;
  imena pisave v datoteki AI ni, ker je besedilo v krivuljah.
- Modra je uradna `#0e8ef0`. Oranžna ostane `#FF8A24`, ker se ujema s
  prelivom v logotipu (uradna `#ff5b24` iz starih zapiskov je bolj rdeča).
- Licenca arhiva: CC BY-NC-SA 4.0 (potrdila oba voditelja; izpisana v nogi strani).
  Licenca ne ureja kloniranja glasov, zato je dodana izjava o glasovih: v
  nogi strani, v opisu na Internet Archive, v `robots.txt` (zavrne pajke za
  učenje) in z glavo `tdm-reservation: 1`.
- E-naslova v novem feedu ni.
- Repozitorij je javen kot del arhiva. Pravila, kaj sme vanj, so v `README.md`.

## Odprta vprašanja

- **Objava prepisov:** soglasje gostov, pregled kakovosti, ali tudi v feed
  (`podcast:transcript`). Do odobritve ostanejo prepisi samo lokalno.

- **Obdobja logotipov** so določena po datumih izvornih datotek (potrdil
  lastnik): 1.0 do junija 2013 (epizode 1–30), tanke črke iOS 7 od junija
  2013 (31–43), oblaček 1.5 od novembra 2013 (44–161), 1.6 od marca 2017
  (162–210; »notch« pri 177, 1.5p od 178). Ni potrjeno, ali je bil logotip
  iOS 7 res naslovnica v feedu. Obdobja so v `nastavitve.json` po datumu.
- Računi: po selitvi je za gostovanje odgovoren lastnik repozitorija (do
  zdaj Nejc). Računa Cloudflare in Internet Archive ima. Dostop do
  registrarja domene, Apple Podcasts Connect in Spotify for Creators ima
  Nejc (deli prijavo ali zamenja sam). Nejc ima čas šele decembra 2026:
  koraki 7 do 9 čakajo do takrat, vmes se vse pripravi in spolira. Odprto:
  rezervni dostop za drugega voditelja.
- Ali preusmeritev na Fireside lahko ostane po odpovedi ali na cenejšem paketu
  (vprašati njihovo podporo).
- Povabilo v Slack ostane v zgodovini gita (prva dva commita); lastnik je
  odločil, da se zgodovina ne prepisuje.

## Omejitve oblačne seje

- Nalaganje v GitHub Releases je iz oblačne seje Claude Code blokirano (HTTP
  403 na ustvarjanje izdaj). `git push` deluje.
- Seja je začasna, zato 8,6 GB zvoka tu ni kam shraniti. Prenos teče na
  lastnikovem računalniku ali neposredno v Internet Archive, ko bodo ključi.
- Prenos pisav z GitHuba je blokiran; Jost je vzet iz paketa npm
  `@fontsource-variable/jost`.

## Tehnične posebnosti

- Šest epizod ima namesto številke posebno oznako: `resnicno-preprosta`,
  `68a`, `68b`, `cryptoparty001`, `cryptoparty002`, `204-1`. Oznaka je zadnji
  del naslova epizode in ime datoteke zvoka (`151.mp3`).
- Fireside v feedu piše imenski prostor Atom s poševnico na koncu
  (`http://www.w3.org/2005/Atom/`). Skripta to upošteva.
- Strani epizod so datoteke `splet/<oznaka>.html`; Cloudflare Pages in GitHub
  Pages jih postrežeta na `/<oznaka>`. Za lokalni predogled je
  `skripte/predogled.py`, ker navaden strežnik tega ne zna.
- Dokler v `nastavitve.json` ni `zvok_nalozen: true` (in dokler ima katera
  kopija začasni naslov z »SE-NI-DOLOCEN«), stran predvaja zvok z izvirnega
  naslova Fireside in ne izpiše povezav do kopij.
- R2: vedro `bitni-pogovori-zvok`, javni naslov `r2.dev` je v
  `nastavitve.json`. Vedro je še prazno; ključ za nalaganje še ni ustvarjen.
- `zgradi_feede.py` se ustavi, če se pri kateri epizodi spremeni `guid`,
  naslov, datum, povezava ali velikost.
- `splet/` se ne ureja ročno; vedno jo zgradi skripta in se commita.

## Zasebni viri (samo kazalo, vsebina se ne objavlja)

Lastnik ima zasebne priprave na epizode. Morda bodo pozneje dodane k opisom
epizod, a šele po izrecni odobritvi. Do takrat se njihova vsebina ne bere v
repozitorij in se ne objavlja.

- **Google Docs** (iskanje po naslovu »ep NN« ali »Bitni«): priprave za
  epizode 69 do 111 (brez 107) in 179; predloga priprav; dokumenti za kviz;
  prvi skupni dokument iz leta 2012.
- **Dropbox, mapa preseljenih dokumentov Paper »Bitni Pogovori«:** priprave
  za epizode 110 (predloga), 114 in 160 do 166.
- **Dropbox, mapa z grafičnimi materiali:** izvorne datoteke logotipov (PSD,
  AI, EPS), barvne različice, pasice, favicon, majice. Štiri naslovnice so že
  v `logotipi/`.
- **Dropbox, mapa podcasta:** zvočni učinki, uvodna glasba, nastavitve
  snemanja. Epizod tam ni.

## Ideje za naprej

Opisane so v `README.md`: bogatejši opisi epizod, strojni prepisi, poglavja,
opozorilo ob odpovedi kopije (lastnik je vprašal, kako bo čez leta izvedel,
da R2 ne deluje; še ni odločeno, katera možnost), vse tri kopije vidne na
strani, GitHub Pages kot rezerva. Lastnik: najprej MP3, to je za pozneje.
Pri prepisih so odprti kakovost slovenščine, pregled pred objavo in soglasje
gostov.

Easter egg »imenovalnik«: lastnik je na začetku vsake epizode izbral eno ime
in pozdravil tega poslušalca. Seznam okoli 400 imen ima v Dropboxu (mapa
nastavitev Alfreda, `imena.txt`). Zamisel: pozdrav z naključnim imenom na
vstopni strani (klik izbere novo) in pravo ime iz prepisa na strani epizode.
Točen stavek pozdrava se določi, ko bodo prepisi. Lastnik prepise dela
lokalno na Macu v ločeni seji.

YouTube (lastnik želi v načrtu, 15. 11. 2026): vseh 215 epizod kot podcast
na YouTubu s preneseno vsebino opisov, poglavij (časi v opisu) in prepisov
(podnapisi) ter urejenim SEO. Načrt in odprta vprašanja so v `README.md`.
Dejstva o uvozu iz RSS in omejitvah API-ja pred izvedbo preveriti v
YouTubovi dokumentaciji; niso bila preverjena.

## Naslednji koraki (stanje ob koncu seje 14. 11. 2026)

1. Lastnik na Macu prenaša zvok (`caffeinate -is python3
   skripte/prenesi_zvok.py --premor 720` ali `--premor 60`). Mac je vmes
   zaspal; prenesenih je bilo le nekaj epizod. Repozitorij ima na Macu v
   mapi Documents (ime mape ima tipkarsko napako, ne preimenovati med
   prenosom). Pred nalaganjem naj požene `git pull`.
2. Ko je zvok prenesen: ključ R2 (Object Read & Write, samo to vedro) in
   ključa Internet Archive nastavi kot spremenljivke okolja na Macu (nikoli
   v klepet ali repozitorij), nato `skripte/nalozi_zvok.py ia`, `r2`,
   `github`. Za GitHub potrebuje nameščen in prijavljen `gh`.
3. V `nastavitve.json` vpisati oznako Internet Archive, pognati
   `skripte/preveri_kopije.py`, nato `zvok_nalozen: true` in zgraditi stran.
4. Preizkus feeda: na začasnem naslovu ga ne dodajati v aplikacije, ker
   `itunes:new-feed-url` kaže na domeno. Pripraviti ločen način preizkusa.
5. Lastnik želi vprašanja eno po eno, ne več naenkrat.

## Dokumenta zunaj repozitorija

Načrt selitve in osnutek oblikovanja sta zasebna artefakta na claude.ai v
lastnikovem računu (»Bitni pogovori: načrt selitve arhiva« in »Bitni pogovori:
osnutek strani«). Odpreta se s seznama artefaktov.
