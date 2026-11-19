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

## Stanje po korakih (19. 11. 2026)

1. **Varnostna kopija:** narejeno. Feed, slike, poglavja, nekaj strani v
   `izvor/`; vseh 215 MP3 je na lastnikovem Macu v `zvok/` (ni v gitu).
   Neobvezna statistika poslušanja odložena (potrebuje Nejčev API ključ).
2. **Oblikovanje:** narejeno in potrjeno.
3. **Gradnja:** narejeno (`skripte/zgradi_stran.py` → `splet/`).
4. **Nalaganje zvoka:** narejeno. GitHub Releases, Internet Archive
   (`bitni-pogovori`) in Cloudflare R2: vsak 215/215, vsebina preverjena s
   SHA-256 (`SHA256SUMS`). Torrent naredi Internet Archive sam.
5. **Objava na začasnem naslovu:** narejeno. Cloudflare Workers na
   `https://bitni-arhiv.bizmar.workers.dev`, vsak push na `main` se objavi
   sam (`wrangler.jsonc`, glava `noindex`). Zvok predvaja prek `/audio/` → R2.
6. **Preizkus:** strani in zvok narejeno. Odprto: feed v validatorju in v
   aplikacijah. Feed na začasnem naslovu kaže na domeno (še pri Fireside),
   zato ga ne dodajati v aplikacije; pripraviti ločen preizkusni feed.
7.–9. Preklop domene, preusmeritev feeda (Fireside, Apple, Spotify),
   odpoved Fireside po 3 mesecih: čaka na Nejca (december 2026).

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
- Zagon (glavni prepis, ob sesutju se znova zažene, narejeno preskoči):
  `sh skripte/prepisi_noc.sh <meja °C> [prednostne oznake]`. Ponoči meja
  70 (lastnik ne želi hrupa), podnevi 100 (brez omejitve). Pri 70 °C okoli
  2–8× hitreje od realnega časa, brez omejitve okoli 6×. Dnevnik
  `prepisi-preizkus/nocno.log`.
- Procese zaganjaj ločeno od aplikacije Claude, sicer se ob njenem zaprtju
  ustavijo (zgodilo se je 16. 11.):
  `python3 -c 'import os,sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' sh skripte/prepisi_noc.sh 100 </dev/null >/dev/null 2>&1 &`
  Enako za `prepisi_pregled.py`, `predogled.py 8001 prepisi-preizkus/splet`
  in za čakalni »zaključek« (čaka na PID ovoja, nato zaporedoma
  `prepisi.py --gostje`, `prepisi_izboljsave.py --imena`,
  `prepisi_izboljsave.py --dvomljivi --meja 100`, `prepisi.py --izvozi`,
  `zgradi_stran.py --prepisi --izhod prepisi-preizkus/splet`,
  `prepisi.py --primerjava`; na koncu vrstica ZAKLJUCEK v
  `prepisi-preizkus/zakljucek.log`).
- Po `brew upgrade` (nov Python) ločeni procesi izgubijo dostop do mape
  Documents (»Operation not permitted«, 19. 11.): ustavi ovoj in ga znova
  zaženi iz seje Claude; narejeno preskoči.
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
- **Stanje 16. 11. 2026 dopoldne:** 184 od 215 epizod prepisanih, ostanek
  teče (okoli 5 ur), nato samodejni zaključek. Rezultati prvih 184:
  povprečno 1,7 % besedila dvomljivega; angleščina samo v 54 (Carrot,
  pravilno); gostje prepoznani z doslednostjo glasu 0,85–0,97. Preizkus
  `--dvomljivi` na epizodi 17 je vrnil cele izgubljene stavke.
- **16. 11. popoldne:** glavni prepis končan (213 + cryptoparty001/002, ki sta
  padli zaradi napake pri epizodah brez oseb in tečeta znova). Lastnik je
  opazil zanke (Whisper isto besedo ali stavek ponovi do 50-krat, okoli 500
  mest) in zamik. Zanke: izvoz jih skrajša na dve ponovitvi, `--dvomljivi`
  jih prepiše znova (zdaj dopolnjuje, že narejeno ostane). Zamik na vzorcu:
  začetki odstavkov se ujemajo z zvokom; odstopa tam, kjer je model izmislil
  imena (prve epizode) ali se zaciklal, kar popravijo izboljšave. MP3 so CBR
  in enaki kot na Fireside.
- **17. 11.:** zaključek končan (dvomljivo 0,4 %, zank 0, začasni WAV
  pobrisani). Govorci brez imena v 7 epizodah poimenovani ročno
  (`delo/<oznaka>/imena.json`); pregled za lastnika na
  `localhost:8001/govorci` (ni v gitu); lastnik je vsa imena potrdil.
- **Po zaključku:** preveriti `zakljucek.log` in pregled; pobrisati
  `prepisi-preizkus/delo/*/zvok.wav` (okoli 115 MB na uro, nastanejo znova
  iz MP3); pregledati epizode z govorcem brez imena (»Govorec N«) in jih
  po potrebi potrditi ročno (`prepisi.py --imena <oznaka> G1="Ime" …`);
  lastniku pokazati predogled in odpreti vprašanje objave.
- **Dogovorjeno za vikende (16. 11.):** popravek napačno zapisanih izrazov in
  imen (npr. angleški izrazi, ki jih Whisper »poslovenči«) s podagenti Sonnet
  (high) v seji Claude Code, ne prek API-ja. Vsak dobi eno epizodo in njene
  opombe, vrne samo seznam popravkov (čas, staro, novo, razlog) v
  `delo/<oznaka>/popravki.json`, izvoz jih uporabi. Najprej preizkus na 3–4
  epizodah, lastnik pregleda, nato serije po 10–20. Obdelava zvoka (čiščenje
  šuma) po oceni ne bi pomagala; lahko se preizkusi le pri slabih posnetkih.
- **18. 11.: preizkus popravkov s podagenti** na epizodah 17, 54, 100, 150,
  205: 232 popravkov (izrazi, izdelki, imena), vsi uporabljeni. Postopek:
  `prepisi_popravki.py --pripravi <oznake>` (vhod v `popravki-vhod/`),
  podagent Sonnet high zapiše `delo/<o>/popravki.json` in negotova mesta
  (`popravki-negotovo.json`), `--preveri` naredi poročilo
  (`localhost:8001/popravki`), `prepisi.py --izvozi` jih uporabi
  (`uporabi_popravke`). Po vsaki gradnji predogleda `--preveri` znova, ker
  gradnja stran pobriše. Lastnik na strani `/popravki` zavrne (✗) ali
  drugače popravi popravke in doda svoje; strežnik `predogled.py` jih shrani v
  `delo/<o>/popravki-lastnik.json`, izvoz jih upošteva. Lastnik: večina
  popravkov je pravilnih. Datum v uvodu se lahko razlikuje od datuma v
  feedu (posneto prej kot objavljeno); to ni napaka, podagentom ne javljati.
  Nato serije po 10–20.
- **19. 11.: prva serija 10 epizod** (5 30 45 70 90 120 135 165 185 210),
  po koncu govorcev za vse epizode. Podagent zdaj sam zapiše tudi
  `popravki-negotovo.json`. 420 popravkov, vsi uporabljeni. Popravke
  številk, ki popravljajo dejstvo namesto slišanega (npr. 15,3 → 12,5),
  premakni med negotove. Poraba: okoli 100–135 tisoč žetonov na epizodo
  (Sonnet high, povprečno 111 tisoč, po poročilu Claude Code), 1–2,5 min
  na epizodo, 10 vzporedno v okoli 2,5 min.
- **19. 11.: druga serija 20 epizod** (1 12 24 35 46 58 69 81 92 103 114
  125 136 147 158 170 180 191 202 resnicno-preprosta). Navodila za
  podagenta so zdaj v `skripte/popravki_navodila.md` (podagent dobi le
  oznako). Povprečno 110 tisoč žetonov na epizodo (83–147 tisoč), skupaj
  2,2 milijona. Po 2. seriji 35 epizod, 1518 popravkov, vsi uporabljeni.
  Izbira naslednjih: enakomerno po še nenarejenih (brez cryptoparty).
- **19. 11.: tretja serija 20 epizod** (2 13 25 36 47 59 71 80 93 104 113
  124 137 146 157 169 179 190 201 204-1). Povprečno 106 tisoč žetonov
  (69–124 tisoč), skupaj 2,1 milijona, 20 vzporedno v okoli 2,5 min.
  Skupaj 55 epizod, 2191 popravkov, vsi uporabljeni. Še 158 epizod.
- **18. 11.: govorci po stavkih** (`skripte/govorci_stavki.py <oznaka>`):
  obstoječe besedilo se poravna z zvokom (Whisper forced alignment), stavke,
  ki jih je stara delitev presekala, združi, vsak stavek ≥1,2 s in ≥3
  besede dobi govorca po glasu (ECAPA, jasna razlika). Kratki »ja« ostanejo
  pri okoliškem govorcu (lastnik: ni treba vsakega). Zapiše
  `delo/<o>/stavki.json`, izvoz ga uporabi, če se odstavki niso spremenili.
  Preizkus na 100: 59 od 1667 stavkov drug govorec, odstavkov, ki se začnejo
  sredi stavka, 247 → 5. Lastnik: »izgleda dobro«.
- **18. 11. zvečer: govorci po stavkih za vse epizode** zagnano ločeno:
  `sh skripte/govorci_noc.sh 70` (meja °C; ob sesutju znova, narejeno
  preskoči). Dnevnik `prepisi-preizkus/govorci.log` (vrstice NAREJENO).
  Okoli 5 min na epizodo + hlajenje, krajše epizode najprej; skupaj okoli
  1–2 dni. Na koncu sam požene izvoz, gradnjo predogleda in `--preveri`;
  zadnja vrstica ZAKLJUCEK.
- **18. 11.: netočno preskakanje v zvoku.** 46 epizod (večinoma 55–140)
  ni pravi CBR (tišine z nižjo hitrostjo, Xing TOC), zato brskalnik pri
  skoku na čas zgreši tudi za 10–25 s; po ogledu več mest postane točno.
  Prepis in predvajalnik nista kriva. Lastnik je odločil: pusti tako
  (datoteke ostanejo enake kot na Fireside, brez prepakiranja v CBR).
  **Narejeno 19. 11. (seja, ki dela stran):** seznam je v `nastavitve.json`
  (`netocno_preskakanje`), opozorilo je v vrstici pod gumbom prepisa.
  Prvotna naloga: na strani teh epizod dodati kratko opozorilo
  (npr. ob prepisu: pri skoku na čas se lahko prepis in zvok za nekaj
  sekund ne ujemata, ker je posnetek tak; od začetka teče usklajeno).
  Epizode: 55 57 59 63 64 66 68a 68b 70 72 74 76 78 79 81 83 85 87 88 90 93 95 97 99 100 102 104 107 109 110 112 114 115 117 119 121 123 125 127 129 131 133 135 137 139 140 (oznake datotek;
  zaznano s preverjanjem okvirjev MP3, 18. 11.).
- Neuporabljeno, a shranjeno: arhiva modelov RSDO v
  `~/.cache/bitni-prepisi/modeli/*.tar.zst` (možen dodaten »glasovalec« pri
  `--dvomljivi`).

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
  Lastnik (18. 11.): gostov verjetno ne bodo obveščali, vpraša še Nejca.
  Pojasnjeno: obvestilo ni nujno, je vljudnost (iskalniki najdejo besedilo,
  strojne napake lahko gostu pripišejo napačne besede).

- **cryptoparty002:** posnetek se ne ujema s feedom. Feed: »Gorazd Božič:
  Zaščitite svojo elektronsko pošto s PGP«; v posnetku je predavanje Mateja
  Kovačiča o mobilni telefoniji (ugotovljeno iz prepisa 17. 11.). Lastnik
  (17. 11.): obe cryptoparty sta predavanji, ne del podcasta; iz arhiva ju
  odstrani seja, ki dela stran. Pri prepisih se z njima ne ukvarjamo
  (izpustiti pri popravkih s podagenti).

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

## Stanje 17. 11. 2026 (seja, ki dela stran)

- Zvok: GitHub Releases naložen in preverjen s SHA-256 (`SHA256SUMS` v korenu
  repozitorija, odtisi kot jih poroča GitHub; lokalna kopija se ujema).
  Internet Archive naložen (`archive.org/details/bitni-pogovori`, 215
  datotek, vsebina preverjena s SHA-256). R2 naložen 18. 11., vsebina
  preverjena s SHA-256 (215/215). `zvok_nalozen` je `true`: stran predvaja
  prek `/audio/` (preusmeritev na R2) in kaže povezave do vseh treh kopij.
- Predavanji `cryptoparty001` in `cryptoparty002` nista na strani
  (`izpusti_na_strani` v `nastavitve.json`, povezavi preusmerita na seznam):
  213 strani epizod. V feedu ostaneta (215), ker je prioriteta gladka
  predaja: novi feed naj bo enak staremu. Po končani selitvi se lahko
  dodata v `izpusti_v_feedu`. Zvok ostane na kopijah (odločil lastnik).
- Alan Rener: sovoditelj do epizode 147, pozneje posebni gost
  (`sovoditelji` v `nastavitve.json`); feed ostane nespremenjen.
- Stran epizode: predvajalnik je lepljiv (`.kartica.plava`), prepis teče v
  strani brez notranjega drsnika, na vrhu prepisa je jasno opozorilo, da ni
  natančen. Prepisi še niso objavljeni (čaka odobritev).

## Omejitve oblačne seje

- Nalaganje v GitHub Releases in push oznak (tag) sta iz oblačne seje
  blokirana (HTTP 403). `git push` na veje deluje.
- Seja je začasna, zato 8,6 GB zvoka tu ni kam shraniti. Prenos teče na
  lastnikovem računalniku ali neposredno v Internet Archive, ko bodo ključi.
- Prenos pisav z GitHuba je blokiran; Jost je vzet iz paketa npm
  `@fontsource-variable/jost`.

## Commiti z lastnikovega Maca

- Od 19. 11. 2026 so podpisani s ključem SSH (samo za podpise, geslo v
  Keychainu, na GitHubu dodan kot »Signing key«). Avtor je lastnik z
  GitHubovim naslovom noreply; nastavljeno v lokalni nastavitvi gita tega
  repozitorija. Claude je naveden kot soavtor (`Co-Authored-By`).
- Če podpis odpove (po ponovnem zagonu ključ ni naložen):
  `ssh-add --apple-load-keychain`. Ne commitati brez podpisa.
- Starejši commiti s Maca ostanejo nepodpisani (zgodovine ne prepisujemo).
  Commiti iz oblačnih sej jih podpiše GitHub.
- Na `main` velja pravilo GitHuba (ruleset »main: samo podpisani commiti«,
  od 19. 11. 2026, brez izjem): push z nepodpisanim commitom GitHub zavrne.
  Takrat commit podpiši (`git commit --amend -S --no-edit` oz. pri več
  commitih `git rebase --exec 'git commit --amend -S --no-edit' origin/main`
  za še ne pushane commite) in pushaj znova.

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
  `nastavitve.json`. Vedro je naloženo in preverjeno (18. 11. 2026).
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

## Naslednji koraki (stanje 19. 11. 2026)

1. Preizkusni feed za aplikacije (korak 6): feed, ki ga lastnik lahko
   varno doda v aplikacijo, z zvokom prek R2 in brez `itunes:new-feed-url`
   na domeno; preveriti tudi v validatorju.
2. Objava prepisov na stran: čaka na lastnika in Nejca (obveščanje gostov
   verjetno ne). Prepisi se medtem izboljšujejo v seji na Macu (popravki s
   podagenti, govorci po stavkih). Ko bo odobreno: odstraniti zaporo v
   `zgradi_stran.py` (`--prepisi` brez `--izhod`), prepise dodati v git.
3. December z Nejcem: koraki 7–9 (navodila v načrtu selitve). Pred
   preklopom domene vprašati Fireside podporo o preusmeritvi po odpovedi.
4. Po selitvi: predavanji CryptoParty lahko v `izpusti_v_feedu`; nova
   podpisana oznaka ob mejniku (prva: `pred-selitvijo-2026-11`, 19. 11.,
   podpisal lastnik na Macu; iz oblačne seje push oznak ni dovoljen, 403).
5. Za pozneje (README »Ideje za naprej«): opozorilo ob odpovedi kopije,
   GitHub Pages kot rezerva, YouTube, imenovalnik, rezervni dostop za Nejca.
6. Lastnik želi vprašanja eno po eno. Oblikovanje: majhni, natančni koraki;
   ob »preveč« vrniti na prejšnjo različico in spremeniti samo omenjeno.

## Dokumenta zunaj repozitorija

Načrt selitve in osnutek oblikovanja sta zasebna artefakta na claude.ai v
lastnikovem računu (»Bitni pogovori: načrt selitve arhiva« in »Bitni pogovori:
osnutek strani«). Odpreta se s seznama artefaktov.
