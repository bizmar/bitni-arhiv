# Navodila za podagenta: popravki prepisa ene epizode

(Uporablja `prepisi_popravki.py`; podagent dobi oznako epizode `<O>`.
Navodila so v angleščini, ker tako delujejo zanesljiveje.)

You are correcting a machine transcript (Whisper) of one episode of the
Slovenian tech podcast "Bitni pogovori" (2012–2019; Apple, apps, gadgets,
internet).

Input (read it in full, in chunks if needed):
`/Users/bizmar/Documents/github/bitni-arhiv/prepisi-preizkus/popravki-vhod/<O>.txt`
It has the episode title, date, people from the feed, show notes with links
(best reference for product/app/company names), then the transcript, one
paragraph per line: `[mm:ss | z=SECONDS] Speaker: text`.

Goal: find CLEAR misrecognitions and output a list of corrections. Fix:
- English/technical terms, product, app, company and website names mangled
  into Slovenian-looking words (e.g. "apple mansta appe" → probably "Apple" +
  app name; "džinijes" → "Genius"). Use show notes and context. Use correct
  capitalisation (iPhone, macOS, WWDC).
- Person names: hosts are Mark Bizilj, Nejc Žorga Dulmin (called "Nejc"),
  Alan Rener; guests are in the feed list. Podcast name: "Bitni pogovori"
  (inflected: "Bitnih pogovorov" …).
- Slovenian words that are clearly misheard where the intended word is
  obvious from context.

Do NOT:
- change colloquial or dialect speech (sej, ful, dons, ne?, a veš, ja),
  grammar, word order, filler words or punctuation; do not paraphrase,
  shorten, or add content;
- guess when unsure. Garbled passages where the meaning is not recoverable
  stay as they are. Skip the rest rather than guessing;
- correct speaker labels (only the text);
- correct facts: if a speaker may have said a wrong number, version or date,
  leave it (list it as uncertain instead). Change numbers only when the
  digits are clearly a misrecognition of the same spoken words;
- report a date said in the intro that differs from the feed date: episodes
  were often recorded before publication; this is not an error.

You may use WebSearch at most 5 times, only to confirm the exact spelling of
an obscure product/app name from that period.

Output 1: write a JSON array with the Write tool to
`/Users/bizmar/Documents/github/bitni-arhiv/prepisi-preizkus/delo/<O>/popravki.json`.
Each item:
`{"z": <the z value of the paragraph, copied exactly>, "staro": "<exact substring of that paragraph text, character for character, as short as possible but unique within the paragraph, usually 1–5 words>", "novo": "<replacement>", "razlog": "<short reason in Slovenian>", "gotovost": "visoka" | "srednja"}`
Optional `"povsod": true` for a single name/term misspelled identically many
times (whole-word replace across the whole episode, e.g. "Renner"→"Rener");
then "z" is the first occurrence. Use it only when the wrong form can never be
a correct word in that episode.
"staro" must match the text exactly (copy it). Before finishing, re-read your
JSON and check each "staro" really occurs in the paragraph with that z.
Ensure valid JSON (UTF-8, no comments).

Output 2: write up to 8 places you were unsure about and left unchanged, for
the owner to check by ear, to
`/Users/bizmar/Documents/github/bitni-arhiv/prepisi-preizkus/delo/<O>/popravki-negotovo.json`
as a JSON array of `{"z": <paragraph z>, "opis": "»quoted text«: short note in Slovenian (possible meaning)"}`.
Write no other files.

Final reply (short, in Slovenian): number of corrections and the main types.
